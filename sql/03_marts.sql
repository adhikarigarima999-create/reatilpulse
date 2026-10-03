-- ============================================================
-- 03_marts.sql
-- Mart layer: analysis-ready, customer-grain fact table.
-- This is what Tableau / pandas / scikit-learn all read from.
-- (Mirrors dbt "marts" models: models/marts/fct_customers.sql)
-- ============================================================

DROP VIEW IF EXISTS fct_customers;
CREATE VIEW fct_customers AS
SELECT
    c.customer_id,
    c.state,
    seq.lifetime_order_count,
    CASE WHEN seq.lifetime_order_count > 1 THEN 1 ELSE 0 END AS is_repeat_customer,
    ROUND(AVG(oe.order_value), 2)          AS avg_order_value,
    ROUND(SUM(oe.order_value), 2)          AS lifetime_value,
    ROUND(AVG(oe.was_late) * 100, 1)       AS pct_orders_late,
    ROUND(AVG(rv.review_score), 2)         AS avg_review_score,
    MIN(oe.purchase_ts)                    AS first_purchase_ts,
    MAX(oe.purchase_ts)                    AS last_purchase_ts
FROM stg_customers c
JOIN int_order_economics oe        ON oe.customer_id = c.customer_id
JOIN int_customer_order_sequence seq ON seq.order_id = oe.order_id
LEFT JOIN stg_reviews rv           ON rv.order_id = oe.order_id
GROUP BY c.customer_id, c.state, seq.lifetime_order_count;

-- fct_orders: order-grain mart used for the A/B test and dashboards
DROP VIEW IF EXISTS fct_orders;
CREATE VIEW fct_orders AS
SELECT
    ir.order_id,
    ir.customer_id,
    ir.order_value,
    ir.was_late,
    ir.review_score,
    ir.payment_type,
    ir.installments,
    ir.payment_quality_flag,
    seq.order_seq_num,
    CASE WHEN seq.order_seq_num > 1 THEN 1 ELSE 0 END AS is_repeat_order
FROM int_order_review ir
JOIN int_customer_order_sequence seq ON seq.order_id = ir.order_id;

-- Example analytical query referenced in the case study:
-- repeat-purchase rate and avg review score by delivery lateness.
-- SELECT
--     was_late,
--     COUNT(DISTINCT customer_id)                AS customers,
--     ROUND(AVG(is_repeat_order) * 100, 1)        AS repeat_rate_pct,
--     ROUND(AVG(review_score), 2)                 AS avg_review_score
-- FROM fct_orders
-- GROUP BY was_late;
