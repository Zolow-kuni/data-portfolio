# Power BI Logistics Dashboard — Build Notes
**Project 10 | Subham Joshi**
Mirrors the weekly KPI monitoring dashboard used at Logistics Integrators Pvt. Ltd.

---

## Step 1 — Import Data into Power BI Desktop

Open Power BI Desktop → **Home → Get Data → Text/CSV**

Import all 4 files from the `outputs/` folder in this order:

| File | Table name in Power BI |
|---|---|
| `logistics_dashboard_data.csv` | `logistics_dashboard_data` |
| `kpi_monthly_summary.csv` | `kpi_monthly_summary` |
| `regional_performance.csv` | `regional_performance` |
| `delay_analysis.csv` | `delay_analysis` |

For each file: click **Transform Data** → verify column types → click **Close & Apply**.

Column type fixes to make in Power Query:
- `order_date`, `ship_date` → Date
- `sales`, `profit`, `shipping_cost`, `product_price` → Decimal Number
- `quantity`, `actual_ship_days`, `scheduled_ship_days` → Whole Number
- `year`, `month`, `week_number` → Whole Number
- `profit_margin_pct`, `on_time_pct`, `late_pct` → Decimal Number

---

## Step 2 — Create Relationships (Model View)

Go to **Model view** (left sidebar icon).

Create these relationships by dragging fields:

```
logistics_dashboard_data[month_year]   → kpi_monthly_summary[month_year]
logistics_dashboard_data[order_region] → regional_performance[order_region]
```

Cardinality: Many-to-One. Cross-filter direction: Single.

---

## Step 3 — Create DAX Measures

Click on `logistics_dashboard_data` table → **New Measure** for each:

```dax
Total Revenue =
SUM(logistics_dashboard_data[sales])

Total Profit =
SUM(logistics_dashboard_data[profit])

Total Orders =
COUNT(logistics_dashboard_data[order_id])

Overall Profit Margin % =
DIVIDE(
    SUM(logistics_dashboard_data[profit]),
    SUM(logistics_dashboard_data[sales])
) * 100

On Time Delivery % =
DIVIDE(
    SUM(logistics_dashboard_data[is_on_time]),
    COUNT(logistics_dashboard_data[order_id])
) * 100

Late Delivery % =
DIVIDE(
    SUM(logistics_dashboard_data[is_late]),
    COUNT(logistics_dashboard_data[order_id])
) * 100

Avg Delay Days =
AVERAGE(logistics_dashboard_data[delay_days])

Avg Shipping Cost =
AVERAGE(logistics_dashboard_data[shipping_cost])

Avg Order Value =
AVERAGE(logistics_dashboard_data[sales])

Revenue at Risk =
CALCULATE(
    SUM(logistics_dashboard_data[sales]),
    logistics_dashboard_data[is_late] = 1
)

MoM Revenue Growth % =
VAR current_month = SUM(kpi_monthly_summary[total_revenue])
VAR prev_month =
    CALCULATE(
        SUM(kpi_monthly_summary[total_revenue]),
        DATEADD(kpi_monthly_summary[month_year], -1, MONTH)
    )
RETURN DIVIDE(current_month - prev_month, prev_month) * 100
```

---

## Step 4 — Build Dashboard Pages

### PAGE 1 — Executive Overview

**Purpose:** Mirrors the weekly management report at Logistics Integrators.

**KPI Cards (top row — 6 cards):**
- Total Revenue → format: $#,##0.00
- Total Orders → format: #,##0
- On Time Delivery % → format: #,##0.0%  |  Target line: 95%
- Late Delivery % → format: #,##0.0%
- Avg Delay Days → format: #,##0.00
- Overall Profit Margin % → format: #,##0.0%

**Line Chart — Monthly Revenue Trend:**
- X-axis: `month_year` (from kpi_monthly_summary, sorted by year + month)
- Y-axis: `total_revenue`
- Secondary Y: `MoM Revenue Growth %`
- Title: "Monthly Revenue with MoM Growth"

**Donut Chart — Delivery Status Mix:**
- Legend: `delivery_status`
- Values: count of `order_id`
- Title: "On-Time vs Late vs Other"

**Bar Chart — Revenue by Department (Top 10):**
- Y-axis: `department_name`
- X-axis: `Total Revenue`
- Sort: descending by revenue
- Top N filter: 10

**Table — Weekly KPI Summary (Last 12 Weeks):**
- Columns: week_start, orders_processed, weekly_revenue, on_time_pct, late_risk_orders
- Data from: `q09_weekly_kpi_summary.csv` (add as 5th table if needed)
- Filter: Top 12 weeks by date

**Slicers:**
- `year` (dropdown)
- `quarter` (dropdown)
- `department_name` (list)
- `market` (list)

---

### PAGE 2 — Delay & Risk Analysis

**KPI Cards (top row — 4 cards):**
- Revenue at Risk → $#,##0.00
- Avg Delay Days
- Max delay (use MAX visual with `delay_days`)
- Late Delivery % (count)

**Bar Chart — Late Delivery % by Region:**
- Y-axis: `order_region`
- X-axis: `late_pct` (from regional_performance)
- Sort: descending
- Colour: conditional (red if > 50%, amber if > 30%)

**Stacked Bar — Delay Category by Shipping Mode:**
- X-axis: `shipping_mode`
- Legend: `delay_category`
- Values: count of orders
- Source: `delay_analysis`

**Scatter Plot — Shipping Cost vs Delay Days:**
- X-axis: `Avg Shipping Cost`
- Y-axis: `Avg Delay Days`
- Legend/Colour: `order_region`
- Size: `Total Revenue`

**Matrix — Region × Shipping Mode → Late %:**
- Rows: `order_region`
- Columns: `shipping_mode`
- Values: `Late Delivery %`
- Conditional formatting: background colour scale (green → red)

**Map Visual — Late Delivery Rate by Country:**
- Location: `order_country`
- Bubble size: `Late Delivery %`
- Colour saturation: `Total Revenue`
- Enable: Azure Maps or Bing Maps (requires internet)

**Slicers:**
- `shipping_mode` (list)
- `order_region` (dropdown)
- Date range slicer on `order_date`

---

### PAGE 3 — Department & Product Performance

**Bar Chart — Profit Margin % by Department:**
- Y-axis: `department_name`
- X-axis: `Overall Profit Margin %`
- Reference line at 20% (target)

**Line Chart — Monthly Profit Trend by Department:**
- X-axis: `month_year`
- Y-axis: `total_profit`
- Legend: `department_name`
- Source: `kpi_monthly_summary`
- Enable: multi-line, show markers

**Treemap — Revenue by Category and Department:**
- Group: `department_name`
- Sub-group: `category_name`
- Values: `Total Revenue`

**Table — Top 20 High-Value Orders:**
- Filter: `high_value_order = 1`
- Columns: order_date, department_name, product_name, sales, delivery_status, delay_category
- Sort: sales descending, Top 20

**Bar Chart — Avg Order Value by Customer Segment:**
- X-axis: `customer_segment`
- Y-axis: `Avg Order Value`

**KPI Cards:**
- High Value Orders (count where high_value_order = 1)
- Avg Shipping Cost per Unit (`shipping_cost_per_unit` average)

**Slicers:**
- `department_name`
- `category_name`
- `customer_segment`

---

### PAGE 4 — Operational KPI Tracker

**Purpose:** Mirrors the Logistics Integrators weekly ops performance board.

**KPI Cards with RAG indicators (5 cards):**

| KPI | Target | Warning | Format |
|---|---|---|---|
| On-Time Delivery % | 95% | 85% | #,##0.0% |
| Avg Shipping Days | ≤ 3 days | ≤ 5 days | #,##0.00 |
| Profit Margin % | 20% | 10% | #,##0.0% |
| Late Risk % | < 5% | < 15% | #,##0.0% |
| Avg Order Value | > $200 | > $100 | $#,##0.00 |

For each KPI card, use **conditional formatting** on the call-out value:
- Green: at or better than target
- Amber: between warning and target
- Red: below warning

**Gauge Charts (one per KPI):**
- Actual value as needle
- Min = 0, Max = target × 1.5
- Target value as goal line
- Colour zones: Red < warning, Amber < target, Green ≥ target

**Table — Department KPI Scorecard:**
- Source: `kpi_monthly_summary` (latest month)
- Columns: department_name, total_orders, on_time_pct, avg_delay_days, profit_margin_pct, late_pct, avg_order_value
- Conditional formatting on every KPI column (background colour)

**Trend arrows per KPI:**
- Create a measure like:
  ```dax
  On Time Trend =
  VAR curr = [On Time Delivery %]
  VAR prev = CALCULATE([On Time Delivery %], DATEADD(logistics_dashboard_data[order_date], -1, MONTH))
  RETURN IF(curr > prev, "↑", IF(curr < prev, "↓", "→"))
  ```
- Display as a card next to each gauge

**Slicers:**
- Month/Year slicer (tied to kpi_monthly_summary[month_year])
- Department slicer

---

## Step 5 — Formatting Standards

Apply these settings across all pages:

**Theme:** Custom
- Primary: `#1F4E79` (dark blue)
- Background: `#F2F2F2` (light grey)
- Accent: `#2E75B6`
- Text: `#1A1A1A`

**Import custom theme JSON:**
```json
{
  "name": "Logistics Analytics",
  "dataColors": ["#1F4E79","#2E75B6","#70AD47","#FFC000","#FF0000","#7030A0"],
  "background": "#F2F2F2",
  "foreground": "#1A1A1A",
  "tableAccent": "#2E75B6"
}
```
Save as `logistics_theme.json` and import via **View → Themes → Browse for themes**.

**Number formats:**
- Currency: `$#,##0.00`
- Percentage: `0.0%`
- Days: `0.00`
- Integer: `#,##0`

**Page navigation buttons:**
1. Insert → Buttons → Navigator → Page Navigator (Power BI will auto-generate)
   OR manually:
2. Insert → Buttons → Blank → set Action = Page Navigation → select target page
3. Style: Filled, dark blue, white text labels: "Overview", "Delay", "Products", "KPIs"
4. Place identically on every page (copy-paste)

**Footer (each page):**
- Insert → Text Box
- Content: `Logistics Analytics Dashboard  |  Data: Kaggle Supply Chain Dataset  |  Last Refreshed: `
- Add a **Card** visual next to it bound to `TODAY()` or `MAX(order_date)`

**Report title (each page):**
- Insert → Text Box → "Logistics Analytics Dashboard"
- Font: Segoe UI, 18pt, white, bold
- Background: `#1F4E79` rectangle shape behind it

---

## Step 6 — Publish (Optional)

1. File → Publish → Publish to Power BI Service
2. Select your workspace
3. Open in browser → pin visuals to a Dashboard
4. Set scheduled refresh if connected to a live data source

---

## Output Files Used by This Dashboard

| File | Rows (approx.) | Purpose |
|---|---|---|
| `logistics_dashboard_data.csv` | ~180,000 | Main fact table |
| `kpi_monthly_summary.csv` | varies | Monthly KPI aggregates |
| `regional_performance.csv` | varies | Region-level metrics |
| `delay_analysis.csv` | varies | Delay breakdown by mode/category |
