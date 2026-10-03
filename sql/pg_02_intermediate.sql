-- ============================================================
-- 02_intermediate_pg.sql
-- Intermediate layer for PostgreSQL
-- ============================================================

DROP VIEW IF EXISTS int_order_economics CASCADE;
CREATE VIEW int_order_economics AS
WITH item_agg AS (
    SELECT
        order_id,
        COUNT(*)                       AS n_items,
        SUM(price)                     AS merchandise_value,
        SUM(freight_value)             AS freight_value,
        SUM(price + freight_value)     AS order_value
    FROM stg_order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.purchase_ts,
    o.estimated_delivery_ts,
    o.delivered_ts,
    ia.n_items,
    ia.merchandise_value,
    ia.freight_value,
    ia.order_value,
    CASE
        WHEN o.delivered_ts IS NOT NULL THEN
            EXTRACT(DAY FROM (o.delivered_ts - o.estimated_delivery_ts))::integer
        ELSE NULL
    END AS delivery_delta_days,
    CASE
        WHEN o.delivered_ts IS NOT NULL
             AND o.delivered_ts > o.estimated_delivery_ts
        THEN 1 ELSE 0
    END AS was_late
FROM stg_orders o
LEFT JOIN item_agg ia ON ia.order_id = o.order_id
WHERE o.order_status = 'delivered';

DROP VIEW IF EXISTS int_order_review CASCADE;
CREATE VIEW int_order_review AS
SELECT
    oe.order_id,
    oe.customer_id,
    oe.order_value,
    oe.was_late,
    r.review_score,
    p.payment_type,
    p.installments,
    p.payment_quality_flag
FROM int_order_economics oe
LEFT JOIN stg_reviews  r ON r.order_id = oe.order_id
LEFT JOIN stg_payments p ON p.order_id = oe.order_id;

DROP VIEW IF EXISTS int_customer_order_sequence CASCADE;
CREATE VIEW int_customer_order_sequence AS
SELECT
    order_id,
    customer_id,
    purchase_ts,
    order_value,
    ROW_NUMBER() OVER (
        PARTITION BY customer_id ORDER BY purchase_ts
    ) AS order_seq_num,
    LAG(purchase_ts) OVER (
        PARTITION BY customer_id ORDER BY purchase_ts
    ) AS prev_order_ts,
    COUNT(*) OVER (PARTITION BY customer_id) AS lifetime_order_count
FROM int_order_economics;
