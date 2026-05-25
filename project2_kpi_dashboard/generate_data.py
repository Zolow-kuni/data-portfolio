"""
generate_data.py — Project 2: Interactive KPI Dashboard
Generates 12 months of synthetic KPI data across 3 departments.
"""
import os
import numpy as np
import pandas as pd

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH      = os.path.join(PORTFOLIO_DIR, "data", "kpi_data.csv")

# KPI definitions: (kpi_id, display_name, target_value, unit)
KPIS = {
    "Logistics": [
        ("on_time_delivery_pct",  "On-Time Delivery %",    95.0,    "%"),
        ("shipment_delay_days",   "Avg Shipment Delay (d)", 1.5,    "days"),
        ("freight_cost_per_unit", "Freight Cost/Unit",       8.0,   "USD"),
        ("orders_processed",      "Orders Processed",      5000.0,  "units"),
    ],
    "Sales": [
        ("revenue",               "Revenue",              500000.0, "USD"),
        ("conversion_rate",       "Conversion Rate",          12.0, "%"),
        ("new_customers",         "New Customers",           200.0, "count"),
        ("avg_deal_size",         "Avg Deal Size",          2500.0, "USD"),
    ],
    "Operations": [
        ("process_efficiency_pct","Process Efficiency %",    90.0,  "%"),
        ("error_rate_pct",        "Error Rate %",             2.0,  "%"),
        ("sla_compliance_pct",    "SLA Compliance %",        98.0,  "%"),
        ("downtime_hours",        "Downtime (hours)",         5.0,  "hours"),
    ],
}


def generate(seed=42):
    rng = np.random.default_rng(seed)
    months = pd.date_range("2024-01", periods=12, freq="MS").strftime("%Y-%m").tolist()
    rows = []

    for dept, kpi_list in KPIS.items():
        for kpi_id, kpi_name, target, unit in kpi_list:
            trend = rng.uniform(-0.02, 0.04)   # slight upward or downward drift
            noise = rng.uniform(0.06, 0.14)    # month-to-month variability

            for t, month in enumerate(months):
                actual = target * (1 + trend * t + rng.normal(0, noise))
                # Randomly inject a dip or spike ~12% of the time
                if rng.random() < 0.12:
                    actual *= rng.choice([0.78, 1.28])
                rows.append({
                    "month":        month,
                    "department":   dept,
                    "kpi_id":       kpi_id,
                    "kpi_name":     kpi_name,
                    "actual_value": round(max(0.0, actual), 2),
                    "target_value": float(target),
                    "unit":         unit,
                })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"[generate_data] Wrote {len(df):,} rows → {OUT_PATH}")
    print(f"  Departments : {df['department'].nunique()}")
    print(f"  KPIs        : {df['kpi_name'].nunique()}")
    print(f"  Months      : {df['month'].nunique()}")
