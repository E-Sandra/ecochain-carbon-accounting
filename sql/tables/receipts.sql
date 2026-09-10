ddl
"CREATE TABLE `ecochain-trace-d56fa.ecochain_data.receipts`
(
  enterprise_name STRING,
  vendor_name STRING,
  utility_category STRING,
  consumption_amount FLOAT64,
  unit_of_measure STRING,
  billing_date DATE,
  billing_year INT64,
  billing_month INT64,
  billing_day INT64,
  submission_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_name STRING,
  production_year INT64,
  production_month STRING
)
PARTITION BY billing_date
CLUSTER BY enterprise_name, vendor_name, billing_year, billing_month;"