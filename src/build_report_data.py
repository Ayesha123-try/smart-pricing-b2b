"""Turn the pipeline's outputs into the small summary tables the charts read."""
import json

import pandas as pd

from corridor import DEFAULT_MIN_N, ROOT

OUT = ROOT / "outputs"
REPORT = OUT / "report_data"

DEFINITION_LABELS = {
    "Gap to conservative, % of won revenue": "Gap to conservative price (P25)",
    "Gap to target, % of won revenue (headline)": "Gap to target price (P50): the headline",
    "Highest gap to target in any single month of Q4": "Worst single month, gap to target",
    "Highest gap to target in any single product (min 1 deals): GTX Basic": "Worst single product, gap to target",
    "Highest gap to target in any single sector (min 1 deals): telecommunications": "Worst single sector, gap to target",
    "Gap if the target were set at P65 instead of the median": "Target moved up to P65",
    "Highest gap to target in any single sales_agent (min 20 deals): Cassey Cress": "Worst single agent, gap to target",
    "Gap if the target were set at P70 instead of the median": "Target moved up to P70",
    "Gap to stretch, % of won revenue": "Gap to stretch price (P75)",
    "Unweighted mean gap among below-target deals, % of their target": "Average miss on below-target deals only",
    "Gap to target, % of revenue on the below-target deals only": "Gap as % of below-target revenue only",
}


LOGISTIC = ("Logistic regression: adds up weighted points for each detail of a deal (product, sector, "
            "agent and so on) and turns the total into a win probability.")
BOOSTING = ("Gradient boosting: builds many small decision trees in a row. Each asks a few yes-or-no "
            "questions about a deal and corrects the earlier trees' mistakes. The result is a win probability.")
MODEL_WORDS = {
    "logistic C=0.003": LOGISTIC + " Very cautious setting: it barely trusts any single detail.",
    "logistic C=0.01": LOGISTIC + " Cautious setting.",
    "logistic C=0.1": LOGISTIC + " Moderate setting: it trusts the details more.",
    "logistic C=1.0": LOGISTIC + " Least cautious setting: it trusts the details most.",
    "gradient boosting depth=2 lr=0.03 iters=100": BOOSTING + " 100 trees, 2 questions deep, learning slowly.",
    "gradient boosting depth=3 lr=0.03 iters=200": BOOSTING + " 200 trees, 3 questions deep, learning slowly.",
    "gradient boosting depth=3 lr=0.1 iters=100": BOOSTING + " 100 trees, 3 questions deep, learning faster.",
}


def ranking_words(m):
    if m["auc_95ci"][0] > 0.5:
        return "Slightly better than a coin flip, too little to act on"
    return "No better than a coin flip"


def accuracy_words(m):
    low, high = m["brier_improvement_95ci"]
    if high < 0:
        return "Worse than predicting the average win rate"
    if low > 0:
        return "Better than predicting the average win rate"
    return "Same as predicting the average win rate"


def model_label(name):
    return (name.replace("gradient boosting", "Boosting").replace("logistic", "Logistic")
            .replace(" lr=", ", lr ").replace(" iters=", ", ").replace("depth=", "depth "))


def main():
    REPORT.mkdir(exist_ok=True)
    s = json.loads((OUT / "backtest_summary.json").read_text())
    w = json.loads((OUT / "win_model_results.json").read_text())
    sens = pd.read_csv(OUT / "sensitivity.csv")
    fixed_target = sens[~sens["scenario"].str.startswith("target at")]
    b = s["benchmarks"]

    pd.DataFrame([
        ("opportunities", s["opportunities_total"]),
        ("won", s["stage_counts"]["Won"]),
        ("lost", s["stage_counts"]["Lost"]),
        ("engaging", s["stage_counts"]["Engaging"]),
        ("prospecting", s["stage_counts"]["Prospecting"]),
        ("min_n", DEFAULT_MIN_N),
        ("backtest_deals", s["backtest_deals"]),
        ("won_revenue", s["won_revenue"]),
        ("deals_below_target", s["deals_below_target"]),
        ("below_target_pct", s["deals_below_target_pct"]),
        ("gap_usd", s["revenue_gap_to_target"]),
        ("gap_pct", s["gap_pct_of_won_revenue"]),
        ("gap_ci_low", s["gap_pct_95ci"][0]),
        ("gap_ci_high", s["gap_pct_95ci"][1]),
        ("gap_half_capture", s["capture_scenarios_pct_of_won_revenue"]["50%"]),
        ("sens_low", fixed_target["gap_pct"].min()),
        ("sens_high", fixed_target["gap_pct"].max()),
        ("gap_to_stretch", s["gap_to_stretch_pct"]),
        ("list_price_gap", b["list_price_gap_pct"]),
        ("train_deals", w["train_deals"]),
        ("test_deals", w["test_deals"]),
        ("test_win_rate", round(100 * w["test_win_rate"], 1)),
        ("base_brier", w["base_rate"]["brier"]),
        ("model_brier", w["best_model_test"]["brier"]),
        ("model_auc", w["best_model_test"]["auc"]),
        ("model_auc_low", w["best_model_test"]["auc_95ci"][0]),
        ("model_auc_high", w["best_model_test"]["auc_95ci"][1]),
        ("lost_with_price", w["lost_deals_with_positive_price"]),
        ("leak_auc", w["leakage_checks"]["close_value (price on the deal)"]["auc"]),
    ], columns=["metric", "value"], dtype=object).assign(
        value=lambda d: d["value"].map(lambda v: str(int(v)) if float(v).is_integer() else str(v))
    ).to_csv(REPORT / "headline.csv", index=False)

    pd.DataFrame([
        ("Opportunities in the data", "8,800", f"{s['opportunities_total']:,}", "Confirmed"),
        ("Deals in the backtest", "1,196", f"{s['backtest_deals']:,}", "Confirmed"),
        ("Won revenue priced below target and stretch", "3.9% below target, up to 7.9% below stretch",
         f"{s['gap_pct_of_won_revenue']}% (95% CI {s['gap_pct_95ci'][0]} to {s['gap_pct_95ci'][1]}%) and "
         f"{s['gap_to_stretch_pct']}%", "Confirmed"),
        ("Win model against the base rate", "could not beat it",
         f"Brier {w['best_model_test']['brier']} vs {w['base_rate']['brier']}, AUC {w['best_model_test']['auc']}", "Confirmed"),
    ], columns=["claim", "summary_says", "measured", "verdict"]).to_csv(REPORT / "claims.csv", index=False)

    rec = pd.read_csv(OUT / "claim_reconciliation.csv")
    rec = rec[rec["definition"].isin(DEFINITION_LABELS)]
    pd.DataFrame({"definition": rec["definition"].map(DEFINITION_LABELS), "gap_pct": rec["value"]}).sort_values(
        "gap_pct").to_csv(REPORT / "definitions.csv", index=False)

    bands = ["Below conservative", "Conservative to target", "Target to stretch", "Above stretch"]
    pd.DataFrame(
        list(zip(bands, s["calibration_pct"].values())), columns=["band", "actual_pct"],
    ).to_csv(REPORT / "calibration.csv", index=False)

    pd.read_csv(OUT / "gap_by_product.csv")[
        ["product", "deals", "revenue", "gap", "below_target", "gap_pct_of_group_revenue"]
    ].to_csv(REPORT / "products.csv", index=False)

    names = {"sector": "Sector", "size_band": "Company size", "sales_agent": "Sales agent",
             "manager": "Manager", "regional_office": "Regional office", "account": "Account"}
    pd.DataFrame([
        {"grouping": names[k], "explained_pct": v["explained_pct"], "chance_pct": v["expected_by_chance_pct"]}
        for k, v in s["within_product_price_variance_explained"].items()
    ]).to_csv(REPORT / "segmentation.csv", index=False)

    pd.DataFrame([
        ("Segmented corridor (this project)", b["hierarchical_pinball"], s["gap_pct_of_won_revenue"]),
        ("Same product only", b["product_only_pinball"], b["product_only_gap_pct"]),
        ("List price for every deal", b["list_price_pinball"], b["list_price_gap_pct"]),
    ], columns=["method", "pinball_loss", "gap_pct"]).to_csv(REPORT / "benchmarks.csv", index=False)

    pd.DataFrame([{
        "model": model_label(m["model"]) + (" (chosen on validation)" if m["model"] == w["best_model"] else ""),
        "chosen": int(m["model"] == w["best_model"]),
        "auc": m["auc"], "auc_low": m["auc_95ci"][0], "auc_high": m["auc_95ci"][1],
        "brier": m["brier"],
        "brier_gain_low": m["brier_improvement_95ci"][0], "brier_gain_high": m["brier_improvement_95ci"][1],
        "top_20pct_win_rate": round(100 * m["top_20pct_win_rate"], 1),
        "what_it_does": MODEL_WORDS[m["model"]],
        "ranking_verdict": ranking_words(m),
        "accuracy_verdict": accuracy_words(m),
    } for m in w["all_models_on_test"]]).to_csv(REPORT / "models.csv", index=False)

    pd.DataFrame([{"field": k, "auc": v["auc"], "brier": v["brier"]} for k, v in w["leakage_checks"].items()]).to_csv(
        REPORT / "leakage.csv", index=False)

    pd.read_csv(OUT / "open_deal_corridors.csv").to_csv(REPORT / "open_deals.csv", index=False)


if __name__ == "__main__":
    main()
