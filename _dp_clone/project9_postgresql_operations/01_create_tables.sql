-- =============================================================================
-- Project 9: PostgreSQL Operations Analytics
-- File: 01_create_tables.sql
-- Author: Subham Joshi
-- Description: Create database schema for logistics analytics
--              Mirrors table design used at Logistics Integrators Pvt. Ltd.
-- Run Order: Step 1 — run this before loading any data
-- =============================================================================

-- Step 1: Create the database (run this connected to the 'postgres' default DB)
-- CREATE DATABASE logistics_analytics;

-- Step 2: Connect to logistics_analytics, then run the rest of this file.
-- \c logistics_analytics;

-- =============================================================================
-- TABLE 1: orders
-- Source: DataCoSupplyChainDataset.csv (180,519 rows, encoding: latin-1)
-- Stores transactional order-level data: sales, shipping, delivery, profit
-- =============================================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id            SERIAL PRIMARY KEY,
    order_date          DATE,
    ship_date           DATE,
    department_name     VARCHAR(100),
    category_name       VARCHAR(100),
    market              VARCHAR(50),
    order_region        VARCHAR(100),
    order_country       VARCHAR(100),
    customer_segment    VARCHAR(50),
    sales               NUMERIC(12,2),
    quantity            INTEGER,
    profit              NUMERIC(12,2),
    shipping_cost       NUMERIC(10,2),
    delivery_status     VARCHAR(50),
    late_delivery_risk  INTEGER,
    actual_ship_days    INTEGER,
    scheduled_ship_days INTEGER,
    shipping_mode       VARCHAR(50),
    product_name        VARCHAR(200),
    product_price       NUMERIC(10,2),
    order_item_discount NUMERIC(5,4),
    benefit_per_order   NUMERIC(12,2),
    order_status        VARCHAR(50)
);

-- =============================================================================
-- TABLE 2: supply_chain_ref
-- Source: supply_chain_data.csv (100 rows, clean)
-- SKU-level reference data: suppliers, defect rates, shipping, stock levels
-- =============================================================================
CREATE TABLE IF NOT EXISTS supply_chain_ref (
    sku                     VARCHAR(20) PRIMARY KEY,
    product_type            VARCHAR(50),
    price                   NUMERIC(10,2),
    availability            INTEGER,
    products_sold           INTEGER,
    revenue_generated       NUMERIC(12,2),
    customer_demographics   VARCHAR(50),
    stock_levels            INTEGER,
    lead_times              INTEGER,
    order_quantities        INTEGER,
    shipping_times          INTEGER,
    shipping_carrier        VARCHAR(20),
    shipping_costs          NUMERIC(10,2),
    supplier_name           VARCHAR(50),
    location                VARCHAR(50),
    lead_time               INTEGER,
    production_volumes      INTEGER,
    manufacturing_lead_time INTEGER,
    manufacturing_costs     NUMERIC(10,2),
    inspection_results      VARCHAR(20),
    defect_rates            NUMERIC(8,4),
    transportation_mode     VARCHAR(20),
    route                   VARCHAR(20),
    costs                   NUMERIC(12,2)
);

-- =============================================================================
-- TABLE 3: kpi_thresholds
-- Manual reference table defining KPI targets and warning levels
-- Used by analysis queries to classify performance as On Target / Warning / Critical
-- =============================================================================
CREATE TABLE IF NOT EXISTS kpi_thresholds (
    kpi_name        VARCHAR(100) PRIMARY KEY,
    target_value    NUMERIC(10,2),
    warning_value   NUMERIC(10,2),
    unit            VARCHAR(20)
);

-- Seed KPI thresholds (mirrors internal SLA definitions from Logistics Integrators)
INSERT INTO kpi_thresholds VALUES
    ('on_time_delivery_pct', 95.00, 85.00, 'percent'),
    ('avg_shipping_days',     3.00,  5.00, 'days'),
    ('avg_profit_margin',    20.00, 10.00, 'percent'),
    ('late_delivery_risk',    5.00, 15.00, 'percent'),
    ('avg_order_value',     200.00, 100.00, 'currency')
ON CONFLICT (kpi_name) DO NOTHING;

-- Confirm table creation
SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)))
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
