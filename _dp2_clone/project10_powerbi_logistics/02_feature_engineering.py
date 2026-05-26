"""
Project 10: Power BI Logistics Dashboard
File: 02_feature_engineering.py
Author: Subham Joshi
Description: Reads the cleaned fact table and produces 3 summary tables
             optimised for direct import into Power BI.
Run: python 02_feature_engineering.py
Prerequisite: 01_clean_and_prepare.py must have run successfully.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "outputs"
INPUT_CSV  = OUTPUT_DIR / "logistics_dashboard_data.csv"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def load_fact() -> pd.DataFrame:
    log(f"Loading fact table from {INPUT_CSV} ...")
    df = pd.read_csv(INPUT_CSV, low_memory=False,
                     parse_dates=["order_date", "ship_date"])
    log(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


# ── Table 1: Monthly KPI summary ──────────────────────────────────────────────
def build_kpi_monthly(df: pd.DataFrame) -> pd.DataFrame:
    log("Building kpi_monthly_summary ...")
    grp = df.groupby(["month_year", "year", "month", "department_name"])

    result = grp.agg(
        total_orders      = ("sales",         "count"),
        total_revenue     = ("sales",         "sum"),
        total_profit      = ("profit",        "sum"),
        on_time_count     = ("is_on_time",    "sum"),
        late_count        = ("is_late",       "sum"),
        total_delay_days  = ("delay_days",    "sum"),
        total_shipping    = ("shipping_cost", "sum"),
        high_value_orders = ("high_value_order", "sum"),
    ).reset_index()

    result["on_time_pct"]       = (result["on_time_count"] / result["total_orders"] * 100).round(2)
    result["late_pct"]          = (result["late_count"]    / result["total_orders"] * 100).round(2)
    result["avg_delay_days"]    = (result["total_delay_days"] / result["total_orders"]).round(2)
    result["avg_shipping_cost"] = (result["total_shipping"]   / result["total_orders"]).round(2)
    result["profit_margin_pct"] = (result["total_profit"] / result["total_revenue"].replace(0, np.nan) * 100).round(2).fillna(0)
    result["avg_order_value"]   = (result["total_revenue"] / result["total_orders"]).round(2)

    return result[[
        "month_year", "year", "month", "department_name",
        "total_orders", "total_revenue", "total_profit",
        "on_time_pct", "late_pct", "avg_delay_days",
        "avg_shipping_cost", "profit_margin_pct",
        "high_value_orders", "avg_order_value",
    ]].sort_values(["year", "month", "department_name"])


# ── Table 2: Regional performance ─────────────────────────────────────────────
def build_regional_performance(df: pd.DataFrame) -> pd.DataFrame:
    log("Building regional_performance ...")
    grp = df.groupby(["order_region", "order_country", "market"])

    result = grp.agg(
        total_orders     = ("sales",      "count"),
        total_revenue    = ("sales",      "sum"),
        total_profit     = ("profit",     "sum"),
        on_time_count    = ("is_on_time", "sum"),
        late_count       = ("is_late",    "sum"),
        total_delay_days = ("delay_days", "sum"),
    ).reset_index()

    result["on_time_pct"]       = (result["on_time_count"] / result["total_orders"] * 100).round(2)
    result["late_pct"]          = (result["late_count"]    / result["total_orders"] * 100).round(2)
    result["avg_delay_days"]    = (result["total_delay_days"] / result["total_orders"]).round(2)
    result["profit_margin_pct"] = (result["total_profit"] / result["total_revenue"].replace(0, np.nan) * 100).round(2).fillna(0)
    result["revenue_rank"]      = result["total_revenue"].rank(ascending=False, method="dense").astype(int)

    result["total_revenue"] = result["total_revenue"].round(2)
    result["total_profit"]  = result["total_profit"].round(2)

    return result[[
        "order_region", "order_country", "market",
        "total_orders", "total_revenue", "total_profit",
        "on_time_pct", "late_pct", "avg_delay_days",
        "profit_margin_pct", "revenue_rank",
    ]].sort_values("revenue_rank")


# ── Table 3: Delay analysis ───────────────────────────────────────────────────
def build_delay_analysis(df: pd.DataFrame) -> pd.DataFrame:
    log("Building delay_analysis ...")
    grp = df.groupby(["shipping_mode", "order_region", "department_name", "delay_category"])

    result = grp.agg(
        order_count   = ("sales",      "count"),
        total_revenue = ("sales",      "sum"),
        avg_delay     = ("delay_days", "mean"),
        max_delay     = ("delay_days", "max"),
        late_revenue  = ("sales",      lambda x: x[df.loc[x.index, "is_late"] == 1].sum()),
    ).reset_index()

    result["avg_delay_days"]  = result["avg_delay"].round(2)
    result["max_delay_days"]  = result["max_delay"].astype(int)
    result["total_revenue"]   = result["total_revenue"].round(2)
    result["revenue_at_risk"] = result["late_revenue"].round(2)

    return result[[
        "shipping_mode", "order_region", "department_name", "delay_category",
        "order_count", "total_revenue", "avg_delay_days", "max_delay_days",
        "revenue_at_risk",
    ]].sort_values(["shipping_mode", "avg_delay_days"], ascending=[True, False])


def main():
    df = load_fact()

    kpi_monthly        = build_kpi_monthly(df)
    regional_perf      = build_regional_performance(df)
    delay_analysis     = build_delay_analysis(df)

    paths = {
        "kpi_monthly_summary.csv":   kpi_monthly,
        "regional_performance.csv":  regional_perf,
        "delay_analysis.csv":        delay_analysis,
    }

    print("\n" + "=" * 55)
    print("  FEATURE ENGINEERING SUMMARY")
    print("=" * 55)
    for fname, table in paths.items():
        out = OUTPUT_DIR / fname
        table.to_csv(out, index=False)
        log(f"  Saved {fname}: {len(table):,} rows × {len(table.columns)} cols")
        print(f"  {fname:<40} {len(table):>6} rows")
    print("=" * 55)
    log("Done.")


if __name__ == "__main__":
    main()
