"""
generate_data.py — Project 3: Financial Data Integrity Checker
Generates synthetic financial records with intentional data-quality errors (~7% of rows).
"""
import os
import numpy as np
import pandas as pd

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH      = os.path.join(PORTFOLIO_DIR, "data", "financial_records.csv")

VENDOR_IDS       = [f"VND{i:03d}" for i in range(1, 51)]
VALID_CURRENCIES = ["INR", "USD", "EUR", "GBP"]
VALID_STATUSES   = ["paid", "pending", "overdue"]
REGIONS          = ["North", "South", "East", "West", "Central"]


def generate(n=650, error_rate=0.07, seed=42):
    rng = np.random.default_rng(seed)
    n_errors = int(n * error_rate)

    start = pd.Timestamp("2023-01-01")
    dates = start + pd.to_timedelta(rng.integers(0, 730, n), unit="D")
    delivery_offsets = rng.integers(1, 30, n)
    delivery_dates = dates + pd.to_timedelta(delivery_offsets, unit="D")

    df = pd.DataFrame({
        "record_id":      [f"REC{i:05d}" for i in range(n)],
        "date":           dates.strftime("%Y-%m-%d"),
        "vendor_id":      rng.choice(VENDOR_IDS, n),
        "amount":         np.round(
                              rng.lognormal(mean=8, sigma=1.5, size=n).clip(50, 500_000), 2
                          ),
        "currency":       rng.choice(VALID_CURRENCIES, n),
        "region":         rng.choice(REGIONS, n),
        "invoice_ref":    [f"INV-{rng.integers(10000, 99999)}" for _ in range(n)],
        "payment_status": rng.choice(VALID_STATUSES, n),
        "delivery_date":  delivery_dates.strftime("%Y-%m-%d"),
        "created_by":     [f"user_{rng.integers(1, 21)}" for _ in range(n)],
    })

    # ── Intentionally inject errors into ~7% of rows ─────────────────────────
    err_idx = rng.choice(n, n_errors, replace=False)
    buckets = np.array_split(err_idx, 7)

    # 1. Null in required field
    for i in buckets[0]:
        col = rng.choice(["vendor_id", "amount", "currency"])
        df.at[int(i), col] = np.nan

    # 2. Duplicate record_id
    for i in buckets[1]:
        df.at[int(i), "record_id"] = df.at[0, "record_id"]

    # 3. Bad date format (YYYY/MM/DD instead of YYYY-MM-DD)
    for i in buckets[2]:
        df.at[int(i), "date"] = (
            f"2024/{rng.integers(1, 13):02d}/{rng.integers(1, 29):02d}"
        )

    # 4. delivery_date before date (chronological violation)
    for i in buckets[3]:
        try:
            d = pd.Timestamp(df.at[int(i), "date"])
            df.at[int(i), "delivery_date"] = (
                d - pd.to_timedelta(int(rng.integers(1, 15)), unit="D")
            ).strftime("%Y-%m-%d")
        except Exception:
            pass

    # 5. Negative or zero amounts
    for i in buckets[4]:
        df.at[int(i), "amount"] = float(rng.choice([-500, -1, 0, -9999]))

    # 6. Invalid currency code
    for i in buckets[5]:
        df.at[int(i), "currency"] = rng.choice(["XYZ", "AUD", "JPY", "CAD"])

    # 7. Invalid payment status
    for i in buckets[6]:
        df.at[int(i), "payment_status"] = rng.choice(["cancelled", "unknown", "draft"])

    return df, VENDOR_IDS


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df, _ = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"[generate_data] Wrote {len(df):,} rows → {OUT_PATH}")
    print(f"  Null values in 'amount' : {df['amount'].isnull().sum()}")
    print(f"  Duplicate record_ids    : {df['record_id'].duplicated().sum()}")
