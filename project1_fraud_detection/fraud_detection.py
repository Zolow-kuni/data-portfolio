"""
fraud_detection.py — Project 1: Fraud & Anomaly Detection System
Detects anomalous transactions using Z-score, IQR, and rule-based risk scoring.
Uses real Kaggle creditcard dataset with strict data cleaning pipeline.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.preprocessing import StandardScaler

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
KAGGLE_CSV    = r"C:\Users\lalit\Downloads\creditcard\creditcard.csv"
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Data cleaning pipeline ────────────────────────────────────────────────────
def load_and_clean():
    """
    Load creditcard.csv and implement 10-step cleaning pipeline:
    1. Load with pd.read_csv()
    2. Drop nulls
    3. Remove duplicates
    4. Log-transform Amount
    5. Extract Hour from Time
    6. Note class imbalance (99.83% normal, 0.17% fraud)
    7. Scale Amount_log and Time with StandardScaler
    8. Remove Time column
    9. Validate Class values
    10. Print cleaning summary
    """
    print("[1/10] Loading dataset …")
    df = pd.read_csv(KAGGLE_CSV)
    rows_loaded = len(df)
    print(f"       {rows_loaded:,} rows loaded")

    print("[2/10] Checking for nulls …")
    nulls_before = df.isnull().sum().sum()
    df = df.dropna()
    nulls_removed = rows_loaded - len(df)
    print(f"       Removed {nulls_removed:,} null rows")

    print("[3/10] Removing duplicates …")
    dups_before = len(df)
    df = df.drop_duplicates()
    dups_removed = dups_before - len(df)
    print(f"       Removed {dups_removed:,} duplicate rows")

    print("[4/10] Log-transforming Amount …")
    df["Amount_log"] = np.log1p(df["Amount"])
    print(f"       Amount range: {df['Amount'].min():.2f} – {df['Amount'].max():.2f}")
    print(f"       Amount_log range: {df['Amount_log'].min():.4f} – {df['Amount_log'].max():.4f}")

    print("[5/10] Extracting Hour from Time …")
    df["Hour"] = (df["Time"] // 3600) % 24
    print(f"       Hour range: {df['Hour'].min()} – {df['Hour'].max()}")

    print("[6/10] Checking class imbalance …")
    fraud_count = (df["Class"] == 1).sum()
    fraud_pct = fraud_count / len(df) * 100
    print(f"       Fraud cases: {fraud_count:,} ({fraud_pct:.2f}%)")
    print(f"       Normal cases: {len(df) - fraud_count:,} ({100 - fraud_pct:.2f}%)")
    print(f"       NOTE: Using raw imbalanced data (NOT resampling)")

    print("[7/10] Feature scaling …")
    scaler = StandardScaler()
    df["Amount_log_scaled"] = scaler.fit_transform(df[["Amount_log"]])
    df["Time_scaled"] = scaler.fit_transform(df[["Time"]])
    print(f"       Scaled Amount_log and Time with StandardScaler")

    print("[8/10] Removing Time column …")
    df = df.drop(columns=["Time"])
    print(f"       Time column removed")

    print("[9/10] Validating Class values …")
    class_vals = df["Class"].unique()
    if set(class_vals) == {0, 1}:
        print(f"       ✓ Class contains only [0, 1]")
    else:
        print(f"       ✗ WARNING: Class contains unexpected values: {sorted(class_vals)}")

    print("[10/10] Cleaning summary …")
    clean_rows = len(df)
    print(f"\n  ┌─ CLEANING SUMMARY ─────────────────────────────────┐")
    print(f"  │ Rows loaded         : {rows_loaded:,}")
    print(f"  │ Nulls removed       : {nulls_removed:,}")
    print(f"  │ Duplicates removed  : {dups_removed:,}")
    print(f"  │ Final clean rows    : {clean_rows:,}")
    print(f"  │ Fraud count         : {fraud_count:,} ({fraud_pct:.2f}%)")
    print(f"  └─────────────────────────────────────────────────────┘")

    return df, rows_loaded, nulls_removed, dups_removed, clean_rows


# ── Anomaly detection: Z-score ─────────────────────────────────────────────────
def flag_zscore(df, col="Amount_log_scaled", threshold=2.5):
    """Flag rows where scaled Amount_log is > threshold SDs from mean."""
    z = np.abs(stats.zscore(df[col].fillna(0)))
    return pd.Series(z > threshold, index=df.index)


# ── Anomaly detection: IQR ────────────────────────────────────────────────────
def flag_iqr(df, col="Amount", top_pct=99):
    """Flag rows in top 1% of Amount distribution."""
    cutoff = np.percentile(df[col].fillna(0), top_pct)
    return df[col] > cutoff


# ── Rule-based risk scoring (0–100) ───────────────────────────────────────────
def compute_risk_score(df):
    """
    Score each transaction 0–100 using Amount_log, Hour, V1, V4, V14.
    These V-columns are most correlated with fraud in the dataset.
    """
    score = pd.Series(0.0, index=df.index)

    # Amount_log component (0–40 pts)
    amt = df["Amount_log"].fillna(0)
    amt_range = amt.max() - amt.min()
    if amt_range > 0:
        score += (amt - amt.min()) / amt_range * 40

    # Hour component (0–20 pts) - late night riskier
    hour = df["Hour"].fillna(12)
    hour_risk = ((hour <= 4) | (hour >= 22)).astype(int) * 20
    score += hour_risk

    # V-feature components (V1, V4, V14 - fraud indicators)
    for v_col, weight in [("V1", 15), ("V4", 15), ("V14", 10)]:
        if v_col in df.columns:
            v = df[v_col].fillna(0)
            v_range = np.abs(v).max()
            if v_range > 0:
                score += (np.abs(v) / v_range) * weight

    return score.clip(0, 100)


# ── Visualisations ────────────────────────────────────────────────────────────
def make_plots(df):
    """Generate 3 visualization plots."""
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

    # 3 — Amount vs Hour scatter (coloured by risk score)
    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(
        df["Amount"], df["Hour"],
        c=df["risk_score"], cmap="RdYlGn_r",
        alpha=0.45, s=12, vmin=0, vmax=100,
    )
    plt.colorbar(sc, ax=ax, label="Risk Score")
    ax.set_xlabel("Transaction Amount ($)")
    ax.set_ylabel("Hour of Day")
    ax.set_title("Amount vs Hour — Coloured by Risk Score")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "amount_vs_hour.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("  FRAUD DETECTION — DATA CLEANING & ANALYSIS")
    print("=" * 60 + "\n")

    df, rows_loaded, nulls_removed, dups_removed, clean_rows = load_and_clean()

    print("\n[ANALYSIS] Computing anomaly detection …\n")

    # Anomaly detection flags
    df["zscore_flag"] = flag_zscore(df)
    df["iqr_flag"]    = flag_iqr(df)

    # Risk scoring
    df["risk_score"]  = compute_risk_score(df)
    df["risk_level"]  = pd.cut(
        df["risk_score"],
        bins=[0, 40, 70, 100],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    )
    df["flagged"] = df["zscore_flag"] | df["iqr_flag"] | (df["risk_score"] >= 70)

    # Save flagged transactions
    flagged = df[df["flagged"]].copy()
    out_cols = ["Amount", "Hour", "V1", "V4", "V14", "risk_score", "risk_level",
                "zscore_flag", "iqr_flag", "Class"]
    out_cols = [c for c in out_cols if c in flagged.columns]
    flagged_path = os.path.join(OUTPUT_DIR, "flagged_transactions.csv")
    flagged[out_cols].sort_values("risk_score", ascending=False).to_csv(
        flagged_path, index=False
    )

    # ── Terminal summary ───────────────────────────────────────────────────
    total    = len(df)
    n_flagged = df["flagged"].sum()
    high     = (df["risk_level"] == "High").sum()
    medium   = (df["risk_level"] == "Medium").sum()
    low      = (df["risk_level"] == "Low").sum()

    print("=" * 60)
    print("  ANOMALY DETECTION SUMMARY")
    print("=" * 60)
    print(f"  Total transactions  : {total:,}")
    print(f"  Flagged             : {n_flagged:,} ({n_flagged / total * 100:.2f}%)")
    print(f"  ├─ High risk (≥70)  : {high:,}")
    print(f"  ├─ Medium (40–70)   : {medium:,}")
    print(f"  └─ Low (<40)        : {low:,}")

    if "Class" in df.columns:
        tp = int(((df["flagged"]) & (df["Class"] == 1)).sum())
        fp = int(((df["flagged"]) & (df["Class"] == 0)).sum())
        fn = int(((~df["flagged"]) & (df["Class"] == 1)).sum())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        print(f"\n  PRECISION & RECALL (vs ground truth):")
        print(f"  True positives      : {tp:,}")
        print(f"  False positives     : {fp:,}")
        print(f"  False negatives     : {fn:,}")
        print(f"  Precision           : {precision:.2%}")
        print(f"  Recall              : {recall:.2%}")
    print("=" * 60)

    print("\n[PLOTS] Generating visualisations …")
    make_plots(df)

    print(f"\n[DONE] All outputs written to:")
    print(f"  {OUTPUT_DIR}")
    print(f"  → flagged_transactions.csv ({len(flagged):,} rows)")
    print(f"  → risk_score_histogram.png")
    print(f"  → flagged_vs_normal.png")
    print(f"  → amount_vs_hour.png\n")

    return rows_loaded, clean_rows


if __name__ == "__main__":
    main()
