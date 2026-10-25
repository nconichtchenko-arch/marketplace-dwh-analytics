{% snapshot dim_customers_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='check',
      check_cols=['country']
    )
}}

SELECT
    customer_id,
    country
FROM {{ ref('dim_customers') }}

{% endsnapshot %}