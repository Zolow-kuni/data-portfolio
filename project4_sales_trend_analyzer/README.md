# Project 4 — Sales & Inventory Trend Analyzer

## What it does

Analyses 2 years of monthly sales and inventory data to surface trends, anomalies, and stock risks:

| Analysis | Description |
|----------|-------------|
| **MoM growth** | Month-over-month % change in revenue and units sold |
| **Rolling average** | 3-month smoothed baseline for each metric |
| **Anomaly detection** | Flags months where revenue deviates > 15% from the rolling average |
| **Low stock alerts** | Products whose current stock falls below their reorder point |
| **Regional ranking** | Revenue rank per region for each month |
| **Seasonal decomposition** | Identifies which calendar months consistently over/under-perform |

## Real-world problem

Supply chain and merchandise planning teams use trend analysis like this to decide reorder quantities, plan promotions, and spot demand shifts before stockouts occur.

## How to run

```bash
cd project4_sales_trend_analyzer
python trend_analyzer.py
```

- If `data/project4/Sample - Superstore.csv` (or similar) exists (Kaggle), it loads that.
- Otherwise, it auto-generates `data/sales_inventory.csv` via `generate_data.py`.

To pre-generate synthetic data:

```bash
python generate_data.py
```

## Outputs (`outputs/` folder)

| File | Description |
|------|-------------|
| `trend_report.csv` | Monthly revenue, MoM growth, rolling avg, anomaly flags |
| `revenue_trend.png` | Line chart with rolling avg overlay and anomaly markers |
| `regional_revenue.png` | Grouped bar chart — revenue by region and category (last 6 months) |
| `revenue_heatmap.png` | Heatmap — month × product category revenue matrix |
| `low_stock_alert.png` | Table of products currently below their reorder point |

## Kaggle dataset

```bash
kaggle datasets download -d vivek468/superstore-dataset-final -p ../data/project4 --unzip
```

Expected file: `data/project4/Sample - Superstore.csv`
Columns used: `Order Date`, `Category`, `Sub-Category`, `Region`, `Sales`, `Quantity`, `Profit`
