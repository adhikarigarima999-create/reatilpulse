-- ============================================================
-- 02_intermediate.sql
-- Intermediate layer: joins + business logic, still order-grain.
-- (Mirrors dbt "intermediate" models: models/intermediate/int_*.sql)
-- ============================================================

-- int_order_economics: one row per order with total value, item count,
-- and delivery timing, built with a correlated aggregation (CTE) over
-- order_items — this is the "joins + window fn" layer the skill matrix
-- calls out.
DROP VIEW IF EXISTS int_order_economics;
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
    -- delivery lateness in days (NULL if not yet delivered)
    CASE
        WHEN o.delivered_ts IS NOT NULL THEN
            CAST(julianday(o.delivered_ts) - julianday(o.estimated_delivery_ts) AS INTEGER)
        ELSE NULL
    END AS delivery_delta_days,
    CASE
        WHEN o.delivered_ts IS NOT NULL
             AND julianday(o.delivered_ts) > julianday(o.estimated_delivery_ts)
        THEN 1 ELSE 0
    END AS was_late
FROM stg_orders o
LEFT JOIN item_agg ia ON ia.order_id = o.order_id
WHERE o.order_status = 'delivered';

-- int_order_review: attach review score + payment quality per order
DROP VIEW IF EXISTS int_order_review;
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

-- int_customer_order_sequence: window function layer — ranks each
-- customer's orders chronologically and flags repeat purchases.
DROP VIEW IF EXISTS int_customer_order_sequence;
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
