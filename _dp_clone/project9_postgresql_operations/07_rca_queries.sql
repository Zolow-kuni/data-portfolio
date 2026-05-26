-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 07_rca_queries.sql
-- Author: Subham Joshi
-- Description: Root Cause Analysis queries for delivery delays and cost overruns.
--              Structured as a drilldown: fleet → region → route → SKU → supplier.
--              Mirrors the RCA methodology used at Logistics Integrators Pvt. Ltd.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-1: Top-level — which shipping mode causes the most delay?
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    shipping_mode,
    COUNT(*)                                                    AS total_orders,
    SUM(late_delivery_risk)                                     AS late_count,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)       AS late_pct,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)       AS avg_delay_days,
    MAX(actual_ship_days - scheduled_ship_days)                 AS max_delay_days,
    ROUND(SUM(CASE WHEN late_delivery_risk=1 THEN sales ELSE 0 END), 2) AS revenue_at_risk
FROM orders
GROUP BY shipping_mode
ORDER BY late_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-2: Drilldown — late delivery by region within each shipping mode
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    shipping_mode,
    order_region,
    COUNT(*)                                                    AS orders,
    SUM(late_delivery_risk)                                     AS late_orders,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)       AS late_pct,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)       AS avg_delay_days,
    ROUND(AVG(shipping_cost), 2)                                AS avg_shipping_cost
FROM orders
GROUP BY shipping_mode, order_region
HAVING COUNT(*) > 30
ORDER BY shipping_mode, late_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-3: Cost overrun analysis — where is shipping cost vs profit ratio worst?
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_region,
    department_name,
    shipping_mode,
    COUNT(*)                                                    AS orders,
    ROUND(SUM(shipping_cost), 2)                               AS total_shipping_cost,
    ROUND(SUM(profit), 2)                                      AS total_profit,
    ROUND(SUM(shipping_cost) / NULLIF(SUM(profit), 0) * 100, 2) AS shipping_cost_pct_of_profit,
    ROUND(AVG(shipping_cost / NULLIF(sales, 0)) * 100, 2)     AS shipping_pct_of_sales
FROM orders
GROUP BY order_region, department_name, shipping_mode
HAVING COUNT(*) > 50
ORDER BY shipping_cost_pct_of_profit DESC
LIMIT 20;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-4: Product category delay pattern
--        Identifies if specific categories are systematically delayed
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    category_name,
    COUNT(*)                                                    AS orders,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)       AS avg_delay_days,
    SUM(late_delivery_risk)                                     AS late_count,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)       AS late_pct,
    ROUND(AVG(shipping_cost), 2)                                AS avg_shipping_cost,
    ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2)             AS avg_profit_margin
FROM orders
GROUP BY category_name
ORDER BY late_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-5: Supply chain link — which suppliers have high defect rates
--        AND correspond to high-delay order categories?
-- ─────────────────────────────────────────────────────────────────────────────
WITH defective AS (
    SELECT supplier_name, product_type, defect_rates, inspection_results,
           transportation_mode, lead_times, manufacturing_lead_time
    FROM supply_chain_ref
    WHERE defect_rates > (
        SELECT AVG(defect_rates) FROM supply_chain_ref
    )
),
order_delays AS (
    SELECT
        category_name,
        ROUND(AVG(actual_ship_days - scheduled_ship_days), 2) AS avg_delay,
        ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_pct,
        COUNT(*) AS orders
    FROM orders
    GROUP BY category_name
)
SELECT
    d.supplier_name,
    d.product_type,
    ROUND(d.defect_rates::NUMERIC, 4)   AS defect_rate,
    d.inspection_results,
    d.transportation_mode,
    d.lead_times                         AS supplier_lead_time,
    o.avg_delay                          AS order_avg_delay_days,
    o.late_pct                           AS order_late_pct,
    o.orders                             AS matched_orders
FROM defective d
JOIN order_delays o
    ON LOWER(o.category_name) LIKE '%' || LOWER(d.product_type) || '%'
ORDER BY d.defect_rates DESC, o.late_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-6: Seasonal delay pattern — does delay worsen in certain months?
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_PART('month', order_date)    AS month_num,
    TO_CHAR(order_date, 'Mon')         AS month_name,
    COUNT(*)                           AS orders,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2) AS avg_delay_days,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_pct,
    ROUND(AVG(shipping_cost), 2)       AS avg_shipping_cost
FROM orders
GROUP BY DATE_PART('month', order_date), TO_CHAR(order_date, 'Mon')
ORDER BY month_num;

-- ─────────────────────────────────────────────────────────────────────────────
-- RCA-7: High-delay region × department combinations with revenue impact
--        Drives remediation prioritisation: fix highest-revenue-at-risk first
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_region,
    department_name,
    COUNT(*)                                                        AS orders,
    SUM(late_delivery_risk)                                         AS late_orders,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)           AS late_pct,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)           AS avg_delay_days,
    ROUND(SUM(CASE WHEN late_delivery_risk = 1 THEN sales ELSE 0 END), 2) AS revenue_at_risk,
    ROUND(SUM(CASE WHEN late_delivery_risk = 1 THEN profit ELSE 0 END), 2) AS profit_at_risk
FROM orders
GROUP BY order_region, department_name
HAVING COUNT(*) > 100
   AND SUM(late_delivery_risk) * 100.0 / COUNT(*) > 30
ORDER BY revenue_at_risk DESC
LIMIT 20;
