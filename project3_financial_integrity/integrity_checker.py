"""
integrity_checker.py — Project 3: Financial Data Integrity Checker
Validates financial records against 10 business rules and scores overall data quality.
Auto-loads Kaggle financials.csv if present; otherwise generates synthetic data.
"""
import os
import sys
import subprocess
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
KAGGLE_CSV    = os.path.join(PORTFOLIO_DIR, "data", "project3", "financials.csv")
SYNTH_CSV     = os.path.join(PORTFOLIO_DIR, "data", "financial_records.csv")
GENERATE_PY   = os.path.join(SCRIPT_DIR, "generate_data.py")
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VENDOR_IDS       = {f"VND{i:03d}" for i in range(1, 51)}
VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP"}
VALID_STATUSES   = {"paid", "pending", "overdue"}
REQUIRED_FIELDS  = ["record_id", "date", "vendor_id", "amount",
                     "currency", "payment_status", "delivery_date"]
DATE_PATTERN     = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Data loading ──────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(KAGGLE_CSV):
        print(f"[load] Kaggle dataset: {KAGGLE_CSV}")
        raw = pd.read_csv(KAGGLE_CSV, encoding="latin-1", thousands=",")
        return _transform_kaggle(raw)

    print("[load] Kaggle data not found — synthetic mode.")
    if not os.path.exists(SYNTH_CSV):
        subprocess.run([sys.executable, GENERATE_PY], check=True)
    return pd.read_csv(SYNTH_CSV)


def _transform_kaggle(raw):
    """Map Kaggle financials columns to the standard schema and inject errors."""
    n = len(raw)
    rng = np.random.default_rng(0)

    # Parse dates from Kaggle
    date_col = next((c for c in ["Date", "date", "Order Date"] if c in raw.columns), None)
    if date_col:
        parsed = pd.to_datetime(raw[date_col], errors="coerce")
    else:
        parsed = pd.Series([pd.Timestamp("2023-06-01")] * n)
    parsed = parsed.fillna(pd.Timestamp("2023-06-01"))
    delivery = parsed + pd.to_timedelta(rng.integers(1, 30, n), unit="D")

    # Gross Sales or Sale Price as amount — strip currency symbols/commas
    amt_col = next((c for c in ["Gross Sales", "Sale Price", "Sales"] if c in raw.columns), None)
    if amt_col:
        amounts = (
            raw[amt_col]
            .astype(str)
            .str.replace(r"[\$,]", "", regex=True)
            .pipe(pd.to_numeric, errors="coerce")
            .abs()
            .fillna(1000)
        )
    else:
        amounts = pd.Series(rng.lognormal(8, 1.5, n).clip(50, 500_000))

    df = pd.DataFrame({
        "record_id":      [f"REC{i:05d}" for i in range(n)],
        "date":           parsed.dt.strftime("%Y-%m-%d"),
        "vendor_id":      rng.choice(sorted(VENDOR_IDS), n),
        "amount":         np.round(amounts.values, 2),
        "currency":       rng.choice(sorted(VALID_CURRENCIES), n),
        "region":         raw.get("Country", pd.Series(["Unknown"] * n)).fillna("Unknown").values,
        "invoice_ref":    [f"INV-{rng.integers(10000, 99999)}" for _ in range(n)],
        "payment_status": rng.choice(sorted(VALID_STATUSES), n),
        "delivery_date":  delivery.dt.strftime("%Y-%m-%d"),
        "created_by":     [f"user_{rng.integers(1, 21)}" for _ in range(n)],
    })

    # Inject ~7% errors so validation rules have something to catch
    n_err = max(1, int(n * 0.07))
    err_idx = rng.choice(n, n_err, replace=False)
    buckets = np.array_split(err_idx, 4)
    for i in buckets[0]: df.at[int(i), "amount"] = float(rng.choice([-500, 0]))
    for i in buckets[1]: df.at[int(i), "currency"] = rng.choice(["XYZ", "AUD"])
    for i in buckets[2]: df.at[int(i), "payment_status"] = "cancelled"
    for i in buckets[3]: df.at[int(i), "vendor_id"] = "VND999"   # orphan

    return df


# ── Validation rules ───────────────────────────────────────────────────────────
def run_rules(df):
    """Run 10 validation rules and return a results DataFrame."""
    results = []

    def _record(name, severity, bad_mask):
        """Add a rule result, capturing up to 10 violating record IDs."""
        bad_idx = df.index[bad_mask].tolist()
        ids_col = "record_id" if "record_id" in df.columns else None
        sample_ids = (
            df.loc[bad_idx[:10], ids_col].tolist() if ids_col else bad_idx[:10]
        )
        preview = ", ".join(str(x) for x in sample_ids)
        if len(bad_idx) > 10:
            preview += " …"
        results.append({
            "rule":       name,
            "severity":   severity,
            "status":     "PASS" if not bad_idx else "FAIL",
            "violations": len(bad_idx),
            "sample_ids": preview,
        })

    # 1 — No nulls in required fields
    null_mask = df[REQUIRED_FIELDS].isnull().any(axis=1)
    _record("1. No nulls in required fields", "Critical", null_mask)

    # 2 — No duplicate record_id
    dup_mask = df["record_id"].duplicated(keep=False)
    _record("2. No duplicate record_id", "Critical", dup_mask)

    # 3 — Date format YYYY-MM-DD
    bad_fmt = ~df["date"].astype(str).apply(lambda v: bool(DATE_PATTERN.match(str(v))))
    _record("3. Date format YYYY-MM-DD", "Major", bad_fmt)

    # 4 — delivery_date after date (only where both dates parse cleanly)
    valid_both = (~bad_fmt) & df["delivery_date"].astype(str).apply(
        lambda v: bool(DATE_PATTERN.match(str(v)))
    )
    d1 = pd.to_datetime(df.loc[valid_both, "date"], errors="coerce")
    d2 = pd.to_datetime(df.loc[valid_both, "delivery_date"], errors="coerce")
    early_delivery = pd.Series(False, index=df.index)
    early_delivery.loc[valid_both] = (d2 < d1).values
    _record("4. delivery_date after date", "Major", early_delivery)

    # 5 — amount > 0
    bad_amount = pd.to_numeric(df["amount"], errors="coerce").fillna(-1) <= 0
    _record("5. amount > 0", "Critical", bad_amount)

    # 6 — amount within 3 SDs of mean (outlier check)
    amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    mean, sd = amounts.mean(), amounts.std()
    outlier_mask = (amounts - mean).abs() > 3 * sd if sd > 0 else pd.Series(False, index=df.index)
    _record("6. amount within 3 SD (outlier)", "Minor", outlier_mask)

    # 7 — Valid currency code
    bad_currency = ~df["currency"].astype(str).isin(VALID_CURRENCIES)
    _record("7. currency in {INR, USD, EUR, GBP}", "Major", bad_currency)

    # 8 — vendor_id in reference list
    bad_vendor = ~df["vendor_id"].astype(str).isin(VENDOR_IDS)
    _record("8. vendor_id in reference list", "Critical", bad_vendor)

    # 9 — payment_status valid
    bad_status = ~df["payment_status"].astype(str).isin(VALID_STATUSES)
    _record("9. payment_status in {paid, pending, overdue}", "Major", bad_status)

    # 10 — Column completeness ≥ 95%
    incomplete_cols = [c for c in df.columns if df[c].notnull().mean() < 0.95]
    completeness_fail = pd.Series(False, index=df.index)
    if incomplete_cols:
        completeness_fail = df[incomplete_cols].isnull().any(axis=1)
    _record(
        f"10. All columns ≥ 95% non-null"
        + (f" (failing: {', '.join(incomplete_cols)})" if incomplete_cols else ""),
        "Minor",
        completeness_fail,
    )

    return pd.DataFrame(results)


# ── Visualisations ─────────────────────────────────────────────────────────────
def make_plots(results_df):
    plt.style.use("seaborn-v0_8-whitegrid")

    # 1 — Bar chart: violations per rule
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = ["#C44E52" if s == "FAIL" else "#55A868" for s in results_df["status"]]
    labels = [r[:38] for r in results_df["rule"]]
    ax.bar(labels, results_df["violations"], color=colors, edgecolor="white")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Violation Count")
    ax.set_title("Data Quality Violations per Validation Rule")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "violations_by_rule.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # 2 — Pie chart: pass/fail distribution
    pass_n = (results_df["status"] == "PASS").sum()
    fail_n = (results_df["status"] == "FAIL").sum()
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.pie(
        [pass_n, fail_n],
        labels=[f"Rules Passed ({pass_n})", f"Rules Failed ({fail_n})"],
        colors=["#55A868", "#C44E52"],
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )
    ax.set_title("Rule Pass / Fail Distribution")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "rule_severity_pie.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    df = load_data()
    print(f"[data] {len(df):,} rows loaded, {df.shape[1]} columns")

    results = run_rules(df)

    # Save integrity report
    report_path = os.path.join(OUTPUT_DIR, "integrity_report.csv")
    results.to_csv(report_path, index=False)

    # Compute overall integrity score
    n_rules  = len(results)
    n_passed = (results["status"] == "PASS").sum()
    score    = n_passed / n_rules * 100

    # ── Terminal summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  FINANCIAL DATA INTEGRITY REPORT")
    print("=" * 65)
    for _, row in results.iterrows():
        icon = "✅" if row["status"] == "PASS" else "❌"
        sev  = f"[{row['severity']}]"
        print(f"  {icon} {sev:<12} {row['rule'][:42]:<42}  {row['violations']:>4} violations")
    print("-" * 65)
    grade = "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D"
    print(f"  Overall Integrity Score : {score:.1f}%  (Grade: {grade})")
    print(f"  Rules passed / total    : {n_passed} / {n_rules}")
    print("=" * 65)

    print("\n[plots] Generating visualisations …")
    make_plots(results)
    print(f"\n[done] Outputs written to: {OUTPUT_DIR}")
    print(f"  integrity_report.csv")


if __name__ == "__main__":
    main()
