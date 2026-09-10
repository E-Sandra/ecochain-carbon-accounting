WITH latest_production AS (
    SELECT 
        *,
        DENSE_RANK() OVER (
            PARTITION BY enterprise_name, vendor_name, production_year, production_month 
            ORDER BY production_year DESC, production_month DESC, submission_timestamp DESC
        ) as dr
    FROM `ecochain-trace-d56fa.ecochain_data.vendor_production_volume`
)
SELECT 
    e.vendor_name,
    e.enterprise_name,
    e.production_year,
    e.production_month,
    MAX(e.source_standard) AS source_standard,
    SUM(e.total_emissions_kg_co2e) AS total_facility_emissions,
    'Kilograms (kg CO2e)' AS emissions_unit,
    MAX(p.total_units_manufactured) AS units_produced,
    ROUND(SUM(e.total_emissions_kg_co2e) / NULLIF(MAX(p.total_units_manufactured), 0), 4) AS kg_co2e_per_unit,
    CURRENT_TIMESTAMP() AS view_ingestion_timestamp
FROM 
    `ecochain-trace-d56fa.ecochain_data.calculated_emissions` e
JOIN 
    latest_production p
ON 
    e.enterprise_name = p.enterprise_name
    AND e.vendor_name = p.vendor_name 
    AND e.production_year = p.production_year 
    AND CAST(e.production_month AS STRING) = CAST(p.production_month AS STRING)
    AND p.dr = 1
GROUP BY 
    e.vendor_name, 
    e.enterprise_name, 
    e.production_year, 
    e.production_month