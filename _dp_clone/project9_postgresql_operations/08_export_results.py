"""
Project 9: PostgreSQL Operations Analytics
File: 08_export_results.py
Author: Subham Joshi
Description: Runs all 15 analysis queries, exports each as CSV to outputs/,
             and writes a plain-text summary report.
Run: python 08_export_results.py
Prerequisite: 02_load_data.py must have run successfully.
"""

import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from datetime import datetime
from pathlib import Path
import sys
import os

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── Config ────────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "dbname":   "logistics_analytics",
    "user":     "postgres",
    "password": "Shubham@12",
    "host":     "localhost",
    "port":     5432,
}
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── 15 Analysis Queries ───────────────────────────────────────────────────────
QUERIES = {
    "q01_monthly_revenue_mom": """
        WITH monthly_revenue AS (
            SELECT DATE_TRUNC('month', order_date) AS month,
                   SUM(sales)         AS total_revenue,
                   COUNT(*)           AS order_count,
                   ROUND(AVG(profit),2) AS avg_profit
            FROM orders GROUP BY DATE_TRUNC('month', order_date)
        )
        SELECT month, total_revenue, order_count, avg_profit,
               LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue,
               ROUND((total_revenue - LAG(total_revenue) OVER (ORDER BY month))
                     / NULLIF(LAG(total_revenue) OVER (ORDER BY month),0)*100,2)
                     AS mom_growth_pct
        FROM monthly_revenue ORDER BY month;
    """,

    "q02_department_kpi_vs_target": """
        WITH dept_kpis AS (
            SELECT department_name, COUNT(*) AS total_orders,
                   ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                                    OR delivery_status ILIKE '%advance%'
                                  THEN 1.0 ELSE 0 END)*100,2) AS on_time_pct,
                   ROUND(AVG(actual_ship_days),2)              AS avg_ship_days,
                   ROUND(SUM(sales),2)                         AS total_revenue,
                   ROUND(AVG(profit/NULLIF(sales,0))*100,2)   AS profit_margin_pct
            FROM orders GROUP BY department_name
        )
        SELECT d.*, k.target_value AS target_on_time,
               CASE WHEN d.on_time_pct >= k.target_value  THEN 'On Target'
                    WHEN d.on_time_pct >= k.warning_value THEN 'Warning'
                    ELSE 'Critical' END AS status
        FROM dept_kpis d
        CROSS JOIN kpi_thresholds k WHERE k.kpi_name='on_time_delivery_pct'
        ORDER BY on_time_pct DESC;
    """,

    "q03_shipping_cost_outliers": """
        WITH stats AS (
            SELECT AVG(shipping_cost) AS avg_cost, STDDEV(shipping_cost) AS std_cost
            FROM orders WHERE shipping_cost > 0
        )
        SELECT order_date, department_name, market,
               shipping_cost, actual_ship_days, delivery_status,
               ROUND((shipping_cost-stats.avg_cost)/stats.std_cost,2) AS z_score
        FROM orders, stats
        WHERE ABS(shipping_cost-stats.avg_cost) > 2.5*stats.std_cost
        ORDER BY z_score DESC LIMIT 50;
    """,

    "q04_late_delivery_rca_region": """
        SELECT order_region, order_country, shipping_mode,
               COUNT(*) AS total_orders,
               SUM(late_delivery_risk) AS late_orders,
               ROUND(SUM(late_delivery_risk)*100.0/COUNT(*),2) AS late_risk_pct,
               ROUND(AVG(actual_ship_days-scheduled_ship_days),2) AS avg_delay_days,
               ROUND(AVG(shipping_cost),2) AS avg_shipping_cost
        FROM orders
        GROUP BY order_region, order_country, shipping_mode
        HAVING COUNT(*) > 100
        ORDER BY late_risk_pct DESC LIMIT 20;
    """,

    "q05_customer_segment_profitability": """
        SELECT customer_segment, COUNT(*) AS total_orders,
               ROUND(SUM(sales),2)  AS total_revenue,
               ROUND(SUM(profit),2) AS total_profit,
               ROUND(AVG(profit/NULLIF(sales,0))*100,2) AS profit_margin_pct,
               ROUND(AVG(sales),2)  AS avg_order_value,
               RANK() OVER (ORDER BY SUM(profit) DESC) AS profit_rank
        FROM orders GROUP BY customer_segment ORDER BY total_profit DESC;
    """,

    "q06_rolling_3m_revenue_by_dept": """
        WITH monthly AS (
            SELECT department_name,
                   DATE_TRUNC('month', order_date) AS month,
                   SUM(sales) AS monthly_revenue
            FROM orders GROUP BY department_name, DATE_TRUNC('month', order_date)
        )
        SELECT department_name, month, monthly_revenue,
               ROUND(AVG(monthly_revenue) OVER (
                   PARTITION BY department_name ORDER BY month
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),2) AS rolling_3m_avg,
               ROUND(monthly_revenue - AVG(monthly_revenue) OVER (
                   PARTITION BY department_name ORDER BY month
                   ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),2) AS deviation_from_avg
        FROM monthly ORDER BY department_name, month;
    """,

    "q07_shipping_mode_performance": """
        SELECT shipping_mode, COUNT(*) AS total_shipments,
               ROUND(AVG(actual_ship_days),2)    AS avg_actual_days,
               ROUND(AVG(scheduled_ship_days),2) AS avg_scheduled_days,
               ROUND(AVG(actual_ship_days-scheduled_ship_days),2) AS avg_delay,
               ROUND(AVG(shipping_cost),2)        AS avg_cost,
               SUM(late_delivery_risk)            AS late_deliveries,
               ROUND(SUM(late_delivery_risk)*100.0/COUNT(*),2) AS late_pct
        FROM orders GROUP BY shipping_mode ORDER BY late_pct DESC;
    """,

    "q08_top_delayed_routes": """
        SELECT order_region, shipping_mode, COUNT(*) AS shipments,
               ROUND(AVG(actual_ship_days-scheduled_ship_days),2) AS avg_delay_days,
               MAX(actual_ship_days-scheduled_ship_days)          AS max_delay_days,
               ROUND(SUM(late_delivery_risk)*100.0/COUNT(*),2)    AS late_risk_pct,
               ROUND(SUM(sales),2)                                AS revenue_at_risk
        FROM orders
        GROUP BY order_region, shipping_mode
        HAVING COUNT(*) > 50
        ORDER BY avg_delay_days DESC LIMIT 10;
    """,

    "q09_weekly_kpi_summary": """
        SELECT DATE_TRUNC('week', order_date) AS week_start,
               COUNT(*) AS orders_processed,
               ROUND(SUM(sales),2)  AS weekly_revenue,
               ROUND(SUM(profit),2) AS weekly_profit,
               ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                                OR delivery_status ILIKE '%advance%'
                              THEN 1.0 ELSE 0 END)*100,2) AS on_time_pct,
               SUM(late_delivery_risk)      AS late_risk_orders,
               ROUND(AVG(shipping_cost),2)  AS avg_shipping_cost
        FROM orders
        GROUP BY DATE_TRUNC('week', order_date)
        ORDER BY week_start;
    """,

    "q10_market_performance_ranking": """
        SELECT market, COUNT(*) AS total_orders,
               ROUND(SUM(sales),2)  AS total_revenue,
               ROUND(SUM(profit),2) AS total_profit,
               ROUND(AVG(profit/NULLIF(sales,0))*100,2) AS margin_pct,
               RANK()   OVER (ORDER BY SUM(sales) DESC) AS revenue_rank,
               NTILE(4) OVER (ORDER BY SUM(sales) DESC) AS revenue_quartile
        FROM orders GROUP BY market ORDER BY total_revenue DESC;
    """,

    "q11_profit_anomaly_zscore": """
        WITH profit_stats AS (
            SELECT department_name, AVG(profit) AS avg_profit,
                   STDDEV(profit) AS std_profit
            FROM orders GROUP BY department_name
        )
        SELECT o.order_date, o.department_name, o.sales, o.profit,
               ROUND((o.profit-p.avg_profit)/NULLIF(p.std_profit,0),2) AS profit_z_score,
               CASE WHEN ABS((o.profit-p.avg_profit)/NULLIF(p.std_profit,0))>3
                    THEN 'High Anomaly'
                    WHEN ABS((o.profit-p.avg_profit)/NULLIF(p.std_profit,0))>2
                    THEN 'Moderate Anomaly' ELSE 'Normal' END AS anomaly_flag
        FROM orders o
        JOIN profit_stats p ON o.department_name=p.department_name
        WHERE ABS((o.profit-p.avg_profit)/NULLIF(p.std_profit,0)) > 2
        ORDER BY ABS((o.profit-p.avg_profit)/NULLIF(p.std_profit,0)) DESC
        LIMIT 100;
    """,

    "q12_supply_chain_defect_impact": """
        SELECT s.product_type, s.supplier_name, s.inspection_results,
               s.defect_rates, s.transportation_mode,
               COUNT(o.order_id)               AS related_orders,
               ROUND(AVG(o.shipping_cost),2)   AS avg_order_shipping_cost,
               ROUND(AVG(o.actual_ship_days),2) AS avg_delivery_days,
               ROUND(SUM(o.profit),2)           AS total_profit
        FROM supply_chain_ref s
        LEFT JOIN orders o
            ON LOWER(o.category_name) LIKE '%'||LOWER(s.product_type)||'%'
        GROUP BY s.product_type, s.supplier_name, s.inspection_results,
                 s.defect_rates, s.transportation_mode
        ORDER BY s.defect_rates DESC;
    """,

    "q13_iqr_order_value_outliers": """
        WITH iqr_calc AS (
            SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sales) AS q1,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sales) AS q3
            FROM orders
        )
        SELECT o.order_date, o.department_name, o.market,
               o.sales, o.quantity, o.delivery_status,
               CASE WHEN o.sales > iqr.q3+1.5*(iqr.q3-iqr.q1) THEN 'Upper Outlier'
                    ELSE 'Lower Outlier' END AS outlier_type
        FROM orders o, iqr_calc iqr
        WHERE o.sales > iqr.q3+1.5*(iqr.q3-iqr.q1)
           OR o.sales < iqr.q1-1.5*(iqr.q3-iqr.q1)
        ORDER BY o.sales DESC LIMIT 100;
    """,

    "q14_cumulative_revenue_by_dept": """
        SELECT department_name,
               DATE_TRUNC('month', order_date) AS month,
               SUM(sales) AS monthly_revenue,
               SUM(SUM(sales)) OVER (
                   PARTITION BY department_name
                   ORDER BY DATE_TRUNC('month', order_date)) AS cumulative_revenue,
               ROUND(SUM(sales)*100.0/SUM(SUM(sales)) OVER (
                   PARTITION BY department_name),2) AS pct_of_annual_revenue
        FROM orders
        GROUP BY department_name, DATE_TRUNC('month', order_date)
        ORDER BY department_name, month;
    """,

    "q15_rca_summary_delay_causes": """
        SELECT order_region, shipping_mode, department_name,
               COUNT(*) AS total_orders,
               SUM(late_delivery_risk) AS late_orders,
               ROUND(SUM(late_delivery_risk)*100.0/COUNT(*),2) AS late_pct,
               ROUND(AVG(actual_ship_days-scheduled_ship_days),2) AS avg_delay,
               ROUND(SUM(sales),2) AS revenue_impacted,
               ROUND(SUM(CASE WHEN late_delivery_risk=1 THEN profit ELSE 0 END),2)
                     AS profit_at_risk
        FROM orders
        GROUP BY order_region, shipping_mode, department_name
        HAVING COUNT(*) > 50
           AND SUM(late_delivery_risk)*100.0/COUNT(*) > 20
        ORDER BY late_pct DESC, revenue_impacted DESC
        LIMIT 20;
    """,
}

# ── Summary stats query ───────────────────────────────────────────────────────
SUMMARY_SQL = """
    SELECT
        COUNT(*) AS total_orders,
        MIN(order_date) AS date_from,
        MAX(order_date) AS date_to,
        COUNT(DISTINCT department_name) AS unique_departments,
        COUNT(DISTINCT market)          AS unique_markets,
        COUNT(DISTINCT order_country)   AS unique_countries,
        ROUND(AVG(CASE WHEN delivery_status ILIKE '%on time%'
                         OR delivery_status ILIKE '%advance%'
                       THEN 1.0 ELSE 0 END)*100, 2) AS on_time_pct,
        ROUND(AVG(profit/NULLIF(sales,0))*100, 2)   AS overall_margin_pct
    FROM orders;
"""

ANOMALY_COUNT_SQL = """
    WITH shipping_anomalies AS (
        SELECT COUNT(*) AS n FROM (
            WITH stats AS (SELECT AVG(shipping_cost) AS a, STDDEV(shipping_cost) AS s
                           FROM orders WHERE shipping_cost>0)
            SELECT 1 FROM orders, stats
            WHERE ABS(shipping_cost-stats.a) > 2.5*stats.s
        ) x
    ),
    profit_anomalies AS (
        SELECT COUNT(*) AS n FROM (
            WITH ps AS (SELECT department_name, AVG(profit) AS a, STDDEV(profit) AS s
                        FROM orders GROUP BY department_name)
            SELECT 1 FROM orders o JOIN ps p USING(department_name)
            WHERE ABS((o.profit-p.a)/NULLIF(p.s,0)) > 2
            LIMIT 100
        ) x
    ),
    iqr_anomalies AS (
        SELECT COUNT(*) AS n FROM (
            WITH iq AS (SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY sales) AS q1,
                               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY sales) AS q3
                        FROM orders)
            SELECT 1 FROM orders o, iq
            WHERE o.sales > iq.q3+1.5*(iq.q3-iq.q1)
               OR o.sales < iq.q1-1.5*(iq.q3-iq.q1)
            LIMIT 100
        ) x
    )
    SELECT (SELECT n FROM shipping_anomalies)
         + (SELECT n FROM profit_anomalies)
         + (SELECT n FROM iqr_anomalies) AS total_anomalies;
"""

TOP_DELAY_SQL = """
    SELECT order_region,
           ROUND(SUM(late_delivery_risk)*100.0/COUNT(*),2) AS late_pct
    FROM orders
    GROUP BY order_region
    ORDER BY late_pct DESC
    LIMIT 3;
"""


def main():
    log("Connecting to PostgreSQL ...")
    try:
        cfg = DB_CONFIG
        engine = create_engine(
            f"postgresql+psycopg2://{cfg['user']}:{quote_plus(cfg['password'])}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
        )
        conn = engine.connect()
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

    log("Running and exporting 15 analysis queries ...")
    results = []

    for query_name, sql in QUERIES.items():
        try:
            df = pd.read_sql_query(text(sql), conn)
            csv_path = OUTPUT_DIR / f"{query_name}.csv"
            df.to_csv(csv_path, index=False)
            results.append((query_name, len(df), csv_path.name))
            log(f"  OK {query_name}: {len(df)} rows -> {csv_path.name}")
        except Exception as e:
            log(f"  ERR {query_name}: {e}")
            results.append((query_name, "ERROR", str(e)))

    # ── Summary stats ─────────────────────────────────────────────────────────
    log("Generating summary stats ...")
    summary_df   = pd.read_sql_query(text(SUMMARY_SQL), conn)
    anomaly_df   = pd.read_sql_query(text(ANOMALY_COUNT_SQL), conn)
    top_delay_df = pd.read_sql_query(text(TOP_DELAY_SQL), conn)

    row          = summary_df.iloc[0]
    total_anomalies = anomaly_df.iloc[0]["total_anomalies"]
    top3_regions = " | ".join(
        f"{r['order_region']} ({r['late_pct']}%)" for _, r in top_delay_df.iterrows()
    )

    summary_txt = f"""
================================================================================
  PROJECT 9 — POSTGRESQL OPERATIONS ANALYTICS
  Export Summary — generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

DATABASE OVERVIEW
-----------------
  Total orders in database : {row['total_orders']:,}
  Date range               : {row['date_from']} to {row['date_to']}
  Unique departments        : {row['unique_departments']}
  Unique markets            : {row['unique_markets']}
  Unique countries          : {row['unique_countries']}

KPI SNAPSHOT
------------
  On-time delivery rate    : {row['on_time_pct']}%
  Overall profit margin    : {row['overall_margin_pct']}%

ANOMALY DETECTION
-----------------
  Total anomalies detected : {total_anomalies}
  (Q03 shipping cost z-score + Q11 profit z-score + Q13 IQR order value)

TOP 3 DELAYED REGIONS
----------------------
  {top3_regions}

EXPORTED FILES
--------------
""".lstrip()

    for qname, rcount, fname in results:
        summary_txt += f"  {fname:<50} {rcount} rows\n"

    summary_txt += "=" * 80 + "\n"

    summary_path = OUTPUT_DIR / "project9_summary.txt"
    summary_path.write_text(summary_txt, encoding="utf-8")
    log(f"Summary written → {summary_path}")

    conn.close()
    engine.dispose()

    # ── Print table ───────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  {'QUERY':<42} {'ROWS':>8}  {'FILE'}")
    print("=" * 65)
    for qname, rcount, fname in results:
        print(f"  {qname:<42} {str(rcount):>8}  {fname}")
    print("=" * 65)
    log("All exports complete.")


if __name__ == "__main__":
    main()
