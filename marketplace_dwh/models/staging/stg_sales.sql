SELECT
    *
FROM {{ source('raw', 'fact_sales') }}
