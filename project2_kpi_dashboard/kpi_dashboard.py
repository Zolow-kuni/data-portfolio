"""
kpi_dashboard.py — Project 2: KPI Dashboard
Builds supply chain KPIs from DataCoSupplyChainDataset.csv using 13-step cleaning.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = r"C:\Users\lalit\Downloads\DataCoSupplyChainDataset\DataCoSupplyChainDataset.csv"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Data cleaning pipeline ────────────────────────────────────────────────────
def load_and_clean():
    """13-step cleaning pipeline for supply chain data."""
    print("[1/13] Loading dataset with encoding='latin-1' …")
    df = pd.read_csv(DATASET_PATH, encoding="latin-1")
    rows_loaded = len(df)
    print(f"       {rows_loaded:,} rows, {len(df.columns)} columns loaded")

    print("[2/13] Stripping whitespace from column names …")
    df.columns = df.columns.str.strip()
    print(f"       Column names stripped")

    print("[3/13] Selecting key columns …")
    key_cols = [
        "order date (DateOrders)", "Department Name", "Sales per customer",
        "Order Item Quantity", "Benefit per order", "Delivery Status",
        "Late_delivery_risk", "Days for shipping (real)",
        "Days for shipment (scheduled)", "Category Name", "Market",
        "Order Region", "Order Country"
    ]
    missing_cols = [c for c in key_cols if c not in df.columns]
    if missing_cols:
        print(f"       WARNING: Missing columns: {missing_cols}")
    df = df[[c for c in key_cols if c in df.columns]]
    print(f"       Kept {len(df.columns)} key columns, dropped {rows_loaded - len(df.columns)} others")

    print("[4/13] Renaming columns for ease …")
    rename_map = {
        "order date (DateOrders)": "Order Date",
        "Sales per customer": "Sales",
        "Order Item Quantity": "Quantity",
        "Benefit per order": "Profit",
        "Days for shipping (real)": "Actual_Days",
        "Days for shipment (scheduled)": "Scheduled_Days",
    }
    df = df.rename(columns=rename_map)
    print(f"       6 columns renamed")

    print("[5/13] Converting Order Date to datetime …")
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    date_nulls = df["Order Date"].isnull().sum()
    print(f"       {date_nulls:,} rows with invalid dates")

    print("[6/13] Dropping rows with null Order Date …")
    rows_before = len(df)
    df = df.dropna(subset=["Order Date"])
    date_rows_dropped = rows_before - len(df)
    print(f"       Dropped {date_rows_dropped:,} rows")

    print("[7/13] Dropping rows where Sales <= 0 …")
    rows_before = len(df)
    df = df[df["Sales"] > 0]
    sales_rows_dropped = rows_before - len(df)
    print(f"       Dropped {sales_rows_dropped:,} rows with invalid Sales")

    print("[8/13] Extracting Month, Year, Month-Year …")
    df["Month"] = df["Order Date"].dt.month
    df["Year"] = df["Order Date"].dt.year
    df["Month-Year"] = df["Order Date"].dt.strftime("%b-%Y")
    print(f"       Extracted temporal features")

    print("[9/13] Creating on_time column …")
    df["on_time"] = df["Delivery Status"].fillna("").str.lower()
    df["on_time"] = ((df["on_time"].str.contains("advance|on time")) &
                     (~df["on_time"].str.contains("late|canceled"))).astype(int)
    print(f"       On-time delivery column created")

    print("[10/13] Creating delay_days column …")
    df["delay_days"] = df["Actual_Days"] - df["Scheduled_Days"]
    print(f"       Delay days calculated (positive=late, negative=early)")

    print("[11/13] Handling Profit nulls …")
    profit_nulls = df["Profit"].isnull().sum()
    df["Profit"] = df["Profit"].fillna(0)
    print(f"       Filled {profit_nulls:,} Profit nulls with 0")

    print("[12/13] Removing rows where Quantity <= 0 …")
    rows_before = len(df)
    df = df[df["Quantity"] > 0]
    qty_rows_dropped = rows_before - len(df)
    print(f"       Dropped {qty_rows_dropped:,} rows")

    print("[13/13] Cleaning summary …")
    clean_rows = len(df)
    on_time_pct = df["on_time"].mean() * 100

    date_range = f"{df['Order Date'].min().date()} to {df['Order Date'].max().date()}"
    unique_depts = df["Department Name"].nunique()

    print(f"\n  ┌─ CLEANING SUMMARY ──────────────────────────────────┐")
    print(f"  │ Rows loaded         : {rows_loaded:,}")
    print(f"  │ Date nulls dropped  : {date_rows_dropped:,}")
    print(f"  │ Sales issues        : {sales_rows_dropped:,}")
    print(f"  │ Quantity issues     : {qty_rows_dropped:,}")
    print(f"  │ Final clean rows    : {clean_rows:,}")
    print(f"  │ Date range          : {date_range}")
    print(f"  │ Unique departments  : {unique_depts}")
    print(f"  │ On-time delivery %  : {on_time_pct:.1f}%")
    print(f"  └──────────────────────────────────────────────────────┘")

    return df, rows_loaded, clean_rows, on_time_pct


# ── KPI calculations ──────────────────────────────────────────────────────────
def calculate_kpis(df):
    """Build 6 key KPIs from cleaned data."""
    print("\n[KPIs] Building 6 key KPI metrics …\n")

    # KPI 1: On-time delivery % per month per department
    kpi_1 = df.groupby(["Month-Year", "Department Name"])["on_time"].agg(
        ["sum", "count"]
    ).reset_index()
    kpi_1["on_time_pct"] = (kpi_1["sum"] / kpi_1["count"] * 100).round(2)
    kpi_1 = kpi_1.rename(columns={"sum": "on_time_count", "count": "total_orders"})
    kpi_1_file = os.path.join(OUTPUT_DIR, "kpi_on_time_delivery.csv")
    kpi_1.to_csv(kpi_1_file, index=False)
    print(f"  ✓ KPI 1: On-time delivery % per month/dept → {kpi_1_file}")

    # KPI 2: Average sales per order per month
    kpi_2 = df.groupby("Month-Year").agg({
        "Sales": ["mean", "median", "std"]
    }).reset_index()
    kpi_2.columns = ["Month-Year", "avg_sales", "median_sales", "std_sales"]
    kpi_2 = kpi_2.round(2)
    kpi_2_file = os.path.join(OUTPUT_DIR, "kpi_avg_sales.csv")
    kpi_2.to_csv(kpi_2_file, index=False)
    print(f"  ✓ KPI 2: Average sales per order/month → {kpi_2_file}")

    # KPI 3: Total revenue per month
    kpi_3 = df.groupby("Month-Year").agg({
        "Sales": "sum",
        "Quantity": "sum"
    }).reset_index()
    kpi_3.columns = ["Month-Year", "total_revenue", "total_quantity"]
    kpi_3_file = os.path.join(OUTPUT_DIR, "kpi_revenue.csv")
    kpi_3.to_csv(kpi_3_file, index=False)
    print(f"  ✓ KPI 3: Total revenue per month → {kpi_3_file}")

    # KPI 4: Late delivery risk % per month
    kpi_4 = df.groupby("Month-Year").agg({
        "Late_delivery_risk": "mean"
    }).reset_index()
    kpi_4.columns = ["Month-Year", "late_risk_pct"]
    kpi_4["late_risk_pct"] = (kpi_4["late_risk_pct"] * 100).round(2)
    kpi_4_file = os.path.join(OUTPUT_DIR, "kpi_late_risk.csv")
    kpi_4.to_csv(kpi_4_file, index=False)
    print(f"  ✓ KPI 4: Late delivery risk % per month → {kpi_4_file}")

    # KPI 5: Average delay days per month
    kpi_5 = df.groupby("Month-Year").agg({
        "delay_days": ["mean", "min", "max"]
    }).reset_index()
    kpi_5.columns = ["Month-Year", "avg_delay", "min_delay", "max_delay"]
    kpi_5 = kpi_5.round(2)
    kpi_5_file = os.path.join(OUTPUT_DIR, "kpi_delay_days.csv")
    kpi_5.to_csv(kpi_5_file, index=False)
    print(f"  ✓ KPI 5: Average delay days per month → {kpi_5_file}")

    # KPI 6: Profit margin % per month
    df["profit_margin"] = (df["Profit"] / df["Sales"] * 100).replace([np.inf, -np.inf], 0)
    kpi_6 = df.groupby("Month-Year").agg({
        "Profit": "sum",
        "Sales": "sum",
        "profit_margin": "mean"
    }).reset_index()
    kpi_6["margin_pct"] = (kpi_6["Profit"] / kpi_6["Sales"] * 100).round(2)
    kpi_6 = kpi_6[["Month-Year", "Profit", "Sales", "margin_pct"]]
    kpi_6.columns = ["Month-Year", "total_profit", "total_sales", "profit_margin_pct"]
    kpi_6_file = os.path.join(OUTPUT_DIR, "kpi_profit_margin.csv")
    kpi_6.to_csv(kpi_6_file, index=False)
    print(f"  ✓ KPI 6: Profit margin % per month → {kpi_6_file}")

    return kpi_1, kpi_2, kpi_3, kpi_4, kpi_5, kpi_6


# ── Visualizations ────────────────────────────────────────────────────────────
def make_plots(df, kpi_2, kpi_3):
    """Generate KPI dashboards."""
    print("\n[PLOTS] Generating visualizations …\n")
    plt.style.use("seaborn-v0_8-whitegrid")

    # Plot 1: Revenue trend
    fig, ax = plt.subplots(figsize=(12, 6))
    kpi_3_sorted = kpi_3.sort_values("Month-Year")
    ax.plot(range(len(kpi_3_sorted)), kpi_3_sorted["total_revenue"],
            marker="o", linewidth=2, markersize=6, color="#2E86AB")
    ax.fill_between(range(len(kpi_3_sorted)), kpi_3_sorted["total_revenue"], alpha=0.3, color="#2E86AB")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total Revenue ($)")
    ax.set_title("Monthly Revenue Trend")
    ax.set_xticks(range(0, len(kpi_3_sorted), max(1, len(kpi_3_sorted)//6)))
    ax.set_xticklabels([kpi_3_sorted.iloc[i]["Month-Year"]
                        for i in range(0, len(kpi_3_sorted), max(1, len(kpi_3_sorted)//6))],
                       rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "revenue_trend.png"), dpi=150)
    plt.close()
    print(f"  Saved: revenue_trend.png")

    # Plot 2: Average Sales per Order
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(kpi_2)), kpi_2["avg_sales"], color="#A23B72", alpha=0.8)
    ax.set_xlabel("Month")
    ax.set_ylabel("Average Sales ($)")
    ax.set_title("Average Sales per Order by Month")
    ax.set_xticks(range(0, len(kpi_2), max(1, len(kpi_2)//6)))
    ax.set_xticklabels([kpi_2.iloc[i]["Month-Year"]
                        for i in range(0, len(kpi_2), max(1, len(kpi_2)//6))],
                       rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "avg_sales_by_month.png"), dpi=150)
    plt.close()
    print(f"  Saved: avg_sales_by_month.png")

    # Plot 3: On-time vs Late delivery
    on_time_by_month = df.groupby("Month-Year")["on_time"].apply(
        lambda x: (x.sum(), len(x) - x.sum())
    ).apply(pd.Series)
    on_time_by_month.columns = ["on_time", "late"]
    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(on_time_by_month))
    ax.bar(x, on_time_by_month["on_time"], label="On Time", color="#06A77D", alpha=0.8)
    ax.bar(x, on_time_by_month["late"], bottom=on_time_by_month["on_time"],
           label="Late", color="#D62246", alpha=0.8)
    ax.set_xlabel("Month")
    ax.set_ylabel("Order Count")
    ax.set_title("On-Time vs Late Deliveries by Month")
    ax.legend()
    ax.set_xticks(range(0, len(on_time_by_month), max(1, len(on_time_by_month)//6)))
    ax.set_xticklabels([on_time_by_month.index[i]
                        for i in range(0, len(on_time_by_month), max(1, len(on_time_by_month)//6))],
                       rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "on_time_vs_late.png"), dpi=150)
    plt.close()
    print(f"  Saved: on_time_vs_late.png")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print("  KPI DASHBOARD — DATA CLEANING & ANALYSIS")
    print("=" * 62 + "\n")

    df, rows_loaded, clean_rows, on_time_pct = load_and_clean()

    # Calculate KPIs
    kpi_1, kpi_2, kpi_3, kpi_4, kpi_5, kpi_6 = calculate_kpis(df)

    # Generate visualizations
    make_plots(df, kpi_2, kpi_3)

    print(f"\n[DONE] All KPI outputs written to:")
    print(f"  {OUTPUT_DIR}")
    print(f"  ✓ kpi_on_time_delivery.csv")
    print(f"  ✓ kpi_avg_sales.csv")
    print(f"  ✓ kpi_revenue.csv")
    print(f"  ✓ kpi_late_risk.csv")
    print(f"  ✓ kpi_delay_days.csv")
    print(f"  ✓ kpi_profit_margin.csv")
    print(f"  ✓ revenue_trend.png")
    print(f"  ✓ avg_sales_by_month.png")
    print(f"  ✓ on_time_vs_late.png\n")

    return rows_loaded, clean_rows


if __name__ == "__main__":
    main()
