-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 06_kpi_queries.sql
-- Author: Subham Joshi
-- Description: KPI tracking queries — measures all 5 defined KPIs against
--              thresholds, generates department scorecards, and tracks
--              weekly KPI trend. Mirrors the Logistics Integrators ops dashboard.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- K1: Overall KPI summary — current values vs targets
-- ─────────────────────────────────────────────────────────────────────────────
WITH overall AS (
    SELECT
        ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                         OR delivery_status ILIKE '%advance%'
                       THEN 1.0 ELSE 0 END) * 100, 2) AS on_time_pct,
        ROUND(AVG(actual_ship_days), 2)                AS avg_ship_days,
        ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2) AS avg_profit_margin,
        ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_risk_pct,
        ROUND(AVG(sales), 2)                           AS avg_order_value
    FROM orders
)
SELECT
    'on_time_delivery_pct'    AS kpi_name, o.on_time_pct   AS actual_value,
    k1.target_value, k1.warning_value,
    CASE WHEN o.on_time_pct >= k1.target_value  THEN 'Green'
         WHEN o.on_time_pct >= k1.warning_value THEN 'Amber'
         ELSE 'Red' END AS rag_status
FROM overall o, kpi_thresholds k1 WHERE k1.kpi_name = 'on_time_delivery_pct'
UNION ALL
SELECT
    'avg_shipping_days', o.avg_ship_days, k2.target_value, k2.warning_value,
    CASE WHEN o.avg_ship_days <= k2.target_value  THEN 'Green'
         WHEN o.avg_ship_days <= k2.warning_value THEN 'Amber'
         ELSE 'Red' END
FROM overall o, kpi_thresholds k2 WHERE k2.kpi_name = 'avg_shipping_days'
UNION ALL
SELECT
    'avg_profit_margin', o.avg_profit_margin, k3.target_value, k3.warning_value,
    CASE WHEN o.avg_profit_margin >= k3.target_value  THEN 'Green'
         WHEN o.avg_profit_margin >= k3.warning_value THEN 'Amber'
         ELSE 'Red' END
FROM overall o, kpi_thresholds k3 WHERE k3.kpi_name = 'avg_profit_margin'
UNION ALL
SELECT
    'late_delivery_risk', o.late_risk_pct, k4.target_value, k4.warning_value,
    CASE WHEN o.late_risk_pct <= k4.target_value  THEN 'Green'
         WHEN o.late_risk_pct <= k4.warning_value THEN 'Amber'
         ELSE 'Red' END
FROM overall o, kpi_thresholds k4 WHERE k4.kpi_name = 'late_delivery_risk'
UNION ALL
SELECT
    'avg_order_value', o.avg_order_value, k5.target_value, k5.warning_value,
    CASE WHEN o.avg_order_value >= k5.target_value  THEN 'Green'
         WHEN o.avg_order_value >= k5.warning_value THEN 'Amber'
         ELSE 'Red' END
FROM overall o, kpi_thresholds k5 WHERE k5.kpi_name = 'avg_order_value';

-- ─────────────────────────────────────────────────────────────────────────────
-- K2: Full department KPI scorecard — all 5 KPIs in one view
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    department_name,
    COUNT(*)                                                            AS total_orders,
    ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                     OR delivery_status ILIKE '%advance%'
                   THEN 1.0 ELSE 0 END) * 100, 2)                     AS on_time_pct,
    ROUND(AVG(actual_ship_days), 2)                                    AS avg_ship_days,
    ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2)                    AS profit_margin_pct,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)              AS late_risk_pct,
    ROUND(AVG(sales), 2)                                               AS avg_order_value,
    ROUND(SUM(sales), 2)                                               AS total_revenue,
    -- RAG status per KPI
    CASE WHEN AVG(CASE WHEN delivery_status ILIKE '%on time%'
                         OR delivery_status ILIKE '%advance%'
                       THEN 1.0 ELSE 0 END) * 100 >= 95 THEN 'G'
         WHEN AVG(CASE WHEN delivery_status ILIKE '%on time%'
                         OR delivery_status ILIKE '%advance%'
                       THEN 1.0 ELSE 0 END) * 100 >= 85 THEN 'A'
         ELSE 'R' END                                                  AS on_time_rag,
    CASE WHEN AVG(profit / NULLIF(sales, 0)) * 100 >= 20 THEN 'G'
         WHEN AVG(profit / NULLIF(sales, 0)) * 100 >= 10 THEN 'A'
         ELSE 'R' END                                                  AS margin_rag
FROM orders
GROUP BY department_name
ORDER BY on_time_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- K3: Weekly KPI trend — last 12 weeks with MoW change arrows
-- ─────────────────────────────────────────────────────────────────────────────
WITH weekly_kpi AS (
    SELECT
        DATE_TRUNC('week', order_date) AS week,
        COUNT(*)                       AS orders,
        ROUND(SUM(sales), 2)           AS revenue,
        ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                         OR delivery_status ILIKE '%advance%'
                       THEN 1.0 ELSE 0 END) * 100, 2) AS on_time_pct,
        ROUND(AVG(profit / NULLIF(sales, 0)) * 100, 2) AS margin_pct,
        ROUND(AVG(actual_ship_days), 2) AS avg_ship_days
    FROM orders
    GROUP BY DATE_TRUNC('week', order_date)
)
SELECT
    week,
    orders,
    revenue,
    on_time_pct,
    margin_pct,
    avg_ship_days,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY week), 2) AS revenue_wow_change,
    CASE WHEN on_time_pct > LAG(on_time_pct) OVER (ORDER BY week) THEN '↑'
         WHEN on_time_pct < LAG(on_time_pct) OVER (ORDER BY week) THEN '↓'
         ELSE '→' END                                     AS on_time_trend
FROM weekly_kpi
ORDER BY week DESC
LIMIT 12;

-- ─────────────────────────────────────────────────────────────────────────────
-- K4: On-time delivery breakdown by shipping mode + market
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    shipping_mode,
    market,
    COUNT(*)                                                              AS orders,
    ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                     OR delivery_status ILIKE '%advance%'
                   THEN 1.0 ELSE 0 END) * 100, 2)                       AS on_time_pct,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2)                AS late_risk_pct,
    ROUND(AVG(shipping_cost), 2)                                          AS avg_cost
FROM orders
GROUP BY shipping_mode, market
ORDER BY on_time_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- K5: Revenue per order trend by quarter — used in QBR presentations
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    DATE_PART('year',    order_date)    AS year,
    DATE_PART('quarter', order_date)    AS quarter,
    COUNT(*)                            AS orders,
    ROUND(SUM(sales), 2)               AS quarterly_revenue,
    ROUND(AVG(sales), 2)               AS avg_order_value,
    ROUND(AVG(profit / NULLIF(sales,0)) * 100, 2) AS profit_margin_pct,
    SUM(late_delivery_risk)             AS late_orders,
    ROUND(SUM(late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_pct
FROM orders
GROUP BY DATE_PART('year', order_date), DATE_PART('quarter', order_date)
ORDER BY year, quarter;
