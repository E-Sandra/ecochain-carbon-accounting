ddl
"CREATE TABLE `ecochain-trace-d56fa.ecochain_data.vendor_production_volume`
(
  enterprise_name STRING,
  vendor_name STRING,
  production_year INT64,
  production_month STRING,
  total_units_manufactured INT64,
  submission_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  file_name STRING
);"