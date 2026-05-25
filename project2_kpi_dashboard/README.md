# Project 2 — Interactive KPI Dashboard

## What it does

A live Streamlit web dashboard for monitoring operational KPIs across departments. Features:

- **Sidebar filters** — select departments and month range interactively
- **Metric cards** — actual vs target for the latest month
- **Bar chart** — actual vs target comparison for all KPIs
- **Trend line** — any KPI's performance over the selected period
- **Anomaly alerts** — highlights KPIs deviating > threshold% from target (configurable)
- **Colour-coded table** — green rows = on target, red = below target

## Real-world problem

Operations and analytics teams use dashboards like this in daily stand-ups to spot underperforming metrics early — before they escalate into SLA breaches or revenue misses.

## How to run

```bash
cd project2_kpi_dashboard
streamlit run kpi_dashboard.py
```

Opens automatically at `http://localhost:8501`.

- If `data/project2/DataCoSupplyChainDataset.csv` exists (Kaggle), it loads and transforms that.
- Otherwise, it auto-generates `data/kpi_data.csv` via `generate_data.py`.

To pre-generate synthetic data:

```bash
python generate_data.py
```

## KPIs covered (synthetic mode)

| Department | KPIs |
|------------|------|
| Logistics | On-Time Delivery %, Avg Shipment Delay, Freight Cost/Unit, Orders Processed |
| Sales | Revenue, Conversion Rate, New Customers, Avg Deal Size |
| Operations | Process Efficiency %, Error Rate %, SLA Compliance %, Downtime (hrs) |

## Kaggle dataset

```bash
kaggle datasets download -d shashwatwork/dataco-smart-supply-chain-for-big-data-analysis -p ../data/project2 --unzip
```

Expected file: `data/project2/DataCoSupplyChainDataset.csv`
Columns used: `Order Date`, `Department Name`, `Sales`, `Order Item Quantity`, `Benefit per order`, `Late_delivery_risk`
