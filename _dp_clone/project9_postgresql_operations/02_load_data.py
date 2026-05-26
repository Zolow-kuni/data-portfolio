"""
Project 9: PostgreSQL Operations Analytics
File: 02_load_data.py
Author: Subham Joshi
Description: Load DataCoSupplyChainDataset.csv and supply_chain_data.csv
             into PostgreSQL. Includes cleaning, column mapping, and batch inserts.
Run: python 02_load_data.py
Prerequisite: Run 01_create_tables.sql first.
"""

import psycopg2
import pandas as pd
from datetime import datetime
import sys

# ── Config ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "dbname":   "logistics_analytics",
    "user":     "postgres",
    "password": "Shubham@12",
    "host":     "localhost",
    "port":     5432,
}

ORDERS_CSV       = r"C:\Users\lalit\Downloads\DataCoSupplyChainDataset\DataCoSupplyChainDataset.csv"
SUPPLY_CHAIN_CSV = r"C:\Users\lalit\Downloads\supply_chain_data\supply_chain_data.csv"
BATCH_SIZE       = 1000


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ── Column mapping: CSV header → Postgres column ─────────────────────────────
ORDERS_COL_MAP = {
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
    "order item discount rate":      "order_item_discount",
    "benefit per order":             "benefit_per_order",
    "order status":                  "order_status",
}


def load_orders(conn):
    log("Reading orders CSV (encoding=latin-1) ...")
    df = pd.read_csv(ORDERS_CSV, encoding="latin-1", low_memory=False)
    log(f"  Raw rows: {len(df):,}")

    # Normalise column names — strip whitespace and embedded quote chars
    df.columns = [c.strip().strip("'\"").strip().lower() for c in df.columns]

    # Keep only mapped columns
    available = {k: v for k, v in ORDERS_COL_MAP.items() if k in df.columns}
    missing   = [k for k in ORDERS_COL_MAP if k not in df.columns]
    if missing:
        log(f"  WARNING — unmapped columns (will be NULL): {missing}")

    df = df[list(available.keys())].rename(columns=available)

    # ── Cleaning ──────────────────────────────────────────────────────────────
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["ship_date"]  = pd.to_datetime(df.get("ship_date"), errors="coerce")

    before = len(df)
    df = df[df["order_date"].notna()]
    df = df[df["sales"].notna() & (df["sales"] > 0)]
    log(f"  Dropped {before - len(df):,} rows (null date or non-positive sales)")

    if "profit" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
    else:
        df["profit"] = 0.0

    if "shipping_cost" in df.columns:
        df["shipping_cost"] = pd.to_numeric(df["shipping_cost"], errors="coerce").fillna(0)
    else:
        df["shipping_cost"] = 0.0

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip())

    # late_delivery_risk → integer 0/1
    df["late_delivery_risk"] = pd.to_numeric(
        df.get("late_delivery_risk", 0), errors="coerce"
    ).fillna(0).astype(int).clip(0, 1)

    # actual_ship_days / scheduled_ship_days → integer
    for col in ("actual_ship_days", "scheduled_ship_days"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # quantity → integer
    if "quantity" in df.columns:
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1).astype(int)

    log(f"  Clean rows to load: {len(df):,}")

    # ── DB insert ──────────────────────────────────────────────────────────────
    INSERT_SQL = """
        INSERT INTO orders (
            order_date, ship_date, department_name, category_name, market,
            order_region, order_country, customer_segment, sales, quantity,
            profit, shipping_cost, delivery_status, late_delivery_risk,
            actual_ship_days, scheduled_ship_days, shipping_mode, product_name,
            product_price, order_item_discount, benefit_per_order, order_status
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
    """

    db_cols = [
        "order_date","ship_date","department_name","category_name","market",
        "order_region","order_country","customer_segment","sales","quantity",
        "profit","shipping_cost","delivery_status","late_delivery_risk",
        "actual_ship_days","scheduled_ship_days","shipping_mode","product_name",
        "product_price","order_item_discount","benefit_per_order","order_status",
    ]

    # Ensure all expected columns exist (fill missing with None)
    for c in db_cols:
        if c not in df.columns:
            df[c] = None

    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE orders RESTART IDENTITY;")

    total = 0
    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE][db_cols]
        rows  = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in batch.itertuples(index=False, name=None)
        ]
        cur.executemany(INSERT_SQL, rows)
        conn.commit()
        total += len(rows)
        if total % 10000 == 0:
            log(f"  Inserted {total:,} rows ...")

    log(f"  Orders loaded: {total:,} rows")

    # Summary stats
    date_min = df["order_date"].min().date()
    date_max = df["order_date"].max().date()
    depts    = df["department_name"].nunique()
    countries= df["order_country"].nunique() if "order_country" in df.columns else "N/A"

    cur.close()
    return total, date_min, date_max, depts, countries


def load_supply_chain(conn):
    log("Reading supply_chain_data.csv ...")
    df = pd.read_csv(SUPPLY_CHAIN_CSV, low_memory=False)
    log(f"  Raw rows: {len(df):,}")
    df.columns = [c.strip() for c in df.columns]

    # Map to table columns (supply_chain_data.csv already has clean headers)
    col_map = {
        "SKU":                    "sku",
        "Product type":           "product_type",
        "Price":                  "price",
        "Availability":           "availability",
        "Number of products sold":"products_sold",
        "Revenue generated":      "revenue_generated",
        "Customer demographics":  "customer_demographics",
        "Stock levels":           "stock_levels",
        "Lead times":             "lead_times",
        "Order quantities":       "order_quantities",
        "Shipping times":         "shipping_times",
        "Shipping carriers":      "shipping_carrier",
        "Shipping costs":         "shipping_costs",
        "Supplier name":          "supplier_name",
        "Location":               "location",
        "Lead time":              "lead_time",
        "Production volumes":     "production_volumes",
        "Manufacturing lead time":"manufacturing_lead_time",
        "Manufacturing costs":    "manufacturing_costs",
        "Inspection results":     "inspection_results",
        "Defect rates":           "defect_rates",
        "Transportation modes":   "transportation_mode",
        "Routes":                 "route",
        "Costs":                  "costs",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    db_cols = [
        "sku","product_type","price","availability","products_sold",
        "revenue_generated","customer_demographics","stock_levels","lead_times",
        "order_quantities","shipping_times","shipping_carrier","shipping_costs",
        "supplier_name","location","lead_time","production_volumes",
        "manufacturing_lead_time","manufacturing_costs","inspection_results",
        "defect_rates","transportation_mode","route","costs",
    ]
    for c in db_cols:
        if c not in df.columns:
            df[c] = None

    INSERT_SQL = """
        INSERT INTO supply_chain_ref (
            sku, product_type, price, availability, products_sold,
            revenue_generated, customer_demographics, stock_levels, lead_times,
            order_quantities, shipping_times, shipping_carrier, shipping_costs,
            supplier_name, location, lead_time, production_volumes,
            manufacturing_lead_time, manufacturing_costs, inspection_results,
            defect_rates, transportation_mode, route, costs
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (sku) DO UPDATE SET
            product_type = EXCLUDED.product_type,
            defect_rates = EXCLUDED.defect_rates,
            inspection_results = EXCLUDED.inspection_results;
    """

    cur = conn.cursor()
    rows = [
        tuple(None if pd.isna(v) else v for v in row)
        for row in df[db_cols].itertuples(index=False, name=None)
    ]
    cur.executemany(INSERT_SQL, rows)
    conn.commit()
    log(f"  Supply chain ref loaded: {len(rows)} rows")
    cur.close()
    return len(rows)


def main():
    log("Connecting to PostgreSQL ...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        log(f"ERROR: Could not connect — {e}")
        sys.exit(1)

    log("Connection established.")

    orders_count, date_min, date_max, depts, countries = load_orders(conn)
    sc_count = load_supply_chain(conn)

    conn.close()

    print("\n" + "="*55)
    print("  LOAD SUMMARY")
    print("="*55)
    print(f"  Orders loaded        : {orders_count:,} rows")
    print(f"  Supply chain ref     : {sc_count} rows")
    print(f"  Date range           : {date_min} to {date_max}")
    print(f"  Unique departments   : {depts}")
    print(f"  Unique countries     : {countries}")
    print("="*55)
    log("Done.")


if __name__ == "__main__":
    main()
