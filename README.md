# Data Portfolio 3 — Subham Joshi

Supply chain and logistics analytics portfolio built with real Kaggle datasets,
mirroring work done at **Logistics Integrators Pvt. Ltd.**

---

## Projects

### Project 9 — PostgreSQL Operations Analytics
**Stack:** PostgreSQL 18 · Python · psycopg2 · pandas

End-to-end SQL analytics pipeline: schema design, data loading (180K rows),
data quality validation, 15 advanced analysis queries (window functions, CTEs,
Z-score anomaly detection, IQR outliers, rolling averages, cross-table joins),
KPI tracking against thresholds, RCA drilldowns, and automated CSV export.

→ [View Project 9](project9_postgresql_operations/README.md)

---

### Project 10 — Power BI Logistics Dashboard
**Stack:** Python · pandas · Power BI Desktop · DAX

4-page interactive dashboard: Executive Overview, Delay & Risk Analysis,
Department & Product Performance, Operational KPI Tracker. Includes 10 DAX
measures, conditional RAG formatting, gauge charts, map visual, matrix heatmap,
and drill-through slicers — with step-by-step build notes.

→ [View Project 10](project10_powerbi_logistics/README.md)

---

## Datasets

| File | Rows | Description |
|---|---|---|
| DataCoSupplyChainDataset.csv | 180,519 | Multi-region logistics orders |
| supply_chain_data.csv | 100 | SKU-level supplier and defect data |

Both datasets from Kaggle, used under open license in place of NDA-protected company data.

---

## Run Order

```bash
# Install dependencies
pip install psycopg2-binary pandas

# Project 9
psql -U postgres -c "CREATE DATABASE logistics_analytics;"
psql -U postgres -d logistics_analytics -f project9_postgresql_operations/01_create_tables.sql
python project9_postgresql_operations/02_load_data.py
python project9_postgresql_operations/08_export_results.py

# Project 10
python project10_powerbi_logistics/01_clean_and_prepare.py
python project10_powerbi_logistics/02_feature_engineering.py
# Then open Power BI Desktop and follow 03_dashboard_notes.md
```
