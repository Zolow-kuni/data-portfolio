"""
generate_data.py — Project 4: Sales & Inventory Trend Analyzer
Generates 2 years of synthetic monthly sales and inventory data.
"""
import os
import numpy as np
import pandas as pd

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH      = os.path.join(PORTFOLIO_DIR, "data", "sales_inventory.csv")

CATEGORIES = ["Electronics", "Clothing", "Home & Garden"]
REGIONS    = ["North", "South", "East"]

PRODUCTS = {
    "Electronics":   [("P001", "Laptop"),       ("P002", "Smartphone"),  ("P003", "Tablet")],
    "Clothing":      [("P004", "Jacket"),        ("P005", "Sneakers"),    ("P006", "T-Shirt")],
    "Home & Garden": [("P007", "Coffee Maker"),  ("P008", "Blender"),     ("P009", "Garden Hose")],
}

# Stock reorder points per product
REORDER_POINTS = {
    "P001": 50,  "P002": 80,  "P003": 60,
    "P004": 100, "P005": 90,  "P006": 150,
    "P007": 70,  "P008": 60,  "P009": 120,
}

# Unit price ranges per category (min, max)
PRICE_RANGES = {
    "Electronics":   (150, 1500),
    "Clothing":      (10,  200),
    "Home & Garden": (20,  300),
}


def generate(seed=42):
    rng = np.random.default_rng(seed)
    months = pd.date_range("2023-01", periods=24, freq="MS")
    rows = []

    for month in months:
        m = month.month
        # Seasonal multiplier: Q4 peak, Q1 slow — sine wave shape
        seasonal = 1.0 + 0.35 * np.sin((m - 3) * np.pi / 6)

        for cat, products in PRODUCTS.items():
            lo, hi = PRICE_RANGES[cat]
            for pid, pname in products:
                price = round(float(rng.uniform(lo, hi)), 2)
                for region in REGIONS:
                    base_units = int(rng.integers(150, 700))
                    units_sold = max(1, int(base_units * seasonal * rng.uniform(0.8, 1.2)))
                    revenue    = round(units_sold * price, 2)
                    stock      = int(rng.integers(0, 280))
                    rows.append({
                        "date":          month.strftime("%Y-%m-%d"),
                        "product_id":    pid,
                        "product_name":  pname,
                        "category":      cat,
                        "region":        region,
                        "units_sold":    units_sold,
                        "revenue":       revenue,
                        "stock_level":   stock,
                        "reorder_point": REORDER_POINTS[pid],
                    })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"[generate_data] Wrote {len(df):,} rows → {OUT_PATH}")
    print(f"  Date range  : {df['date'].min()} → {df['date'].max()}")
    print(f"  Categories  : {df['category'].nunique()}")
    print(f"  Regions     : {df['region'].nunique()}")
    low_stock = df[df["stock_level"] < df["reorder_point"]]
    print(f"  Low-stock records: {len(low_stock)}")
