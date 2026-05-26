# Project 9 — PostgreSQL Operations Analytics

**Author:** Subham Joshi
**Stack:** PostgreSQL 18 · Python 3 · psycopg2 · pandas

---

## What It Does

Replicates the SQL-based operations analytics work done at **Logistics Integrators Pvt. Ltd.** using a real Kaggle supply chain dataset. The project covers the full pipeline: schema design → data loading → quality validation → advanced analysis → anomaly detection → KPI tracking → root cause analysis → CSV export.

---

## Real-World Problem It Solves

At Logistics Integrators, the operations team ran weekly SQL queries against a PostgreSQL instance to:
- Track on-time delivery rates across regions and shipping modes
- Detect anomalous orders (cost outliers, profit spikes, extreme delays)
- Perform root cause analysis when a region's late delivery rate spiked
- Report KPI scorecards to department heads every Monday

This project mirrors that exact workflow with real Kaggle logistics data.

---

## Dataset

- **DataCoSupplyChainDataset.csv** — 180,519 rows, 53 columns, encoding: latin-1
  - Source: Kaggle (used in place of company data under NDA)
  - Contains: orders, shipping, delivery status, profit, regions, departments

- **supply_chain_data.csv** — 100 rows, 24 columns (clean)
  - SKU-level data: suppliers, defect rates, stock levels, transport modes

---

## Run Order

```
1. Start PostgreSQL (localhost:5432)

2. Create the database:
   psql -U postgres -c "CREATE DATABASE logistics_analytics;"

3. Create tables:
   psql -U postgres -d logistics_analytics -f 01_create_tables.sql

4. Load data (update password in script if needed):
   python 02_load_data.py

5. Validate data quality:
   psql -U postgres -d logistics_analytics -f 03_data_cleaning.sql

6. Run analysis queries:
   psql -U postgres -d logistics_analytics -f 04_analysis_queries.sql

7. Run anomaly detection:
   psql -U postgres -d logistics_analytics -f 05_anomaly_detection.sql

8. Run KPI queries:
   psql -U postgres -d logistics_analytics -f 06_kpi_queries.sql

9. Run RCA queries:
   psql -U postgres -d logistics_analytics -f 07_rca_queries.sql

10. Export all results to CSV:
    python 08_export_results.py
```

---

## SQL Skills Demonstrated

| Technique | Files |
|---|---|
| Window functions (LAG, RANK, NTILE, SUM OVER, AVG OVER) | 04, 06, 07 |
| CTEs (WITH clauses) | 04, 05, 06, 07 |
| Statistical anomaly detection (Z-score, IQR) | 04, 05 |
| Rolling averages (ROWS BETWEEN) | 04, 06 |
| Cross-table JOINs with fuzzy matching | 04 |
| Conditional aggregation (CASE WHEN inside SUM/AVG) | 04, 06, 07 |
| PERCENTILE_CONT for IQR | 04, 05 |
| KPI threshold comparison with CROSS JOIN | 04, 06 |

---

## Outputs

All CSVs are written to `outputs/`:

| File | Description |
|---|---|
| `q01_monthly_revenue_mom.csv` | Monthly revenue with MoM growth |
| `q02_department_kpi_vs_target.csv` | Dept KPIs vs targets (RAG status) |
| `q03_shipping_cost_outliers.csv` | Z-score outliers on shipping cost |
| `q04_late_delivery_rca_region.csv` | Late delivery by region + mode |
| `q05_customer_segment_profitability.csv` | Profitability by segment |
| `q06_rolling_3m_revenue_by_dept.csv` | Rolling 3-month revenue |
| `q07_shipping_mode_performance.csv` | Mode benchmarking |
| `q08_top_delayed_routes.csv` | Worst 10 route + mode combos |
| `q09_weekly_kpi_summary.csv` | Weekly ops review data |
| `q10_market_performance_ranking.csv` | Market ranking with quartile |
| `q11_profit_anomaly_zscore.csv` | Profit anomalies by department |
| `q12_supply_chain_defect_impact.csv` | Defect rate × order impact |
| `q13_iqr_order_value_outliers.csv` | IQR outliers on order value |
| `q14_cumulative_revenue_by_dept.csv` | Cumulative revenue tracker |
| `q15_rca_summary_delay_causes.csv` | Comprehensive RCA summary |
| `project9_summary.txt` | Plain-text executive summary |
