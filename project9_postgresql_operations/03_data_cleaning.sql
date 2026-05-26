-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 03_data_cleaning.sql
-- Author: Subham Joshi
-- Description: Data quality validation queries run after loading.
--              Mirrors QA checks performed at Logistics Integrators Pvt. Ltd.
--              to validate every data pipeline load before analysis.
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Row count verification
--    Expected: ~180,000 orders, 100 supply chain SKUs
-- ─────────────────────────────────────────────────────────────────────────────
SELECT COUNT(*) AS total_rows FROM orders;
SELECT COUNT(*) AS ref_rows   FROM supply_chain_ref;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Null check on critical columns
--    Any non-zero here requires investigation before proceeding
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    COUNT(*) FILTER (WHERE order_date IS NULL)     AS null_dates,
    COUNT(*) FILTER (WHERE sales IS NULL)           AS null_sales,
    COUNT(*) FILTER (WHERE department_name IS NULL) AS null_dept,
    COUNT(*) FILTER (WHERE delivery_status IS NULL) AS null_status
FROM orders;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Duplicate order detection
--    Same date + dept + sales + quantity appearing more than once
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    order_date, department_name, sales, quantity,
    COUNT(*) AS dupes
FROM orders
GROUP BY order_date, department_name, sales, quantity
HAVING COUNT(*) > 1
ORDER BY dupes DESC
LIMIT 20;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Date range validation
--    Verify the loaded data spans the expected historical window
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    MIN(order_date) AS earliest_order,
    MAX(order_date) AS latest_order,
    MAX(order_date) - MIN(order_date) AS date_span_days
FROM orders;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Negative / zero value checks
--    Negative sales = data error; very negative profit may be valid returns
-- ─────────────────────────────────────────────────────────────────────────────
SELECT COUNT(*) AS negative_sales  FROM orders WHERE sales < 0;
SELECT COUNT(*) AS negative_profit FROM orders WHERE profit < -10000;
SELECT COUNT(*) AS zero_quantity   FROM orders WHERE quantity <= 0;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Delivery status category breakdown with percentages
--    Helps confirm expected distribution (on-time, late, cancelled)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    delivery_status,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM orders
GROUP BY delivery_status
ORDER BY count DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. Late delivery risk distribution
--    risk=1 should align with actual late delivery rates
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    late_delivery_risk,
    COUNT(*) AS orders,
    ROUND(AVG(actual_ship_days), 2) AS avg_ship_days
FROM orders
GROUP BY late_delivery_risk;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. Shipping days anomaly — orders that took 3× longer than scheduled
--    Flags extreme outliers that may indicate data entry errors
-- ─────────────────────────────────────────────────────────────────────────────
SELECT COUNT(*) AS suspicious_shipping
FROM orders
WHERE actual_ship_days > scheduled_ship_days * 3;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. Defect rate outliers in supply chain reference table
--    SKUs exceeding mean + 2σ defect rate need supplier investigation
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    sku, product_type, defect_rates, inspection_results
FROM supply_chain_ref
WHERE defect_rates > (
    SELECT AVG(defect_rates) + 2 * STDDEV(defect_rates)
    FROM supply_chain_ref
)
ORDER BY defect_rates DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. Stock level alerts
--     SKUs with stock < 10 units are at risk of fulfilment failure
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    sku, product_type, stock_levels, lead_times, supplier_name
FROM supply_chain_ref
WHERE stock_levels < 10
ORDER BY stock_levels ASC;
