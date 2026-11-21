"""Can a model predict win / loss better than the base rate, using what is known at engagement?

Trained on deals closed before 2017-10-01 and tested on deals closed in Q4 2017. Using the fixed
cutoff slightly favours the model, because some Q4 deals were engaged before the cutoff.
"""
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from corridor import ROOT, load_deals

CUTOFF = pd.Timestamp("2017-10-01")
VALID_START = pd.Timestamp("2017-07-01")
TEST_END = pd.Timestamp("2018-01-01")
SEED = 2026
PRIOR_STRENGTH = 20

CATEGORICAL = ["product", "series", "sector", "size_band", "office_location",
               "sales_agent", "manager", "regional_office"]
NUMERIC = ["list_price", "revenue", "employees", "year_established", "engage_month", "engage_dow",
           "agent_win_rate", "account_win_rate", "product_win_rate", "agent_prior_deals"]


def add_history_features(closed):
    """Smoothed win rates, counting only deals that closed before each deal was engaged."""
    closed = closed.copy()
    history = closed.sort_values("close_date")
    dates = history["close_date"].to_numpy()
    wins = history["won"].to_numpy()
    base = wins.mean()
    for key, name in (("sales_agent", "agent"), ("account", "account"), ("product", "product")):
        groups = {
            k: (dates[idx], np.cumsum(wins[idx]))
            for k, idx in history.groupby(key).indices.items()
        }
        rates, counts = [], []
        for value, engaged in zip(closed[key], closed["engage_date"].to_numpy()):
            d, cum = groups[value]
            n = np.searchsorted(d, engaged, side="left")
            w = cum[n - 1] if n else 0
            rates.append((w + PRIOR_STRENGTH * base) / (n + PRIOR_STRENGTH))
            counts.append(n)
        closed[f"{name}_win_rate"] = rates
        if name == "agent":
            closed["agent_prior_deals"] = counts
    closed["engage_month"] = closed["engage_date"].dt.month
    closed["engage_dow"] = closed["engage_date"].dt.day_of_week
    return closed


def preprocess(categorical, numeric):
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), numeric),
    ])


def candidates(categorical, numeric):
    for c in (0.003, 0.01, 0.1, 1.0):
        yield f"logistic C={c}", make_pipeline(
            preprocess(categorical, numeric), LogisticRegression(C=c, max_iter=2000))
    for depth, lr, iters in ((2, 0.03, 100), (3, 0.03, 200), (3, 0.1, 100)):
        yield f"gradient boosting depth={depth} lr={lr} iters={iters}", make_pipeline(
            preprocess(categorical, numeric),
            HistGradientBoostingClassifier(max_depth=depth, learning_rate=lr, max_iter=iters, random_state=SEED))


def scores(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    auc = roc_auc_score(y, p) if np.unique(p).size > 1 else 0.5
    return {"auc": round(float(auc), 4), "brier": round(float(brier_score_loss(y, p)), 4),
            "log_loss": round(float(log_loss(y, p)), 4)}


def bootstrap(y, p_model, p_base, reps=2000):
    """95% CIs for the model's AUC and its Brier improvement over the base rate."""
    rng = np.random.default_rng(SEED)
    y, p_model, p_base = map(np.asarray, (y, p_model, p_base))
    aucs, improvements = [], []
    for _ in range(reps):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        aucs.append(roc_auc_score(y[i], p_model[i]))
        improvements.append(np.mean((p_base[i] - y[i]) ** 2) - np.mean((p_model[i] - y[i]) ** 2))
    pct = lambda v: [round(float(x), 4) for x in np.percentile(v, [2.5, 97.5])]
    return {"auc_95ci": pct(aucs), "brier_improvement_95ci": pct(improvements)}


def select_and_test(train, test, categorical, numeric):
    """Pick the best settings on Jul-Sep closes, then refit on all pre-cutoff deals."""
    fit, valid = train[train["close_date"] < VALID_START], train[train["close_date"] >= VALID_START]
    tried = []
    for name, model in candidates(categorical, numeric):
        model.fit(fit[categorical + numeric], fit["won"])
        p = model.predict_proba(valid[categorical + numeric])[:, 1]
        tried.append({"model": name, **scores(valid["won"], p)})
    best = min(tried, key=lambda r: r["log_loss"])["model"]
    model = dict(candidates(categorical, numeric))[best]
    model.fit(train[categorical + numeric], train["won"])
    return best, model.predict_proba(test[categorical + numeric])[:, 1], tried


def main():
    deals = load_deals()
    closed = deals[deals["deal_stage"].isin(["Won", "Lost"])].copy()
    closed["won"] = (closed["deal_stage"] == "Won").astype(int)
    closed = add_history_features(closed)
    closed["cycle_days"] = (closed["close_date"] - closed["engage_date"]).dt.days
    closed["close_month"] = closed["close_date"].dt.month

    train = closed[closed["close_date"] < CUTOFF]
    test = closed[(closed["close_date"] >= CUTOFF) & (closed["close_date"] < TEST_END)]
    y = test["won"].to_numpy()
    base_rate = float(train["won"].mean())
    p_base = np.full(len(test), base_rate)

    results = {
        "train_deals": int(len(train)), "test_deals": int(len(test)),
        "train_win_rate": round(base_rate, 4), "test_win_rate": round(float(y.mean()), 4),
        "base_rate": scores(y, p_base),
    }

    best, p, tried = select_and_test(train, test, CATEGORICAL, NUMERIC)
    results["best_model"] = best
    results["best_model_test"] = {**scores(y, p), **bootstrap(y, p, p_base)}
    results["validation_grid"] = tried

    # Each family judged on the test set too, so the verdict doesn't hang on one selected model.
    results["all_models_on_test"] = []
    for name, model in candidates(CATEGORICAL, NUMERIC):
        model.fit(train[CATEGORICAL + NUMERIC], train["won"])
        p_candidate = model.predict_proba(test[CATEGORICAL + NUMERIC])[:, 1]
        top = np.argsort(-p_candidate)[: len(p_candidate) // 5]
        results["all_models_on_test"].append({
            "model": name, **scores(y, p_candidate), **bootstrap(y, p_candidate, p_base),
            "top_20pct_win_rate": round(float(y[top].mean()), 4),
        })

    # Decision value: would acting on the score pick better deals than picking at random?
    order = np.argsort(-p)
    top = order[: len(order) // 5]
    results["top_20pct_win_rate"] = round(float(y[top].mean()), 4)

    # The base rate re-estimated with hindsight, the best any constant prediction could do.
    results["hindsight_base_rate"] = scores(y, np.full(len(test), y.mean()))

    # Leakage checks: these fields look predictive but aren't known when pricing an offer.
    leaks = {}
    for label, extra in (("close_value (price on the deal)", ["close_value"]),
                         ("close month", ["close_month"]),
                         ("sales cycle length", ["cycle_days"])):
        m = make_pipeline(preprocess(CATEGORICAL, NUMERIC + extra),
                          HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=100, random_state=SEED))
        m.fit(train[CATEGORICAL + NUMERIC + extra], train["won"])
        leaks[label] = scores(y, m.predict_proba(test[CATEGORICAL + NUMERIC + extra])[:, 1])
    results["leakage_checks"] = leaks

    # The evidence behind "no price on lost deals".
    lost = closed[closed["won"] == 0]
    results["lost_deals_total"] = int(len(lost))
    results["lost_deals_with_positive_price"] = int((lost["close_value"] > 0).sum())
    results["list_prices_per_product"] = int(deals.groupby("product")["list_price"].nunique().max())
    results["win_rate_by_product"] = (
        closed.groupby("product")["won"].mean().round(3).sort_values().to_dict())

    (ROOT / "outputs" / "win_model_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
