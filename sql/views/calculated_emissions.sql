WITH latest_receipts AS (
    SELECT 
        *,
        DENSE_RANK() OVER (
            PARTITION BY enterprise_name, vendor_name, utility_category, billing_year, billing_month 
            ORDER BY billing_date DESC, submission_timestamp DESC
        ) as dr
    FROM `ecochain-trace-d56fa.ecochain_data.receipts`
),
standardised AS (
    SELECT 
        r.*,
        CASE 
            WHEN r.unit_of_measure = 'mL' THEN r.consumption_amount / 1000.0
            WHEN r.unit_of_measure = 'kL' THEN r.consumption_amount * 1000.0
            WHEN r.unit_of_measure = 'Wh' THEN r.consumption_amount / 1000.0
            WHEN r.unit_of_measure = 'MWh' THEN r.consumption_amount * 1000.0
            WHEN r.unit_of_measure = 'grams' THEN r.consumption_amount / 1000.0
            WHEN r.unit_of_measure = 'tonnes' THEN r.consumption_amount * 1000.0
            ELSE r.consumption_amount 
        END AS standardised_consumption_amount,
        CASE 
            WHEN r.unit_of_measure IN ('mL', 'kL') THEN 'Liters'
            WHEN r.unit_of_measure IN ('Wh', 'MWh') THEN 'kWh'
            WHEN r.unit_of_measure IN ('grams', 'tonnes') THEN 'kg'
            ELSE r.unit_of_measure
        END AS standardised_unit_of_measure
    FROM latest_receipts r
    WHERE r.dr = 1
)
SELECT 
    s.enterprise_name,
    s.vendor_name,
    s.utility_category,
    s.billing_date,
    s.billing_year,
    s.billing_month,
    s.billing_day,
    s.production_year,
    s.production_month,
    s.consumption_amount,
    s.unit_of_measure,
    s.standardised_consumption_amount,
    s.standardised_unit_of_measure,
    ef.kg_co2e_per_unit AS emission_factor,
    ROUND(s.standardised_consumption_amount * ef.kg_co2e_per_unit, 2) AS total_emissions_kg_co2e,
    ef.source_standard,
    s.file_name,
    s.submission_timestamp,
    CURRENT_TIMESTAMP() AS view_ingestion_timestamp
FROM standardised s
LEFT JOIN `ecochain-trace-d56fa.ecochain_data.emission_factors` ef
  ON ef.utility_category = s.utility_category