"""Step 3: load the raw CSVs into DuckDB and print what they actually contain."""
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    con = duckdb.connect(str(ROOT / "crm.duckdb"))
    con.execute((ROOT / "sql" / "01_load.sql").read_text())

    checks = {
        "row counts": """
            SELECT 'pipeline' t, count(*) n FROM raw_pipeline UNION ALL
            SELECT 'accounts', count(*) FROM raw_accounts UNION ALL
            SELECT 'products', count(*) FROM raw_products UNION ALL
            SELECT 'teams', count(*) FROM raw_teams""",
        "duplicate opportunity ids": """
            SELECT count(*) - count(DISTINCT opportunity_id) dupes FROM raw_pipeline""",
        "stages and close_value": """
            SELECT deal_stage, count(*) n,
                   count(engage_date) has_engage, count(close_date) has_close,
                   count(close_value) has_value,
                   sum(CASE WHEN close_value = 0 THEN 1 ELSE 0 END) value_zero,
                   sum(CASE WHEN close_value > 0 THEN 1 ELSE 0 END) value_pos,
                   count(account) has_account
            FROM raw_pipeline GROUP BY 1 ORDER BY 2 DESC""",
        "date ranges": """
            SELECT deal_stage, min(engage_date) min_eng, max(engage_date) max_eng,
                   min(close_date) min_close, max(close_date) max_close
            FROM raw_pipeline GROUP BY 1""",
        "products with no match in products table": """
            SELECT p.product, count(*) n FROM raw_pipeline p
            LEFT JOIN raw_products r USING (product)
            WHERE r.product IS NULL GROUP BY 1""",
        "accounts with no match in accounts table": """
            SELECT p.account, p.deal_stage, count(*) n FROM raw_pipeline p
            LEFT JOIN raw_accounts a USING (account)
            WHERE a.account IS NULL GROUP BY 1, 2 ORDER BY 3 DESC""",
        "agents with no match in teams table": """
            SELECT count(*) n FROM raw_pipeline p
            LEFT JOIN raw_teams t USING (sales_agent) WHERE t.sales_agent IS NULL""",
        "sectors": "SELECT sector, count(*) n FROM raw_accounts GROUP BY 1 ORDER BY 1",
        "won value vs list price by product": """
            SELECT p.product, r.sales_price list_price, count(*) won,
                   min(close_value) min_v,
                   quantile_cont(close_value, 0.25) p25,
                   quantile_cont(close_value, 0.5) p50,
                   quantile_cont(close_value, 0.75) p75,
                   max(close_value) max_v,
                   round(avg(close_value) / r.sales_price, 3) avg_ratio_to_list
            FROM raw_pipeline p
            JOIN raw_products r ON replace(p.product, 'GTXPro', 'GTX Pro') = r.product
            WHERE deal_stage = 'Won' GROUP BY 1, 2 ORDER BY 2""",
        "closed deals by month": """
            SELECT strftime(close_date, '%Y-%m') m,
                   sum(CASE WHEN deal_stage = 'Won' THEN 1 ELSE 0 END) won,
                   sum(CASE WHEN deal_stage = 'Lost' THEN 1 ELSE 0 END) lost
            FROM raw_pipeline WHERE close_date IS NOT NULL GROUP BY 1 ORDER BY 1""",
        "engaged deals by month": """
            SELECT strftime(engage_date, '%Y-%m') m,
                   sum(CASE WHEN deal_stage = 'Won' THEN 1 ELSE 0 END) won,
                   sum(CASE WHEN deal_stage = 'Lost' THEN 1 ELSE 0 END) lost,
                   sum(CASE WHEN deal_stage = 'Engaging' THEN 1 ELSE 0 END) open
            FROM raw_pipeline WHERE engage_date IS NOT NULL GROUP BY 1 ORDER BY 1""",
    }
    lines = ["# Data profile", ""]
    for title, sql in checks.items():
        df = con.execute(sql).df()
        print(f"\n== {title}\n{df.to_string(index=False)}")
        lines += [f"## {title}", "", "```", df.to_string(index=False), "```", ""]
    (ROOT / "outputs" / "data_profile.md").write_text("\n".join(lines), encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
