# Project 3 — Financial Data Integrity Checker

## What it does

Validates a financial records dataset against **10 business rules** and produces a scored integrity report.

| Rule | Type |
|------|------|
| No nulls in required fields | Critical |
| No duplicate `record_id` | Critical |
| Date format must be YYYY-MM-DD | Major |
| `delivery_date` after `date` | Major |
| `amount` > 0 | Critical |
| `amount` within 3 SDs of mean (outlier) | Minor |
| `currency` ∈ {INR, USD, EUR, GBP} | Major |
| `vendor_id` in reference vendor list | Critical |
| `payment_status` ∈ {paid, pending, overdue} | Major |
| All columns ≥ 95% non-null (completeness) | Minor |

An **overall integrity score** (0–100%, A–D grade) is printed at the end.

The dataset intentionally contains ~7% erroneous rows for realistic testing.

## Real-world problem

Finance ops teams run these checks before month-end close, during vendor onboarding, and as part of ETL pipelines. Catching bad records upstream prevents reconciliation failures downstream.

## How to run

```bash
cd project3_financial_integrity
python integrity_checker.py
```

- If `data/project3/financials.csv` exists (Kaggle), it maps that dataset to the standard schema and injects test errors.
- Otherwise, it auto-generates `data/financial_records.csv` via `generate_data.py`.

To generate synthetic data only:

```bash
python generate_data.py
```

## Outputs (`outputs/` folder)

| File | Description |
|------|-------------|
| `integrity_report.csv` | Rule-by-rule results with violation counts and sample IDs |
| `violations_by_rule.png` | Bar chart — violation count per rule |
| `rule_severity_pie.png` | Pie chart — rules passed vs failed |

## Kaggle dataset

```bash
kaggle datasets download -d atharvaarya25/financials -p ../data/project3 --unzip
```

Expected file: `data/project3/financials.csv`
Columns used: `Segment`, `Country`, `Product`, `Units Sold`, `Sale Price`, `Gross Sales`, `Date`
