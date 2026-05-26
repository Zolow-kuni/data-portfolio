# Project 10 — Power BI Logistics Dashboard

**Author:** Subham Joshi
**Stack:** Python 3 · pandas · Power BI Desktop · DAX

---

## What It Does

Builds a 4-page Power BI dashboard that replicates the **weekly KPI monitoring dashboard** used at Logistics Integrators Pvt. Ltd. The Python scripts clean the raw supply chain data and produce 3 optimised summary tables. The dashboard provides executives and operations managers with real-time visibility into delivery performance, cost variance, regional risk, and department-level KPIs.

---

## Real-World Problem It Solves

At Logistics Integrators, operations managers needed a single dashboard to:
- Monitor on-time delivery rates against the 95% SLA target
- Identify regions and shipping modes driving late deliveries
- Track weekly revenue and profit margin trends
- Surface high-risk orders and revenue at risk before week-end close

This project mirrors that exact dashboard, rebuilt with Kaggle data.

---

## Dataset

**DataCoSupplyChainDataset.csv** (180,519 rows, encoding: latin-1)
- Kaggle source, used in place of NDA-protected company data

---

## Run Order

```
1. Run cleaning pipeline:
   python 01_clean_and_prepare.py

2. Run feature engineering:
   python 02_feature_engineering.py

3. Open Power BI Desktop

4. Import all 4 CSV files from outputs/ as separate tables

5. Follow 03_dashboard_notes.md step-by-step to build the dashboard
```

---

## Output Files (inputs to Power BI)

| File | Rows (approx.) | Description |
|---|---|---|
| `logistics_dashboard_data.csv` | ~180,000 | Main cleaned fact table with all derived columns |
| `kpi_monthly_summary.csv` | varies | Monthly KPIs aggregated by department |
| `regional_performance.csv` | varies | Region-level delivery and revenue metrics |
| `delay_analysis.csv` | varies | Delay breakdown by mode, region, category |

---

## Derived Columns Added by Python

| Column | Logic |
|---|---|
| `delay_days` | actual_ship_days − scheduled_ship_days |
| `is_late` | 1 if delivery_status contains "Late" |
| `is_on_time` | 1 if delivery_status contains "Advance" or "on time" |
| `profit_margin_pct` | profit / sales × 100 |
| `shipping_cost_per_unit` | shipping_cost / quantity |
| `high_value_order` | 1 if sales > 500 |
| `delay_category` | On Time / Minor / Moderate / Major |
| `month_year` | e.g. "Jan-2016" for timeline axis |
| `quarter` | "Q1" through "Q4" |

---

## Dashboard Pages

| Page | Audience | Key Visuals |
|---|---|---|
| Executive Overview | C-suite, weekly review | Revenue trend, on-time KPI cards, department bar chart |
| Delay & Risk Analysis | Ops managers | Late % by region, delay heatmap matrix, scatter plot, map |
| Department & Product | Category managers | Profit margin by dept, treemap, top high-value orders |
| Operational KPI Tracker | Ops leads, daily standup | Gauge charts vs targets, RAG scorecard, trend arrows |

---

## DAX Measures

10 measures defined covering:
- Revenue, Profit, Margin %
- On-Time %, Late %, Avg Delay, Avg Shipping Cost
- Revenue at Risk
- MoM Revenue Growth %

See `03_dashboard_notes.md` for the full DAX code and step-by-step build guide.
