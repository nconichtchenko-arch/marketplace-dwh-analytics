SELECT
    invoice_no,
    stock_code,
    date_id AS order_date,
    customer_id,
    SUM(quantity) AS total_quantity,
    SUM(total_amount) AS total_revenue
FROM {{ ref('stg_sales') }}
GROUP BY 
    invoice_no, 
    stock_code, 
    date_id, 
    customer_id
