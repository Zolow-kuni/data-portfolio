"""
Project 10: Power BI Logistics Dashboard
File: 01_clean_and_prepare.py
Author: Subham Joshi
Description: Load, clean, and feature-engineer the main fact table for Power BI.
             Mirrors the data preparation pipeline used at Logistics Integrators.
Run: python 01_clean_and_prepare.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_CSV  = r"C:\Users\lalit\Downloads\DataCoSupplyChainDataset\DataCoSupplyChainDataset.csv"
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "logistics_dashboard_data.csv"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# Column name map: raw CSV → clean snake_case
COL_MAP = {
    "order date (dateorders)":       "order_date",
    "shipping date (dateorders)":    "ship_date",
    "department name":               "department_name",
    "category name":                 "category_name",
    "market":                        "market",
    "order region":                  "order_region",
    "order country":                 "order_country",
    "customer segment":              "customer_segment",
    "sales":                         "sales",
    "order item quantity":           "quantity",
    "order profit per order":        "profit",
    "delivery status":               "delivery_status",
    "late_delivery_risk":            "late_delivery_risk",
    "days for shipping (real)":      "actual_ship_days",
    "days for shipment (scheduled)": "scheduled_ship_days",
    "shipping mode":                 "shipping_mode",
    "product name":                  "product_name",
    "product price":                 "product_price",
    "benefit per order":             "benefit_per_order",
}

KEEP_COLS = list(COL_MAP.values())


def load_and_clean(path: str) -> pd.DataFrame:
    log(f"Loading: {path}")
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    log(f"  Raw shape: {df.shape}")

    # 1. Strip whitespace and embedded quote chars from column names
    df.columns = [c.strip().strip("'\"").strip().lower() for c in df.columns]

    # 2. Rename to snake_case
    df = df.rename(columns={k: v for k, v in COL_MAP.items() if k in df.columns})

    # 3. Keep only required columns
    available = [c for c in KEEP_COLS if c in df.columns]
    df = df[available].copy()

    # 4. Parse dates
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    if "ship_date" in df.columns:
        df["ship_date"] = pd.to_datetime(df["ship_date"], errors="coerce")

    rows_before = len(df)

    # 5. Drop rows with null order_date
    df = df[df["order_date"].notna()]

    # 6. Drop rows with sales <= 0
    df["sales"] = pd.to_numeric(df["sales"], errors="coerce")
    df = df[df["sales"].notna() & (df["sales"] > 0)]

    log(f"  Dropped {rows_before - len(df):,} rows (null date or bad sales)")

    # 7. Fill nulls
    if "profit" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
    else:
        df["profit"] = 0.0

    if "shipping_cost" in df.columns:
        df["shipping_cost"] = pd.to_numeric(df["shipping_cost"], errors="coerce").fillna(0)
    else:
        df["shipping_cost"] = 0.0

    # Numeric coercions
    for col in ("quantity", "actual_ship_days", "scheduled_ship_days",
                "late_delivery_risk", "product_price", "benefit_per_order"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["quantity"]           = df["quantity"].astype(int).clip(lower=1)
    df["late_delivery_risk"] = df["late_delivery_risk"].astype(int).clip(0, 1)
    df["actual_ship_days"]   = df["actual_ship_days"].astype(int)
    df["scheduled_ship_days"]= df["scheduled_ship_days"].astype(int)

    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    log("Engineering derived columns ...")

    # Temporal columns
    df["year"]        = df["order_date"].dt.year
    df["month"]       = df["order_date"].dt.month
    df["month_name"]  = df["order_date"].dt.strftime("%b")
    df["month_year"]  = df["order_date"].dt.strftime("%b-%Y")
    df["quarter"]     = "Q" + df["order_date"].dt.quarter.astype(str)
    df["week_number"] = df["order_date"].dt.isocalendar().week.astype(int)

    # Delay metrics
    df["delay_days"] = df["actual_ship_days"] - df["scheduled_ship_days"]

    # Delivery flags
    df["is_late"] = df["delivery_status"].str.contains(
        "Late", case=False, na=False
    ).astype(int)

    df["is_on_time"] = df["delivery_status"].str.contains(
        "Advance|on time", case=False, na=False
    ).astype(int)

    # Financial metrics
    df["profit_margin_pct"] = (
        df["profit"] / df["sales"].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    df["shipping_cost_per_unit"] = (
        df["shipping_cost"] / df["quantity"].replace(0, np.nan)
    ).round(2).fillna(0)

    df["high_value_order"] = (df["sales"] > 500).astype(int)

    # Delay category
    def categorise_delay(d):
        if d <= 0:
            return "On Time"
        elif d <= 2:
            return "Minor Delay (1-2 days)"
        elif d <= 5:
            return "Moderate Delay (3-5 days)"
        else:
            return "Major Delay (5+ days)"

    df["delay_category"] = df["delay_days"].apply(categorise_delay)

    return df


def print_summary(df_before_rows: int, df: pd.DataFrame):
    on_time_rate = df["is_on_time"].mean() * 100
    late_rate    = df["is_late"].mean() * 100
    margin       = (df["profit"] / df["sales"].replace(0, np.nan)).mean() * 100

    print("\n" + "=" * 55)
    print("  CLEANING SUMMARY")
    print("=" * 55)
    print(f"  Rows before cleaning   : {df_before_rows:,}")
    print(f"  Rows after cleaning    : {len(df):,}")
    print(f"  Date range             : {df['order_date'].min().date()} → "
          f"{df['order_date'].max().date()}")
    print(f"  Unique departments     : {df['department_name'].nunique()}")
    print(f"  Unique markets         : {df['market'].nunique()}")
    print(f"  Unique regions         : {df['order_region'].nunique()}")
    print(f"  On-time delivery rate  : {on_time_rate:.2f}%")
    print(f"  Overall profit margin  : {margin:.2f}%")
    print(f"  Late delivery rate     : {late_rate:.2f}%")
    print(f"  Output columns         : {len(df.columns)}")
    print("=" * 55)


def main():
    raw_rows = sum(1 for _ in open(INPUT_CSV, encoding="latin-1")) - 1
    df = load_and_clean(INPUT_CSV)
    df = engineer_features(df)

    log(f"Saving to {OUTPUT_CSV} ...")
    df.to_csv(OUTPUT_CSV, index=False)
    log("Saved.")

    print_summary(raw_rows, df)
    log("Done.")


if __name__ == "__main__":
    main()
