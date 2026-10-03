-- ============================================================
-- 01_staging.sql
-- Staging layer: one view per raw table, 1:1 grain, light cleaning only.
-- No business logic here — just type-casting, dedup, and standardizing.
-- (Mirrors dbt "staging" models: models/staging/stg_*.sql)
-- ============================================================

-- stg_customers: standardize state codes to uppercase
DROP VIEW IF EXISTS stg_customers;
CREATE VIEW stg_customers AS
SELECT
    customer_id,
    city,
    UPPER(state) AS state
FROM customers;

-- stg_orders: dedupe exact duplicate rows, cast timestamps
DROP VIEW IF EXISTS stg_orders;
CREATE VIEW stg_orders AS
SELECT DISTINCT
    order_id,
    customer_id,
    order_status,
    datetime(purchase_ts)              AS purchase_ts,
    datetime(approved_ts)              AS approved_ts,
    datetime(estimated_delivery_ts)    AS estimated_delivery_ts,
    datetime(delivered_ts)             AS delivered_ts
FROM orders;

-- stg_order_items: unchanged grain, just renamed/typed
DROP VIEW IF EXISTS stg_order_items;
CREATE VIEW stg_order_items AS
SELECT
    order_id,
    item_no,
    product_id,
    seller_id,
    category,
    CAST(price AS REAL)          AS price,
    CAST(freight_value AS REAL)  AS freight_value
FROM order_items;

-- stg_payments: drop negative / null payment values (data quality rule),
-- flag them instead of silently discarding so the issue is auditable
DROP VIEW IF EXISTS stg_payments;
CREATE VIEW stg_payments AS
SELECT
    order_id,
    payment_type,
    installments,
    payment_value,
    CASE
        WHEN payment_value IS NULL THEN 'missing_value'
        WHEN payment_value < 0     THEN 'negative_value'
        ELSE 'ok'
    END AS payment_quality_flag
FROM payments;

-- stg_reviews: clamp to valid 1-5 range (defensive; source can drift)
DROP VIEW IF EXISTS stg_reviews;
CREATE VIEW stg_reviews AS
SELECT
    order_id,
    review_score
FROM reviews
WHERE review_score BETWEEN 1 AND 5;
