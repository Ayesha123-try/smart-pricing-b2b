"""Backtest the corridor on deals won in Q4 2017, pricing each from earlier deals only.

Settings fixed before any result was seen: min_n = 30, quartiles, and comparison deals must
have closed before the backtest deal was engaged (the strictest reading of "earlier data").
"""
import json

import numpy as np
import pandas as pd

from corridor import LEVELS, PriceCorridor, ROOT, load_deals, quote_book

TEST_START = pd.Timestamp("2017-10-01")
TEST_END = pd.Timestamp("2018-01-01")
OUT = ROOT / "outputs"
SEED = 2026


def run(won, min_n=30, quantiles=(0.25, 0.5, 0.75), levels=LEVELS, as_of_col="engage_date", cutoff=None):
    corridor = PriceCorridor(won, min_n=min_n, quantiles=quantiles, levels=levels)
    test = won[(won["close_date"] >= TEST_START) & (won["close_date"] < TEST_END)]
    rows = []
    for d in test.itertuples():
        as_of = cutoff if cutoff is not None else getattr(d, as_of_col)
        q = corridor.quote(d.product, d.sector, d.size_band, d.list_price, as_of)
        rows.append({
            "opportunity_id": d.opportunity_id, "sales_agent": d.sales_agent, "product": d.product,
            "sector": d.sector, "size_band": d.size_band, "account": d.account,
            "engage_date": d.engage_date.date(), "close_date": d.close_date.date(),
            "list_price": d.list_price, "close_value": d.close_value,
            "conservative": q.conservative, "target": q.target, "stretch": q.stretch,
            "level": q.level, "n_comparable": q.n_comparable,
        })
    return pd.DataFrame(rows)


def gap_pct(bt, col="target"):
    gap = (bt[col] - bt["close_value"]).clip(lower=0).sum()
    return 100 * gap / bt["close_value"].sum()


def pinball(y, pred, q):
    e = y - pred
    return np.maximum(q * e, (q - 1) * e)


def corridor_pinball(bt):
    """Lower is better. Averages price-normalised pinball loss over the three quantiles."""
    y = bt["close_value"] / bt["list_price"]
    return float(np.mean([
        pinball(y, bt[col] / bt["list_price"], q).mean()
        for col, q in (("conservative", 0.25), ("target", 0.5), ("stretch", 0.75))
    ]))


def bootstrap_gap(bt, reps=5000):
    rng = np.random.default_rng(SEED)
    gaps = (bt["target"] - bt["close_value"]).clip(lower=0).to_numpy()
    vals = bt["close_value"].to_numpy()
    idx = rng.integers(0, len(bt), size=(reps, len(bt)))
    pct = 100 * gaps[idx].sum(axis=1) / vals[idx].sum(axis=1)
    return [round(float(x), 2) for x in np.percentile(pct, [2.5, 97.5])]


def group_table(bt, key):
    g = bt.assign(gap=(bt["target"] - bt["close_value"]).clip(lower=0))
    t = g.groupby(key).agg(
        deals=("close_value", "size"), revenue=("close_value", "sum"), gap=("gap", "sum"),
        below_target=("gap", lambda s: float((s > 0).mean())),
    ).reset_index()
    t["gap_pct_of_group_revenue"] = (100 * t["gap"] / t["revenue"]).round(2)
    t["share_of_total_gap"] = (100 * t["gap"] / t["gap"].sum()).round(1)
    t["below_target"] = (100 * t["below_target"]).round(1)
    t["gap"] = t["gap"].round(0)
    return t.sort_values("gap", ascending=False)


def variance_explained(won, by):
    """Share of within-product price variance explained by a grouping (0 = none)."""
    d = won.assign(r=won["close_value"] / won["list_price"]).dropna(subset=[by])
    resid = d["r"] - d.groupby("product")["r"].transform("mean")
    fitted = resid.groupby(d[by]).transform("mean")
    # Random labels would still "explain" about (groups - 1) / (deals - 1) of the variance.
    chance = (d[by].nunique() - 1) / (len(d) - 1)
    return {"explained_pct": round(100 * float(fitted.var() / resid.var()), 2),
            "expected_by_chance_pct": round(100 * chance, 2)}


def main():
    deals = load_deals()
    won = deals[deals["deal_stage"] == "Won"].sort_values("close_date").reset_index(drop=True)
    bt = run(won)
    bt.round(2).to_csv(OUT / "backtest_deals.csv", index=False)

    # Look-ahead audit: re-quote every deal after physically deleting all later data.
    for d in bt.itertuples():
        as_of = pd.Timestamp(d.engage_date)
        q = PriceCorridor(won[won["close_date"] < as_of]).quote(
            d.product, d.sector, d.size_band, d.list_price, as_of)
        assert (q.target, q.level, q.n_comparable) == (d.target, d.level, d.n_comparable)

    revenue = float(bt["close_value"].sum())
    below = bt["close_value"] < bt["target"]
    gap = float((bt["target"] - bt["close_value"]).clip(lower=0).sum())
    summary = {
        "opportunities_total": int(len(deals)),
        "stage_counts": deals["deal_stage"].value_counts().to_dict(),
        "backtest_deals": int(len(bt)),
        "won_revenue": revenue,
        "deals_below_target": int(below.sum()),
        "deals_below_target_pct": round(100 * float(below.mean()), 1),
        "revenue_gap_to_target": round(gap),
        "gap_pct_of_won_revenue": round(gap_pct(bt), 2),
        "gap_pct_95ci": bootstrap_gap(bt),
        "look_ahead_audit": f"passed on all {len(bt)} deals",
        "gap_to_conservative_pct": round(gap_pct(bt, "conservative"), 2),
        "gap_to_stretch_pct": round(gap_pct(bt, "stretch"), 2),
        "capture_scenarios_pct_of_won_revenue": {
            f"{c}%": round(gap_pct(bt) * c / 100, 2) for c in (25, 50, 100)
        },
        "calibration_pct": {
            "below_conservative (expect ~25)": round(100 * float((bt["close_value"] < bt["conservative"]).mean()), 1),
            "conservative_to_target (expect ~25)": round(100 * float(((bt["close_value"] >= bt["conservative"]) & below).mean()), 1),
            "target_to_stretch (expect ~25)": round(100 * float(((~below) & (bt["close_value"] <= bt["stretch"])).mean()), 1),
            "above_stretch (expect ~25)": round(100 * float((bt["close_value"] > bt["stretch"]).mean()), 1),
        },
        "level_used": bt["level"].value_counts().to_dict(),
        "median_comparable_deals": float(bt["n_comparable"].median()),
    }

    # Sensitivity: every choice that could move the headline number.
    sens = []
    for min_n in (10, 20, 30, 50, 100):
        for as_of_col in ("engage_date", "close_date"):
            b = run(won, min_n=min_n, as_of_col=as_of_col)
            sens.append({"scenario": f"min_n={min_n}, known by {as_of_col}", "gap_pct": round(gap_pct(b), 2),
                         "below_target_pct": round(100 * float((b["close_value"] < b["target"]).mean()), 1)})
    b = run(won, cutoff=TEST_START)
    sens.append({"scenario": "fixed cutoff: trained on closes before 2017-10-01", "gap_pct": round(gap_pct(b), 2),
                 "below_target_pct": round(100 * float((b["close_value"] < b["target"]).mean()), 1)})
    for q in ((0.25, 0.4, 0.75), (0.25, 0.6, 0.75)):
        b = run(won, quantiles=q)
        sens.append({"scenario": f"target at P{int(q[1] * 100)}", "gap_pct": round(gap_pct(b), 2),
                     "below_target_pct": round(100 * float((b["close_value"] < b["target"]).mean()), 1)})
    pd.DataFrame(sens).to_csv(OUT / "sensitivity.csv", index=False)
    summary["sensitivity_gap_range_pct"] = [min(s["gap_pct"] for s in sens), max(s["gap_pct"] for s in sens)]

    # Does segmenting help? Compare against simpler corridors on the same deals.
    product_only = run(won, levels=[("product", ("product",)), ("all products", ())])
    list_flat = bt.assign(conservative=bt["list_price"], target=bt["list_price"], stretch=bt["list_price"])
    summary["benchmarks"] = {
        "hierarchical_pinball": round(corridor_pinball(bt), 5),
        "product_only_pinball": round(corridor_pinball(product_only), 5),
        "list_price_pinball": round(corridor_pinball(list_flat), 5),
        "product_only_gap_pct": round(gap_pct(product_only), 2),
        "list_price_gap_pct": round(gap_pct(list_flat), 2),
    }
    summary["within_product_price_variance_explained"] = {
        by: variance_explained(won, by) for by in ("sector", "size_band", "sales_agent", "manager", "regional_office", "account")
    }
    summary["price_to_list_ratio"] = {
        k: round(float(v), 3)
        for k, v in (won["close_value"] / won["list_price"]).describe(percentiles=[.25, .5, .75]).items()
    }

    for key in ("product", "sector", "size_band", "sales_agent", "level"):
        group_table(bt, key).to_csv(OUT / f"gap_by_{key}.csv", index=False)
    quote_book(deals).to_csv(OUT / "open_deal_corridors.csv", index=False)

    (OUT / "backtest_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=2, default=float))
    print(pd.DataFrame(sens).to_string(index=False))
    print(group_table(bt, "product").to_string(index=False))


if __name__ == "__main__":
    main()
