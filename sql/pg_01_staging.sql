-- ============================================================
-- 01_staging_pg.sql
-- Staging layer for PostgreSQL
-- ============================================================

DROP VIEW IF EXISTS stg_customers CASCADE;
CREATE VIEW stg_customers AS
SELECT
    customer_id,
    city,
    UPPER(state) AS state
FROM customers;

DROP VIEW IF EXISTS stg_orders CASCADE;
CREATE VIEW stg_orders AS
SELECT DISTINCT
    order_id,
    customer_id,
    order_status,
    purchase_ts::timestamp              AS purchase_ts,
    approved_ts::timestamp              AS approved_ts,
    estimated_delivery_ts::timestamp    AS estimated_delivery_ts,
    delivered_ts::timestamp             AS delivered_ts
FROM orders;

DROP VIEW IF EXISTS stg_order_items CASCADE;
CREATE VIEW stg_order_items AS
SELECT
    order_id,
    item_no,
    product_id,
    seller_id,
    category,
    price::double precision          AS price,
    freight_value::double precision  AS freight_value
FROM order_items;

DROP VIEW IF EXISTS stg_payments CASCADE;
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

DROP VIEW IF EXISTS stg_reviews CASCADE;
CREATE VIEW stg_reviews AS
SELECT
    order_id,
    review_score
FROM reviews
WHERE review_score BETWEEN 1 AND 5;
