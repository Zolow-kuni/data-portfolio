"""
fraud_detection.py — Project 1: Fraud & Anomaly Detection System
Detects anomalous transactions using Z-score, IQR, and rule-based risk scoring.
Auto-loads Kaggle creditcard.csv if present; otherwise generates synthetic data.
"""
import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
KAGGLE_CSV    = os.path.join(PORTFOLIO_DIR, "data", "project1", "creditcard.csv")
SYNTH_CSV     = os.path.join(PORTFOLIO_DIR, "data", "transactions.csv")
GENERATE_PY   = os.path.join(SCRIPT_DIR, "generate_data.py")
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Risk points assigned by transaction type
TYPE_RISK = {"international": 30, "online": 15, "ATM": 10, "POS": 5}


# ── Data loading ──────────────────────────────────────────────────────────────
def load_data():
    """Load Kaggle creditcard.csv or fall back to synthetic transactions."""
    if os.path.exists(KAGGLE_CSV):
        print(f"[load] Kaggle dataset: {KAGGLE_CSV}")
        df = pd.read_csv(KAGGLE_CSV)

        # Standardise column names to match synthetic schema
        df = df.rename(columns={"Amount": "amount", "Class": "is_fraud"})
        df["transaction_id"] = [f"TXN{i:06d}" for i in df.index]

        rng = np.random.default_rng(0)
        df["hour"] = (df["Time"] / 3600 % 24).astype(int)
        df["frequency_per_day"] = rng.integers(1, 15, len(df))
        df["type"] = rng.choice(
            ["online", "ATM", "POS", "international"], len(df),
            p=[0.35, 0.25, 0.30, 0.10],
        )
        return df, "kaggle"

    print("[load] Kaggle data not found — using synthetic dataset.")
    if not os.path.exists(SYNTH_CSV):
        print("[load] Generating synthetic data …")
        subprocess.run([sys.executable, GENERATE_PY], check=True)
    return pd.read_csv(SYNTH_CSV), "synthetic"


# ── Anomaly detection: Z-score ─────────────────────────────────────────────────
def flag_zscore(df, col="amount", threshold=2.5):
    """Flag rows whose amount is more than `threshold` SDs from the mean."""
    z = np.abs(stats.zscore(df[col].fillna(0)))
    return pd.Series(z > threshold, index=df.index)


# ── Anomaly detection: IQR ─────────────────────────────────────────────────────
def flag_iqr(df, col="amount", top_pct=99):
    """Flag rows in the top 1% of the amount distribution."""
    cutoff = np.percentile(df[col].fillna(0), top_pct)
    return df[col] > cutoff


# ── Rule-based risk scoring (0–100) ───────────────────────────────────────────
def compute_risk_score(df):
    """
    Score each transaction 0–100 based on 4 risk factors:
      - Amount (0–40 pts)
      - Frequency per day (0–20 pts)
      - Transaction type (0–30 pts)
      - Hour of day — late-night adds 10 pts
    """
    score = pd.Series(0.0, index=df.index)

    # Amount component
    amt = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    amt_range = amt.max() - amt.min()
    if amt_range > 0:
        score += (amt - amt.min()) / amt_range * 40

    # Frequency component
    freq = pd.to_numeric(df["frequency_per_day"], errors="coerce").fillna(1)
    freq_range = freq.max() - freq.min()
    if freq_range > 0:
        score += (freq - freq.min()) / freq_range * 20

    # Transaction type component
    score += df["type"].map(TYPE_RISK).fillna(10)

    # Late-night penalty (midnight–4 AM or 10 PM–midnight)
    hour = pd.to_numeric(df["hour"], errors="coerce").fillna(12)
    score += ((hour <= 4) | (hour >= 22)).astype(int) * 10

    return score.clip(0, 100)


# ── Visualisations ─────────────────────────────────────────────────────────────
def make_plots(df):
    plt.style.use("seaborn-v0_8-whitegrid")

    # 1 — Risk score histogram
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(df["risk_score"], bins=50, color="#4C72B0", edgecolor="white", alpha=0.85)
    ax.axvline(70, color="red",    linestyle="--", linewidth=1.4, label="High threshold (70)")
    ax.axvline(40, color="orange", linestyle="--", linewidth=1.4, label="Medium threshold (40)")
    ax.set_xlabel("Risk Score")
    ax.set_ylabel("Transaction Count")
    ax.set_title("Distribution of Transaction Risk Scores")
    ax.legend()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "risk_score_histogram.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # 2 — Flagged vs Normal bar chart
    counts = df["flagged"].value_counts()
    labels = ["Normal", "Flagged"]
    values = [counts.get(False, 0), counts.get(True, 0)]
    colors = ["#55A868", "#C44E52"]
    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                f"{v:,}", ha="center", va="bottom", fontweight="bold")
    ax.set_ylabel("Number of Transactions")
    ax.set_title("Flagged vs Normal Transactions")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "flagged_vs_normal.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # 3 — Amount vs Frequency scatter (coloured by risk score)
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(
        df["amount"], df["frequency_per_day"],
        c=df["risk_score"], cmap="RdYlGn_r",
        alpha=0.45, s=12, vmin=0, vmax=100,
    )
    plt.colorbar(sc, ax=ax, label="Risk Score")
    ax.set_xlabel("Transaction Amount ($)")
    ax.set_ylabel("Frequency per Day")
    ax.set_title("Amount vs Frequency — Coloured by Risk Score")
    ax.set_xscale("log")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "amount_vs_frequency.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    df, source = load_data()
    print(f"[data] {len(df):,} rows loaded (source: {source})")

    # Compute detection flags
    df["zscore_flag"] = flag_zscore(df)
    df["iqr_flag"]    = flag_iqr(df)
    df["risk_score"]  = compute_risk_score(df)
    df["risk_level"]  = pd.cut(
        df["risk_score"],
        bins=[0, 40, 70, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    )
    # A transaction is flagged if any method triggers
    df["flagged"] = df["zscore_flag"] | df["iqr_flag"] | (df["risk_score"] >= 70)

    # Save flagged transactions report
    flagged = df[df["flagged"]].copy()
    out_cols = [c for c in
                ["transaction_id", "date", "amount", "type", "hour",
                 "frequency_per_day", "risk_score", "risk_level",
                 "zscore_flag", "iqr_flag", "is_fraud"]
                if c in flagged.columns]
    flagged_path = os.path.join(OUTPUT_DIR, "flagged_transactions.csv")
    flagged[out_cols].sort_values("risk_score", ascending=False).to_csv(flagged_path, index=False)

    # ── Terminal summary ───────────────────────────────────────────────────────
    total    = len(df)
    n_flagged = df["flagged"].sum()
    high     = (df["risk_level"] == "High").sum()
    medium   = (df["risk_level"] == "Medium").sum()
    low      = (df["risk_level"] == "Low").sum()

    print("\n" + "=" * 56)
    print("  FRAUD DETECTION — SUMMARY REPORT")
    print("=" * 56)
    print(f"  Total transactions  : {total:,}")
    print(f"  Flagged             : {n_flagged:,} ({n_flagged / total * 100:.1f}%)")
    print(f"  ├─ High risk (≥70)  : {high:,}")
    print(f"  ├─ Medium (40–70)   : {medium:,}")
    print(f"  └─ Low (<40)        : {low:,}")

    # Precision / recall against ground truth label when available
    if "is_fraud" in df.columns:
        tp = int(((df["flagged"]) & (df["is_fraud"] == 1)).sum())
        fp = int(((df["flagged"]) & (df["is_fraud"] == 0)).sum())
        fn = int(((~df["flagged"]) & (df["is_fraud"] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        print(f"\n  Ground truth validation:")
        print(f"  Actual fraud rows   : {int(df['is_fraud'].sum()):,}")
        print(f"  True positives      : {tp:,}")
        print(f"  Precision           : {precision:.2%}")
        print(f"  Recall              : {recall:.2%}")
    print("=" * 56)

    print("\n[plots] Generating visualisations …")
    make_plots(df)
    print(f"\n[done] Outputs written to: {OUTPUT_DIR}")
    print(f"  flagged_transactions.csv ({len(flagged):,} rows)")


if __name__ == "__main__":
    main()
