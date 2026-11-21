"""Which definition, if any, reproduces the CV's "up to 7.1% of won revenue priced below target"?

This is a lookup, not a tuning step: the headline stays as defined in backtest.py.
"""
import json

import pandas as pd

from backtest import gap_pct, run
from corridor import ROOT, load_deals

OUT = ROOT / "outputs"


def pct(gap, base):
    return round(100 * float(gap) / float(base), 2)


def main():
    bt = pd.read_csv(OUT / "backtest_deals.csv")
    rev = bt["close_value"].sum()
    below = bt["close_value"] < bt["target"]
    gap = lambda col, d=bt: (d[col] - d["close_value"]).clip(lower=0)

    rows = [
        {"definition": "Gap to target, % of won revenue (headline)", "value": pct(gap("target").sum(), rev)},
        {"definition": "Gap to conservative, % of won revenue", "value": pct(gap("conservative").sum(), rev)},
        {"definition": "Gap to stretch, % of won revenue", "value": pct(gap("stretch").sum(), rev)},
        {"definition": "Gap to target, % of revenue on the below-target deals only",
         "value": pct(gap("target").sum(), bt.loc[below, "close_value"].sum())},
        {"definition": "Unweighted mean gap to target per deal, % of its target",
         "value": round(100 * float((gap("target") / bt["target"]).mean()), 2)},
        {"definition": "Unweighted mean gap among below-target deals, % of their target",
         "value": round(100 * float((gap("target") / bt["target"])[below].mean()), 2)},
        {"definition": "Share of won revenue sitting on below-target deals",
         "value": pct(bt.loc[below, "close_value"].sum(), rev)},
    ]
    for key, min_deals in (("product", 1), ("sector", 1), ("size_band", 1), ("sales_agent", 20)):
        g = bt.assign(gap=gap("target")).groupby(key).agg(gap=("gap", "sum"), rev=("close_value", "sum"), n=("gap", "size"))
        g = g[g["n"] >= min_deals]
        g["p"] = 100 * g["gap"] / g["rev"]
        rows.append({"definition": f"Highest gap to target in any single {key} (min {min_deals} deals): {g['p'].idxmax()}",
                     "value": round(float(g["p"].max()), 2)})
    bt["close_month"] = bt["close_date"].astype(str).str[:7]
    g = bt.assign(gap=gap("target")).groupby("close_month").agg(gap=("gap", "sum"), rev=("close_value", "sum"))
    rows.append({"definition": "Highest gap to target in any single month of Q4",
                 "value": round(float((100 * g["gap"] / g["rev"]).max()), 2)})

    # What percentile would the target have to sit at for the gap to reach 7.1%?
    deals = load_deals()
    won = deals[deals["deal_stage"] == "Won"].sort_values("close_date").reset_index(drop=True)
    for q in (0.65, 0.70, 0.75):
        b = run(won, quantiles=(0.25, q, 0.9))
        rows.append({"definition": f"Gap if the target were set at P{int(q * 100)} instead of the median",
                     "value": round(gap_pct(b), 2)})

    table = pd.DataFrame(rows)
    table["distance_from_7.1"] = (table["value"] - 7.1).abs().round(2)
    table.to_csv(OUT / "claim_reconciliation.csv", index=False)
    print(table.to_string(index=False))
    (OUT / "claim_reconciliation.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
