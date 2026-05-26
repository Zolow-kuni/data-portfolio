-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 05_anomaly_detection.sql
-- Author: Subham Joshi
-- Description: Dedicated anomaly detection queries — Z-score, IQR, rolling
--              baseline deviation, and multi-dimensional flagging.
--              Mirrors anomaly alert logic used at Logistics Integrators.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- A1: Z-score anomaly detection on shipping cost (global baseline)
-- ─────────────────────────────────────────────────────────────────────────────
WITH global_stats AS (
    SELECT
        AVG(shipping_cost)    AS mean_cost,
        STDDEV(shipping_cost) AS sd_cost
    FROM orders WHERE shipping_cost > 0
)
SELECT
    order_id,
    order_date,
    department_name,
    market,
    shipping_cost,
    ROUND((shipping_cost - g.mean_cost) / NULLIF(g.sd_cost, 0), 3) AS z_score,
    CASE
        WHEN ABS((shipping_cost - g.mean_cost) / NULLIF(g.sd_cost, 0)) > 3 THEN 'Extreme'
        WHEN ABS((shipping_cost - g.mean_cost) / NULLIF(g.sd_cost, 0)) > 2 THEN 'High'
        ELSE 'Moderate'
    END AS severity
FROM orders, global_stats g
WHERE ABS((shipping_cost - g.mean_cost) / NULLIF(g.sd_cost, 0)) > 2
ORDER BY z_score DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- A2: Department-scoped profit anomaly (Z-score per department)
-- ─────────────────────────────────────────────────────────────────────────────
WITH dept_stats AS (
    SELECT department_name,
           AVG(profit)    AS mean_profit,
           STDDEV(profit) AS sd_profit
    FROM orders
    GROUP BY department_name
)
SELECT
    o.order_id,
    o.order_date,
    o.department_name,
    o.sales,
    o.profit,
    ROUND((o.profit - d.mean_profit) / NULLIF(d.sd_profit, 0), 3) AS z_score,
    CASE
        WHEN ABS((o.profit - d.mean_profit) / NULLIF(d.sd_profit, 0)) > 3 THEN 'Extreme'
        ELSE 'High'
    END AS severity
FROM orders o
JOIN dept_stats d USING (department_name)
WHERE ABS((o.profit - d.mean_profit) / NULLIF(d.sd_profit, 0)) > 2.5
ORDER BY ABS((o.profit - d.mean_profit) / NULLIF(d.sd_profit, 0)) DESC
LIMIT 200;

-- ─────────────────────────────────────────────────────────────────────────────
-- A3: IQR-based outlier detection on sales order value
-- ─────────────────────────────────────────────────────────────────────────────
WITH bounds AS (
    SELECT
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sales) AS q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sales) AS q3
    FROM orders
),
fence AS (
    SELECT q1, q3,
           q1 - 1.5 * (q3 - q1) AS lower_fence,
           q3 + 1.5 * (q3 - q1) AS upper_fence
    FROM bounds
)
SELECT
    o.order_id, o.order_date, o.department_name,
    o.market, o.sales, o.quantity,
    f.lower_fence, f.upper_fence,
    CASE
        WHEN o.sales > f.upper_fence THEN 'Upper Outlier'
        ELSE 'Lower Outlier'
    END AS outlier_direction
FROM orders o, fence f
WHERE o.sales > f.upper_fence OR o.sales < f.lower_fence
ORDER BY o.sales DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- A4: Shipping delay spike detection vs rolling monthly average
--     Flags weeks where avg delay is >50% above the rolling 4-week baseline
-- ─────────────────────────────────────────────────────────────────────────────
WITH weekly AS (
    SELECT
        DATE_TRUNC('week', order_date) AS week,
        ROUND(AVG(actual_ship_days - scheduled_ship_days), 2) AS avg_delay
    FROM orders
    GROUP BY DATE_TRUNC('week', order_date)
),
rolling AS (
    SELECT
        week,
        avg_delay,
        ROUND(AVG(avg_delay) OVER (
            ORDER BY week
            ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING
        ), 2) AS rolling_4w_baseline
    FROM weekly
)
SELECT
    week,
    avg_delay,
    rolling_4w_baseline,
    ROUND(avg_delay - rolling_4w_baseline, 2)             AS spike_above_baseline,
    ROUND((avg_delay - rolling_4w_baseline)
          / NULLIF(rolling_4w_baseline, 0) * 100, 1)     AS pct_above_baseline
FROM rolling
WHERE avg_delay > rolling_4w_baseline * 1.5
  AND rolling_4w_baseline IS NOT NULL
ORDER BY pct_above_baseline DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- A5: Multi-dimensional risk flag — orders meeting multiple anomaly criteria
--     High shipping cost AND late AND high delay → compound risk flag
-- ─────────────────────────────────────────────────────────────────────────────
WITH thresholds AS (
    SELECT
        AVG(shipping_cost) + STDDEV(shipping_cost)          AS high_ship_cost,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY actual_ship_days - scheduled_ship_days)
                                                              AS p75_delay
    FROM orders WHERE shipping_cost > 0
)
SELECT
    o.order_id,
    o.order_date,
    o.department_name,
    o.order_region,
    o.shipping_mode,
    o.sales,
    o.shipping_cost,
    o.actual_ship_days - o.scheduled_ship_days AS delay_days,
    o.delivery_status,
    (CASE WHEN o.shipping_cost > t.high_ship_cost THEN 1 ELSE 0 END
   + CASE WHEN o.late_delivery_risk = 1              THEN 1 ELSE 0 END
   + CASE WHEN o.actual_ship_days - o.scheduled_ship_days > t.p75_delay THEN 1 ELSE 0 END
    ) AS risk_score,
    CASE
        WHEN (CASE WHEN o.shipping_cost > t.high_ship_cost THEN 1 ELSE 0 END
            + CASE WHEN o.late_delivery_risk = 1              THEN 1 ELSE 0 END
            + CASE WHEN o.actual_ship_days - o.scheduled_ship_days > t.p75_delay THEN 1 ELSE 0 END) = 3
        THEN 'Critical'
        WHEN (CASE WHEN o.shipping_cost > t.high_ship_cost THEN 1 ELSE 0 END
            + CASE WHEN o.late_delivery_risk = 1              THEN 1 ELSE 0 END
            + CASE WHEN o.actual_ship_days - o.scheduled_ship_days > t.p75_delay THEN 1 ELSE 0 END) = 2
        THEN 'High'
        ELSE 'Moderate'
    END AS compound_risk
FROM orders o, thresholds t
WHERE (CASE WHEN o.shipping_cost > t.high_ship_cost THEN 1 ELSE 0 END
     + CASE WHEN o.late_delivery_risk = 1              THEN 1 ELSE 0 END
     + CASE WHEN o.actual_ship_days - o.scheduled_ship_days > t.p75_delay THEN 1 ELSE 0 END) >= 2
ORDER BY risk_score DESC, o.sales DESC
LIMIT 100;
