-- One clean row per opportunity. Fixes the two naming errors found in profiling:
--   'GTXPro' in the pipeline is 'GTX Pro' in the products table (1,480 rows)
--   'technolgy' is a typo for 'technology' in the accounts table (12 accounts)
-- Size bands are round numbers chosen before looking at any pricing result.
CREATE OR REPLACE VIEW deals AS
SELECT
    p.opportunity_id,
    p.sales_agent,
    t.manager,
    t.regional_office,
    replace(p.product, 'GTXPro', 'GTX Pro') AS product,
    r.series,
    r.sales_price AS list_price,
    p.account,
    replace(a.sector, 'technolgy', 'technology') AS sector,
    a.revenue,
    a.employees,
    a.year_established,
    a.office_location,
    CASE
        WHEN a.employees IS NULL THEN NULL
        WHEN a.employees < 1000 THEN 'small'
        WHEN a.employees < 5000 THEN 'mid'
        ELSE 'large'
    END AS size_band,
    p.deal_stage,
    p.engage_date,
    p.close_date,
    p.close_value
FROM raw_pipeline p
LEFT JOIN raw_products r ON replace(p.product, 'GTXPro', 'GTX Pro') = r.product
LEFT JOIN raw_accounts a ON p.account = a.account
LEFT JOIN raw_teams t ON p.sales_agent = t.sales_agent;
