# Course 2 – Get Started with Python

**Google Advanced Data Analytics Certificate · Automatidata Project**

## Project Overview

EDA on the 2017 NYC Yellow Taxi trip dataset (408,294 rows, 18 columns)
for the New York City Taxi and Limousine Commission (TLC).

## Deliverables

| File | Description |
|------|-------------|
| `automatidata_eda.py` | Python EDA script: cleaning, feature engineering, 4 visualisations |
| `PACE_strategy_notes.md` | PACE framework notes (Plan, Analyze, Construct, Execute) |
| `executive_summary_notes.md` | Executive summary key findings and recommendations |

## Dataset

- **Source:** NYC TLC Yellow Taxi 2017 (Coursera / Google)
- **Rows:** 408,294 trips
- **Columns:** 18 (datetime, distance, fare, payment type, etc.)

## Key Findings

- Median trip duration: ~11–13 minutes
- Peak demand: 6–9 AM and 5–8 PM on weekdays
- ~0.5% of trips have zero distance but non-zero fare (flagged as anomalies)
- Credit card is the dominant payment method (~67%)
- Q3/Q4 show marginally higher average fares

## Outlier Strategy

- Raw data preserved in full
- IQR filtering applied only to analytical subsets
- Zero-distance trips flagged separately, not silently dropped

## Tools Used

- Python (Pandas, NumPy, Matplotlib, Seaborn)
- Tableau Public (scatter plot: Total Amount vs Trip Distance)
- PACE strategy framework
