"""
generate_data.py — Project 1: Fraud & Anomaly Detection
Generates a synthetic transaction dataset as a fallback when Kaggle data is unavailable.
"""
import os
import numpy as np
import pandas as pd

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH      = os.path.join(PORTFOLIO_DIR, "data", "transactions.csv")


def generate(n_normal=1850, n_fraud=150, seed=42):
    rng = np.random.default_rng(seed)

    # Hour-of-day weights: business hours are busier
    hour_weights = np.ones(24)
    hour_weights[8:19] = 4.0
    hour_weights /= hour_weights.sum()

    # ── Normal transactions ──────────────────────────────────────────────────
    normal_dates = (
        pd.Timestamp("2024-01-01")
        + pd.to_timedelta(rng.integers(0, 365, n_normal), unit="D")
    )
    normal = pd.DataFrame({
        "transaction_id":    [f"TXN{i:06d}" for i in range(n_normal)],
        "date":              normal_dates.strftime("%Y-%m-%d"),
        "amount":            np.round(rng.lognormal(mean=4.0, sigma=1.0, size=n_normal).clip(5, 4000), 2),
        "type":              rng.choice(["online", "ATM", "POS", "international"], n_normal,
                                        p=[0.40, 0.25, 0.30, 0.05]),
        "hour":              rng.choice(24, size=n_normal, p=hour_weights),
        "frequency_per_day": rng.integers(1, 6, n_normal),
        "is_fraud":          np.zeros(n_normal, dtype=int),
    })

    # ── Fraudulent transactions — high amounts, odd hours, international ─────
    fraud_dates = (
        pd.Timestamp("2024-01-01")
        + pd.to_timedelta(rng.integers(0, 365, n_fraud), unit="D")
    )
    fraud = pd.DataFrame({
        "transaction_id":    [f"TXN{i:06d}" for i in range(n_normal, n_normal + n_fraud)],
        "date":              fraud_dates.strftime("%Y-%m-%d"),
        "amount":            np.round(rng.lognormal(mean=7.5, sigma=1.2, size=n_fraud).clip(200, 80000), 2),
        "type":              rng.choice(["online", "ATM", "POS", "international"], n_fraud,
                                        p=[0.15, 0.10, 0.05, 0.70]),
        "hour":              rng.choice([0, 1, 2, 3, 4, 22, 23], size=n_fraud),
        "frequency_per_day": rng.integers(8, 25, n_fraud),
        "is_fraud":          np.ones(n_fraud, dtype=int),
    })

    df = (
        pd.concat([normal, fraud], ignore_index=True)
        .sample(frac=1, random_state=seed)
        .reset_index(drop=True)
    )
    return df


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    print(f"[generate_data] Wrote {len(df):,} rows → {OUT_PATH}")
    print(f"  Fraud rows  : {df['is_fraud'].sum()} ({df['is_fraud'].mean() * 100:.1f}%)")
    print(f"  Amount range: ${df['amount'].min():.2f} – ${df['amount'].max():,.2f}")
