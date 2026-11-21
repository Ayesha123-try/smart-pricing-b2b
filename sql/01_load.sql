-- Raw tables, loaded as-is from data/raw. Nothing is cleaned here.
CREATE OR REPLACE TABLE raw_pipeline AS SELECT * FROM read_csv_auto('data/raw/sales_pipeline.csv', header = true);
CREATE OR REPLACE TABLE raw_accounts AS SELECT * FROM read_csv_auto('data/raw/accounts.csv', header = true);
CREATE OR REPLACE TABLE raw_products AS SELECT * FROM read_csv_auto('data/raw/products.csv', header = true);
CREATE OR REPLACE TABLE raw_teams    AS SELECT * FROM read_csv_auto('data/raw/sales_teams.csv', header = true);
