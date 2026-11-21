# Smart Pricing Prototype: Price Corridor on B2B CRM Data

## Goal
For each B2B offer, suggest a **conservative, target and stretch** price based on similar won
deals. Then test two things on real history:

1. How much won revenue was priced below target?
2. Can a win-probability model beat the base rate when lost deals have no price?

The CV bullet's numbers (8,800 opportunities, 1,196 backtest deals, up to 7.1%) are treated as
**claims to check, not targets to hit**. The report states whatever the data actually gives,
and flags any difference from the bullet.

## Data
**CRM Sales Opportunities** (Maven Analytics, public domain, fictitious company "MavenTech").

| Table | Grain | Used for |
|---|---|---|
| `sales_pipeline` | one opportunity | stage, dates, `close_value` |
| `products` | one product | series, list price |
| `accounts` | one customer | sector, revenue, employees |
| `sales_teams` | one sales agent | manager, regional office |

## Steps

| # | Step | Output |
|---|---|---|
| 1 | Set up: folders, install DuckDB and scikit-learn, pin versions | `requirements.txt` |
| 2 | Get the data and record file checksums | `data/raw/`, `data/SOURCE.md` |
| 3 | Load into DuckDB and profile: row counts, stages, nulls, join failures, name mismatches, what `close_value` looks like on lost deals | `sql/`, `outputs/data_profile.md` |
| 4 | Build a clean deal table, and fix or document any data problems | `crm.duckdb` view |
| 5 | Build the corridor: for each offer, take similar **won** deals and read off P25 / P50 / P75 as conservative / target / stretch. Start with the narrowest group and widen only until there are enough deals | `src/corridor.py` |
| 6 | Backtest walk-forward: each deal is priced **only from deals closed before it was engaged**. Assert in code that no future data is used | `outputs/backtest_deals.csv` |
| 7 | Measure: share of deals below target, revenue gap as a % of won revenue, coverage of the corridor, which fallback level was used, and sensitivity to the choices made in step 5 | `outputs/backtest_summary.json` |
| 8 | Win-probability model: logistic regression and gradient boosting on a time split, compared with the base rate on AUC, Brier score and log loss. Include a leakage check on `close_value` | `outputs/win_model_results.json` |
| 9 | Unit tests on the corridor and the no-future-data rule | `tests/` |
| 10 | Results report with charts, plus a README to rerun everything | report page, `README.md` |

## Honesty rules
- "Up to X%" is an **upper bound**: it assumes every below-target deal would still have closed
  at target. The data can't show that, because lost deals have no price.
- The company is fictitious, so results demonstrate the method, not real money.
- Every choice that could move the headline number is listed and tested in step 7.
