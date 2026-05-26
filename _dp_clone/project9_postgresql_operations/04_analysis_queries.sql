-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 04_analysis_queries.sql
-- Author: Subham Joshi
-- Description: 15 advanced analytical queries covering window functions,
--              CTEs, anomaly detection, KPI tracking, and cross-table joins.
--              Mirrors the analytics SQL written at Logistics Integrators.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- Q01: Monthly revenue trend with month-over-month growth %
--      Used in the weekly executive review at Logistics Integrators
-- ─────────────────────────────────────────────────────────────────────────────
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        SUM(sales)         AS total_revenue,
        COUNT(*)           AS order_count,
        ROUND(AVG(profit), 2) AS avg_profit
    FROM orders
    GROUP BY DATE_TRUNC('month', order_date)
)
SELECT
    month,
    total_revenue,
    order_count,
    avg_profit,
    LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100, 2
    ) AS mom_growth_pct
FROM monthly_revenue
ORDER BY month;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q02: Department performance vs KPI targets
--      Classifies each department as On Target / Warning / Critical
-- ─────────────────────────────────────────────────────────────────────────────
WITH dept_kpis AS (
    SELECT
        department_name,
        COUNT(*) AS total_orders,
        ROUND(AVG(
            CASE WHEN delivery_status ILIKE '%on time%'
                   OR delivery_status ILIKE '%advance%' THEN 1.0 ELSE 0 END
        ) * 100, 2) AS on_time_pct,
        ROUND(AVG(actual_ship_days), 2) AS avg_ship_days,
        ROUND(SUM(sales), 2)            AS total_revenue,
        ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2) AS profit_margin_pct
    FROM orders
    GROUP BY department_name
)
SELECT
    d.*,
    k.target_value  AS target_on_time,
    CASE
        WHEN d.on_time_pct >= k.target_value  THEN 'On Target'
        WHEN d.on_time_pct >= k.warning_value THEN 'Warning'
        ELSE 'Critical'
    END AS status
FROM dept_kpis d
CROSS JOIN kpi_thresholds k
WHERE k.kpi_name = 'on_time_delivery_pct'
ORDER BY on_time_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q03: Anomaly detection — shipping cost outliers using Z-score
--      Orders beyond 2.5σ from mean shipping cost are flagged for review
-- ─────────────────────────────────────────────────────────────────────────────
WITH stats AS (
    SELECT
        AVG(shipping_cost)    AS avg_cost,
        STDDEV(shipping_cost) AS std_cost
    FROM orders
    WHERE shipping_cost > 0
)
SELECT
    order_date, department_name, market,
    shipping_cost, actual_ship_days, delivery_status,
    ROUND((shipping_cost - stats.avg_cost) / stats.std_cost, 2) AS z_score
FROM orders, stats
WHERE ABS(shipping_cost - stats.avg_cost) > 2.5 * stats.std_cost
ORDER BY z_score DESC
LIMIT 50;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q04: Late delivery root cause analysis by region
--      Identifies region + shipping mode combinations with highest delay rates
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_region,
    order_country,
    shipping_mode,
    COUNT(*)                                                    AS total_orders,
    SUM(late_delivery_risk)                                     AS late_orders,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)       AS late_risk_pct,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)       AS avg_delay_days,
    ROUND(AVG(shipping_cost), 2)                                AS avg_shipping_cost
FROM orders
GROUP BY order_region, order_country, shipping_mode
HAVING COUNT(*) > 100
ORDER BY late_risk_pct DESC
LIMIT 20;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q05: Customer segment profitability analysis with ranking
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    customer_segment,
    COUNT(*)                                        AS total_orders,
    ROUND(SUM(sales), 2)                            AS total_revenue,
    ROUND(SUM(profit), 2)                           AS total_profit,
    ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(sales), 2)                            AS avg_order_value,
    RANK() OVER (ORDER BY SUM(profit) DESC)         AS profit_rank
FROM orders
GROUP BY customer_segment
ORDER BY total_profit DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q06: Rolling 3-month average revenue by department
--      Used to smooth seasonality and identify persistent underperformers
-- ─────────────────────────────────────────────────────────────────────────────
WITH monthly AS (
    SELECT
        department_name,
        DATE_TRUNC('month', order_date) AS month,
        SUM(sales) AS monthly_revenue
    FROM orders
    GROUP BY department_name, DATE_TRUNC('month', order_date)
)
SELECT
    department_name,
    month,
    monthly_revenue,
    ROUND(AVG(monthly_revenue) OVER (
        PARTITION BY department_name
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_3m_avg,
    ROUND(monthly_revenue - AVG(monthly_revenue) OVER (
        PARTITION BY department_name
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS deviation_from_avg
FROM monthly
ORDER BY department_name, month;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q07: Shipping mode performance comparison
--      Benchmarks each mode on cost, speed, and late delivery rate
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    shipping_mode,
    COUNT(*)                                                     AS total_shipments,
    ROUND(AVG(actual_ship_days), 2)                              AS avg_actual_days,
    ROUND(AVG(scheduled_ship_days), 2)                           AS avg_scheduled_days,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)        AS avg_delay,
    ROUND(AVG(shipping_cost), 2)                                 AS avg_cost,
    SUM(late_delivery_risk)                                      AS late_deliveries,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)        AS late_pct
FROM orders
GROUP BY shipping_mode
ORDER BY late_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q08: Top 10 most delayed routes (region + shipping mode)
--      Revenue at risk = cumulative sales on all late-risk routes
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_region,
    shipping_mode,
    COUNT(*)                                                   AS shipments,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)      AS avg_delay_days,
    MAX(actual_ship_days - scheduled_ship_days)                AS max_delay_days,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)      AS late_risk_pct,
    ROUND(SUM(sales), 2)                                       AS revenue_at_risk
FROM orders
GROUP BY order_region, shipping_mode
HAVING COUNT(*) > 50
ORDER BY avg_delay_days DESC
LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q09: Weekly KPI summary — mirrors Logistics Integrators weekly ops review
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_TRUNC('week', order_date) AS week_start,
    COUNT(*)                       AS orders_processed,
    ROUND(SUM(sales), 2)           AS weekly_revenue,
    ROUND(SUM(profit), 2)          AS weekly_profit,
    ROUND(AVG(
        CASE WHEN delivery_status ILIKE '%on time%'
               OR delivery_status ILIKE '%advance%' THEN 1.0 ELSE 0 END
    ) * 100, 2) AS on_time_pct,
    SUM(late_delivery_risk)        AS late_risk_orders,
    ROUND(AVG(shipping_cost), 2)   AS avg_shipping_cost
FROM orders
GROUP BY DATE_TRUNC('week', order_date)
ORDER BY week_start;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q10: Market performance ranking with revenue quartile
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    market,
    COUNT(*)                                        AS total_orders,
    ROUND(SUM(sales), 2)                            AS total_revenue,
    ROUND(SUM(profit), 2)                           AS total_profit,
    ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2) AS margin_pct,
    RANK()  OVER (ORDER BY SUM(sales) DESC)         AS revenue_rank,
    NTILE(4) OVER (ORDER BY SUM(sales) DESC)        AS revenue_quartile
FROM orders
GROUP BY market
ORDER BY total_revenue DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q11: Profit anomaly detection using Z-score by department
--      Flags individual orders deviating >2σ from their department mean
-- ─────────────────────────────────────────────────────────────────────────────
WITH profit_stats AS (
    SELECT
        department_name,
        AVG(profit)    AS avg_profit,
        STDDEV(profit) AS std_profit
    FROM orders
    GROUP BY department_name
)
SELECT
    o.order_date,
    o.department_name,
    o.sales,
    o.profit,
    ROUND((o.profit - p.avg_profit) / NULLIF(p.std_profit, 0), 2) AS profit_z_score,
    CASE
        WHEN ABS((o.profit - p.avg_profit) / NULLIF(p.std_profit, 0)) > 3 THEN 'High Anomaly'
        WHEN ABS((o.profit - p.avg_profit) / NULLIF(p.std_profit, 0)) > 2 THEN 'Moderate Anomaly'
        ELSE 'Normal'
    END AS anomaly_flag
FROM orders o
JOIN profit_stats p ON o.department_name = p.department_name
WHERE ABS((o.profit - p.avg_profit) / NULLIF(p.std_profit, 0)) > 2
ORDER BY ABS((o.profit - p.avg_profit) / NULLIF(p.std_profit, 0)) DESC
LIMIT 100;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q12: Cross-table join — supply chain defect impact on order metrics
--      Joins supply_chain_ref to orders via product category matching
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    s.product_type,
    s.supplier_name,
    s.inspection_results,
    s.defect_rates,
    s.transportation_mode,
    COUNT(o.order_id)              AS related_orders,
    ROUND(AVG(o.shipping_cost), 2) AS avg_order_shipping_cost,
    ROUND(AVG(o.actual_ship_days), 2) AS avg_delivery_days,
    ROUND(SUM(o.profit), 2)        AS total_profit
FROM supply_chain_ref s
LEFT JOIN orders o
    ON LOWER(o.category_name) LIKE '%' || LOWER(s.product_type) || '%'
GROUP BY s.product_type, s.supplier_name, s.inspection_results,
         s.defect_rates, s.transportation_mode
ORDER BY s.defect_rates DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q13: IQR-based outlier detection on order value
--      Uses interquartile range instead of Z-score — more robust to skew
-- ─────────────────────────────────────────────────────────────────────────────
WITH iqr_calc AS (
    SELECT
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sales) AS q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sales) AS q3
    FROM orders
)
SELECT
    o.order_date, o.department_name, o.market,
    o.sales, o.quantity, o.delivery_status,
    CASE
        WHEN o.sales > iqr.q3 + 1.5 * (iqr.q3 - iqr.q1) THEN 'Upper Outlier'
        WHEN o.sales < iqr.q1 - 1.5 * (iqr.q3 - iqr.q1) THEN 'Lower Outlier'
    END AS outlier_type
FROM orders o, iqr_calc iqr
WHERE o.sales > iqr.q3 + 1.5 * (iqr.q3 - iqr.q1)
   OR o.sales < iqr.q1 - 1.5 * (iqr.q3 - iqr.q1)
ORDER BY o.sales DESC
LIMIT 100;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q14: Cumulative revenue and running totals by department
--      Tracks each department's cumulative share of annual revenue over time
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    department_name,
    DATE_TRUNC('month', order_date) AS month,
    SUM(sales) AS monthly_revenue,
    SUM(SUM(sales)) OVER (
        PARTITION BY department_name
        ORDER BY DATE_TRUNC('month', order_date)
    ) AS cumulative_revenue,
    ROUND(SUM(sales) * 100.0 / SUM(SUM(sales)) OVER (
        PARTITION BY department_name
    ), 2) AS pct_of_annual_revenue
FROM orders
GROUP BY department_name, DATE_TRUNC('month', order_date)
ORDER BY department_name, month;

-- ─────────────────────────────────────────────────────────────────────────────
-- Q15: Comprehensive RCA summary — top delay causes with revenue impact
--      Shows which region + mode + department combos are worst performers
--      and how much revenue and profit is at risk from those delays
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_region,
    shipping_mode,
    department_name,
    COUNT(*)                                                          AS total_orders,
    SUM(late_delivery_risk)                                           AS late_orders,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)            AS late_pct,
    ROUND(AVG(actual_ship_days - scheduled_ship_days), 2)            AS avg_delay,
    ROUND(SUM(sales), 2)                                             AS revenue_impacted,
    ROUND(SUM(CASE WHEN late_delivery_risk = 1 THEN profit ELSE 0 END), 2)
                                                                      AS profit_at_risk
FROM orders
GROUP BY order_region, shipping_mode, department_name
HAVING COUNT(*) > 50
   AND SUM(late_delivery_risk) * 100.0 / COUNT(*) > 20
ORDER BY late_pct DESC, revenue_impacted DESC
LIMIT 20;
