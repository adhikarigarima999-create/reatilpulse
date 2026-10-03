-- ============================================================
-- 03_marts_pg.sql
-- Mart layer for PostgreSQL
-- ============================================================

DROP VIEW IF EXISTS fct_customers CASCADE;
CREATE VIEW fct_customers AS
SELECT
    c.customer_id,
    c.state,
    seq.lifetime_order_count,
    CASE WHEN seq.lifetime_order_count > 1 THEN 1 ELSE 0 END AS is_repeat_customer,
    ROUND(AVG(oe.order_value)::numeric, 2)          AS avg_order_value,
    ROUND(SUM(oe.order_value)::numeric, 2)          AS lifetime_value,
    ROUND((AVG(oe.was_late) * 100)::numeric, 1)     AS pct_orders_late,
    ROUND(AVG(rv.review_score)::numeric, 2)         AS avg_review_score,
    MIN(oe.purchase_ts)                              AS first_purchase_ts,
    MAX(oe.purchase_ts)                              AS last_purchase_ts
FROM stg_customers c
JOIN int_order_economics oe        ON oe.customer_id = c.customer_id
JOIN int_customer_order_sequence seq ON seq.order_id = oe.order_id
LEFT JOIN stg_reviews rv           ON rv.order_id = oe.order_id
GROUP BY c.customer_id, c.state, seq.lifetime_order_count;

DROP VIEW IF EXISTS fct_orders CASCADE;
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
