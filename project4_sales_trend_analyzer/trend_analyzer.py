"""
trend_analyzer.py — Project 4: Sales Trend Analyzer
Analyzes sales trends from Sample - Superstore.csv using 15-step cleaning.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = r"C:\Users\lalit\Downloads\Sample - Superstore\Sample - Superstore.csv"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Data cleaning pipeline ────────────────────────────────────────────────────
def load_and_clean():
    """15-step cleaning pipeline for sales data."""
    print("[1/15] Loading dataset with encoding='latin-1' …")
    df = pd.read_csv(DATASET_PATH, encoding="latin-1")
    rows_loaded = len(df)
    print(f"       {rows_loaded:,} rows, {len(df.columns)} columns loaded")

    print("[2/15] Stripping whitespace from column names …")
    df.columns = df.columns.str.strip()
    print(f"       Column names stripped")

    print("[3/15] Converting Order Date to datetime …")
    for fmt in ["%d/%m/%Y", "%m/%d/%Y"]:
        try:
            df["Order Date"] = pd.to_datetime(df["Order Date"], format=fmt, errors="coerce")
            if df["Order Date"].isnull().sum() < rows_loaded * 0.1:
                break
        except:
            pass
    print(f"       {df['Order Date'].isnull().sum():,} date parse errors")

    print("[4/15] Converting Ship Date to datetime …")
    for fmt in ["%d/%m/%Y", "%m/%d/%Y"]:
        try:
            df["Ship Date"] = pd.to_datetime(df["Ship Date"], format=fmt, errors="coerce")
            if df["Ship Date"].isnull().sum() < rows_loaded * 0.1:
                break
        except:
            pass
    print(f"       {df['Ship Date'].isnull().sum():,} date parse errors")

    print("[5/15] Dropping rows where Order Date is null …")
    rows_before = len(df)
    df = df.dropna(subset=["Order Date"])
    date_rows_dropped = rows_before - len(df)
    print(f"       Dropped {date_rows_dropped:,} rows")

    print("[6/15] Validating Sales > 0 …")
    rows_before = len(df)
    df = df[df["Sales"] > 0]
    sales_rows_dropped = rows_before - len(df)
    print(f"       Dropped {sales_rows_dropped:,} rows with invalid Sales")

    print("[7/15] Validating Quantity > 0 …")
    rows_before = len(df)
    df = df[df["Quantity"] > 0]
    qty_rows_dropped = rows_before - len(df)
    print(f"       Dropped {qty_rows_dropped:,} rows with invalid Quantity")

    print("[8/15] Validating Discount (0–1) …")
    invalid_discounts = ((df["Discount"] < 0) | (df["Discount"] > 1)).sum()
    if invalid_discounts > 0:
        print(f"       ✗ {invalid_discounts:,} invalid discount values")
    else:
        print(f"       ✓ All discounts valid")

    print("[9/15] Checking Profit outliers …")
    profit_extreme = (df["Profit"] < df["Profit"].quantile(0.01)) | (df["Profit"] > df["Profit"].quantile(0.99))
    print(f"       {profit_extreme.sum():,} extreme profit values (top/bottom 1%)")

    print("[10/15] Validating Region values …")
    valid_regions = {"East", "West", "Central", "South"}
    actual_regions = set(df["Region"].unique())
    invalid_regions = actual_regions - valid_regions
    if invalid_regions:
        print(f"       ✗ Invalid regions: {invalid_regions}")
    else:
        print(f"       ✓ All regions valid")

    print("[11/15] Validating Category values …")
    valid_categories = {"Furniture", "Office Supplies", "Technology"}
    actual_categories = set(df["Category"].unique())
    invalid_categories = actual_categories - valid_categories
    if invalid_categories:
        print(f"       ✗ Invalid categories: {invalid_categories}")
    else:
        print(f"       ✓ All categories valid")

    print("[12/15] Removing duplicate Order ID + Product ID combinations …")
    dups_before = len(df)
    df = df.drop_duplicates(subset=["Order ID", "Product ID"])
    dups_removed = dups_before - len(df)
    print(f"       Removed {dups_removed:,} duplicates")

    print("[13/15] Extracting temporal features …")
    df["Month"] = df["Order Date"].dt.month
    df["Year"] = df["Order Date"].dt.year
    df["Month-Year"] = df["Order Date"].dt.strftime("%b-%Y")
    df["Quarter"] = df["Order Date"].dt.quarter.apply(lambda x: f"Q{x}")
    print(f"       Extracted Month, Year, Month-Year, Quarter")

    print("[14/15] Creating profit_margin column …")
    df["profit_margin"] = (df["Profit"] / df["Sales"] * 100).replace([np.inf, -np.inf], 0)
    print(f"       Profit margin calculated")

    print("[15/15] Cleaning summary …")
    clean_rows = len(df)
    date_range = f"{df['Order Date'].min().date()} to {df['Order Date'].max().date()}"
    unique_categories = df["Category"].nunique()
    unique_subcategories = df["Sub-Category"].nunique()
    unique_regions = df["Region"].nunique()
    overall_margin = df["profit_margin"].mean()

    print(f"\n  ┌─ CLEANING SUMMARY ──────────────────────────────────┐")
    print(f"  │ Rows loaded         : {rows_loaded:,}")
    print(f"  │ Date nulls dropped  : {date_rows_dropped:,}")
    print(f"  │ Sales issues        : {sales_rows_dropped:,}")
    print(f"  │ Quantity issues     : {qty_rows_dropped:,}")
    print(f"  │ Duplicates removed  : {dups_removed:,}")
    print(f"  │ Final clean rows    : {clean_rows:,}")
    print(f"  │ Date range          : {date_range}")
    print(f"  │ Unique categories   : {unique_categories}")
    print(f"  │ Sub-categories      : {unique_subcategories}")
    print(f"  │ Regions             : {unique_regions}")
    print(f"  │ Overall margin %    : {overall_margin:.2f}%")
    print(f"  └──────────────────────────────────────────────────────┘")

    return df, rows_loaded, clean_rows


# ── Analysis functions ────────────────────────────────────────────────────────
def analyze_trends(df):
    """Generate 7 key analysis outputs."""
    print("\n[ANALYSIS] Computing trend analysis …\n")

    # 1. Monthly revenue trend with 3-month rolling average
    monthly_sales = df.groupby("Month-Year")["Sales"].sum().reset_index()
    monthly_sales["rolling_avg_3m"] = monthly_sales["Sales"].rolling(window=3, center=True).mean()
    output_1 = os.path.join(OUTPUT_DIR, "monthly_revenue_trend.csv")
    monthly_sales.to_csv(output_1, index=False)
    print(f"  ✓ 1. Monthly revenue trend → {output_1}")

    # 2. MoM growth rate
    monthly_sales["mom_growth"] = monthly_sales["Sales"].pct_change() * 100
    monthly_qty = df.groupby("Month-Year")["Quantity"].sum().reset_index()
    monthly_qty["mom_growth"] = monthly_qty["Quantity"].pct_change() * 100
    output_2 = os.path.join(OUTPUT_DIR, "mom_growth_rates.csv")
    growth_data = pd.DataFrame({
        "Month-Year": monthly_sales["Month-Year"],
        "Sales_Growth_%": monthly_sales["mom_growth"],
        "Quantity_Growth_%": monthly_qty["mom_growth"]
    })
    growth_data.to_csv(output_2, index=False)
    print(f"  ✓ 2. Month-over-month growth → {output_2}")

    # 3. Flag anomalies (>15% deviation from rolling avg)
    monthly_sales["deviation_pct"] = np.abs(
        (monthly_sales["Sales"] - monthly_sales["rolling_avg_3m"]) / monthly_sales["rolling_avg_3m"] * 100
    )
    anomalies = monthly_sales[monthly_sales["deviation_pct"] > 15]
    output_3 = os.path.join(OUTPUT_DIR, "sales_anomalies.csv")
    anomalies.to_csv(output_3, index=False)
    print(f"  ✓ 3. Sales anomalies (>15% deviation) → {output_3} ({len(anomalies)} found)")

    # 4. Regional revenue by Category (pivot)
    regional_pivot = df.pivot_table(
        values="Sales", index="Region", columns="Category", aggfunc="sum"
    )
    output_4 = os.path.join(OUTPUT_DIR, "regional_revenue_by_category.csv")
    regional_pivot.to_csv(output_4)
    print(f"  ✓ 4. Regional revenue by category → {output_4}")

    # 5. Seasonal analysis
    seasonal = df.groupby("Month")["Sales"].mean().reset_index()
    seasonal["Month_Name"] = seasonal["Month"].map({
        1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
        7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
    })
    output_5 = os.path.join(OUTPUT_DIR, "seasonal_analysis.csv")
    seasonal.to_csv(output_5, index=False)
    print(f"  ✓ 5. Seasonal analysis (avg sales by month) → {output_5}")

    # 6. Sub-Category profitability ranking
    subcategory_profit = df.groupby("Sub-Category").agg({
        "Profit": "sum",
        "Sales": "sum"
    }).reset_index()
    subcategory_profit["profit_margin_pct"] = (
        subcategory_profit["Profit"] / subcategory_profit["Sales"] * 100
    ).round(2)
    subcategory_profit = subcategory_profit.sort_values("profit_margin_pct", ascending=False)
    output_6 = os.path.join(OUTPUT_DIR, "subcategory_profitability.csv")
    subcategory_profit.to_csv(output_6, index=False)
    print(f"  ✓ 6. Sub-category profitability ranking → {output_6}")

    # 7. Top/Bottom 10 products by profit margin
    product_margins = df.groupby("Product Name").agg({
        "Profit": "sum",
        "Sales": "sum",
        "Quantity": "sum"
    }).reset_index()
    product_margins["profit_margin_pct"] = (
        product_margins["Profit"] / product_margins["Sales"] * 100
    ).round(2)
    top_10 = product_margins.nlargest(10, "profit_margin_pct")
    bottom_10 = product_margins.nsmallest(10, "profit_margin_pct")
    output_7 = os.path.join(OUTPUT_DIR, "top_bottom_products.csv")
    combined = pd.concat([
        top_10.assign(ranking="Top 10"),
        bottom_10.assign(ranking="Bottom 10")
    ])
    combined.to_csv(output_7, index=False)
    print(f"  ✓ 7. Top/Bottom 10 products by margin → {output_7}")

    return monthly_sales, regional_pivot, seasonal, subcategory_profit


# ── Visualizations ────────────────────────────────────────────────────────────
def make_plots(df, monthly_sales):
    """Generate analysis visualizations."""
    print("\n[PLOTS] Generating visualizations …\n")
    plt.style.use("seaborn-v0_8-whitegrid")

    # Plot 1: Revenue trend with rolling average
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(range(len(monthly_sales)), monthly_sales["Sales"],
            marker="o", label="Monthly Sales", color="#1F77B4", alpha=0.7, linewidth=2)
    ax.plot(range(len(monthly_sales)), monthly_sales["rolling_avg_3m"],
            label="3-Month Rolling Avg", color="#FF7F0E", linewidth=2.5)
    ax.fill_between(range(len(monthly_sales)), monthly_sales["Sales"], alpha=0.2, color="#1F77B4")
    ax.set_xlabel("Month")
    ax.set_ylabel("Sales ($)")
    ax.set_title("Monthly Revenue Trend with 3-Month Rolling Average")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "revenue_trend.png"), dpi=150)
    plt.close()
    print(f"  Saved: revenue_trend.png")

    # Plot 2: Profit margin by category
    category_margin = df.groupby("Category")["profit_margin"].mean()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(category_margin.index, category_margin.values, color=["#2CA02C", "#D62728", "#9467BD"], alpha=0.8)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
    ax.set_ylabel("Profit Margin (%)")
    ax.set_title("Average Profit Margin by Category")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "profit_margin_by_category.png"), dpi=150)
    plt.close()
    print(f"  Saved: profit_margin_by_category.png")

    # Plot 3: Regional sales comparison
    regional_sales = df.groupby("Region")["Sales"].sum()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(regional_sales.index, regional_sales.values, color=["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728"], alpha=0.8)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${height/1000:.0f}K', ha='center', va='bottom', fontweight='bold')
    ax.set_ylabel("Sales ($)")
    ax.set_title("Total Sales by Region")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "sales_by_region.png"), dpi=150)
    plt.close()
    print(f"  Saved: sales_by_region.png")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print("  SALES TREND ANALYZER — DATA CLEANING & ANALYSIS")
    print("=" * 62 + "\n")

    df, rows_loaded, clean_rows = load_and_clean()

    # Run analysis
    monthly_sales, regional_pivot, seasonal, subcategory_profit = analyze_trends(df)

    # Generate visualizations
    make_plots(df, monthly_sales)

    print(f"\n[DONE] All analysis outputs written to:")
    print(f"  {OUTPUT_DIR}")
    print(f"  → monthly_revenue_trend.csv")
    print(f"  → mom_growth_rates.csv")
    print(f"  → sales_anomalies.csv")
    print(f"  → regional_revenue_by_category.csv")
    print(f"  → seasonal_analysis.csv")
    print(f"  → subcategory_profitability.csv")
    print(f"  → top_bottom_products.csv")
    print(f"  → revenue_trend.png")
    print(f"  → profit_margin_by_category.png")
    print(f"  → sales_by_region.png\n")

    return rows_loaded, clean_rows


if __name__ == "__main__":
    main()
