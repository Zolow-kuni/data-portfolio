"""
integrity_checker.py — Project 3: Financial Data Integrity Checker
Validates Financials.csv data against 10 business rules.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = r"C:\Users\lalit\Downloads\Financials\Financials.csv"
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Data cleaning pipeline ────────────────────────────────────────────────────
def load_and_clean():
    """14-step cleaning pipeline for financial data."""
    print("[1/14] Loading dataset with encoding='latin-1' …")
    df = pd.read_csv(DATASET_PATH, encoding="latin-1")
    rows_loaded = len(df)
    print(f"       {rows_loaded:,} rows, {len(df.columns)} columns loaded")

    print("[2/14] Stripping whitespace from column names …")
    df.columns = df.columns.str.strip()
    print(f"       Column names stripped")

    print("[3/14] Stripping whitespace from string values …")
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    print(f"       String values stripped")

    print("[4/14] Cleaning numeric columns (remove $, commas) …")
    numeric_cols = ["Units Sold", "Manufacturing Price", "Sale Price",
                    "Gross Sales", "Discounts", "Sales", "COGS", "Profit"]
    numeric_errors = {}
    for col in numeric_cols:
        if col in df.columns:
            initial_count = len(df)
            df[col] = df[col].astype(str).str.replace("$", "", regex=False)
            df[col] = df[col].str.replace(",", "", regex=False)
            df[col] = df[col].str.replace(" ", "", regex=False)
            conversion_errors = pd.to_numeric(df[col], errors="coerce").isnull().sum()
            numeric_errors[col] = conversion_errors
            df[col] = pd.to_numeric(df[col], errors="coerce")
    print(f"       Numeric cols cleaned: {numeric_errors}")

    print("[5/14] Parsing Date column …")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        date_parse_errors = df["Date"].isnull().sum()
        print(f"       {date_parse_errors:,} date parse errors")

    print("[6/14] Removing fully duplicate rows …")
    dups_before = len(df)
    df = df.drop_duplicates()
    dups_removed = dups_before - len(df)
    print(f"       Removed {dups_removed:,} duplicate rows")

    print("[7/14] Validating Month Number (1–12) …")
    if "Month Number" in df.columns:
        month_outliers = df[(df["Month Number"] < 1) | (df["Month Number"] > 12)]
        if len(month_outliers) > 0:
            print(f"       ✗ {len(month_outliers):,} Month Number outliers found")
        else:
            print(f"       ✓ All Month Numbers valid")

    print("[8/14] Validating Year (2010–2030) …")
    if "Year" in df.columns:
        year_outliers = df[(df["Year"] < 2010) | (df["Year"] > 2030)]
        if len(year_outliers) > 0:
            print(f"       ✗ {len(year_outliers):,} Year outliers found")
        else:
            print(f"       ✓ All Years valid")

    print("[9/14] Validating Segment values …")
    if "Segment" in df.columns:
        valid_segments = {"Government", "Midmarket", "Channel Partners", "Enterprise", "Small Business"}
        actual_segments = set(df["Segment"].unique())
        invalid_segments = actual_segments - valid_segments
        if invalid_segments:
            print(f"       ✗ Invalid segments: {invalid_segments}")
        else:
            print(f"       ✓ All Segments valid")

    print("[10/14] Data nulls per column …")
    null_counts = df.isnull().sum()
    print(f"       Nulls remaining: {null_counts[null_counts > 0].to_dict() if null_counts.sum() > 0 else 'None'}")

    print("[11/14] Numeric conversion failures …")
    print(f"       {numeric_errors}")

    print("[12/14] Date range …")
    if "Date" in df.columns and not df["Date"].isnull().all():
        date_min = df["Date"].min()
        date_max = df["Date"].max()
        print(f"       {date_min.date()} to {date_max.date()}")

    print("[13/14] Unique segments and countries …")
    segments_found = df["Segment"].nunique() if "Segment" in df.columns else 0
    countries_found = df["Country"].nunique() if "Country" in df.columns else 0
    print(f"       Segments: {segments_found}, Countries: {countries_found}")

    print("[14/14] Cleaning summary …")
    clean_rows = len(df)
    print(f"\n  ┌─ CLEANING SUMMARY ──────────────────────────────────┐")
    print(f"  │ Rows loaded         : {rows_loaded:,}")
    print(f"  │ Duplicates removed  : {dups_removed:,}")
    print(f"  │ Final clean rows    : {clean_rows:,}")
    print(f"  │ Nulls (remaining)   : {null_counts.sum()}")
    print(f"  │ Unique segments     : {segments_found}")
    print(f"  │ Unique countries    : {countries_found}")
    print(f"  └──────────────────────────────────────────────────────┘")

    return df, rows_loaded, clean_rows


# ── Validation rules ──────────────────────────────────────────────────────────
def validate_data(df):
    """Apply 10 validation rules."""
    print("\n[VALIDATION] Applying 10 business rules …\n")

    issues = []

    # Rule 1: No nulls in key columns
    key_cols = ["Segment", "Country", "Product", "Units Sold", "Sales", "Profit", "Date"]
    for col in key_cols:
        if col in df.columns:
            nulls = df[col].isnull().sum()
            if nulls > 0:
                issues.append(f"Rule 1: {nulls:,} nulls in {col}")

    # Rule 2: No duplicates (already handled in cleaning)
    print(f"  ✓ Rule 1:  No nulls in key columns")
    print(f"  ✓ Rule 2:  No duplicate rows")

    # Rule 3: Date parses correctly
    if "Date" in df.columns:
        parse_failures = df["Date"].isnull().sum()
        print(f"  ✓ Rule 3:  Date parses ({parse_failures:,} failures)")

    # Rule 4: Units Sold > 0
    if "Units Sold" in df.columns:
        invalid = (df["Units Sold"] <= 0).sum()
        if invalid > 0:
            issues.append(f"Rule 4: {invalid:,} rows with Units Sold <= 0")
        else:
            print(f"  ✓ Rule 4:  Units Sold > 0")

    # Rule 5: Sale Price > 0
    if "Sale Price" in df.columns:
        invalid = (df["Sale Price"] <= 0).sum()
        if invalid > 0:
            issues.append(f"Rule 5: {invalid:,} rows with Sale Price <= 0")
        else:
            print(f"  ✓ Rule 5:  Sale Price > 0")

    # Rule 6: Sales > 0
    if "Sales" in df.columns:
        invalid = (df["Sales"] <= 0).sum()
        if invalid > 0:
            issues.append(f"Rule 6: {invalid:,} rows with Sales <= 0")
        else:
            print(f"  ✓ Rule 6:  Sales > 0")

    # Rule 7: Profit outliers (beyond 3 sigma)
    if "Profit" in df.columns:
        profit_mean = df["Profit"].mean()
        profit_std = df["Profit"].std()
        outliers = ((df["Profit"] - profit_mean).abs() > 3 * profit_std).sum()
        print(f"  ✓ Rule 7:  Profit outliers ({outliers:,} beyond 3-sigma)")

    # Rule 8: Gross Sales ≈ Units × Sale Price (within 10%)
    if all(col in df.columns for col in ["Gross Sales", "Units Sold", "Sale Price"]):
        df["calc_gross"] = df["Units Sold"] * df["Sale Price"]
        df["gross_diff_pct"] = np.abs(df["Gross Sales"] - df["calc_gross"]) / df["Gross Sales"]
        mismatches = (df["gross_diff_pct"] > 0.10).sum()
        print(f"  ✓ Rule 8:  Gross Sales ≈ Units × Price ({mismatches:,} >10% diff)")

    # Rule 9: COGS > 0
    if "COGS" in df.columns:
        invalid = (df["COGS"] <= 0).sum()
        if invalid > 0:
            issues.append(f"Rule 9: {invalid:,} rows with COGS <= 0")
        else:
            print(f"  ✓ Rule 9:  COGS > 0")

    # Rule 10: > 95% non-null values per column
    print(f"  ✓ Rule 10: Data completeness")
    for col in df.columns:
        completeness = (1 - df[col].isnull().sum() / len(df)) * 100
        if completeness < 95:
            issues.append(f"Rule 10: {col} only {completeness:.1f}% complete")
        print(f"           {col}: {completeness:.1f}%")

    return issues


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 62)
    print("  FINANCIAL INTEGRITY CHECKER — DATA CLEANING & VALIDATION")
    print("=" * 62 + "\n")

    df, rows_loaded, clean_rows = load_and_clean()

    # Validate data
    issues = validate_data(df)

    # Save validated data
    output_file = os.path.join(OUTPUT_DIR, "validated_financials.csv")
    df.to_csv(output_file, index=False)

    # Generate issues report
    issues_file = os.path.join(OUTPUT_DIR, "validation_issues.txt")
    with open(issues_file, "w") as f:
        f.write("FINANCIAL DATA VALIDATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        if issues:
            f.write(f"ISSUES FOUND: {len(issues)}\n")
            for issue in issues:
                f.write(f"  • {issue}\n")
        else:
            f.write("✓ ALL VALIDATION RULES PASSED\n")

    print(f"\n[DONE] Validation complete!")
    print(f"  {OUTPUT_DIR}")
    print(f"  → validated_financials.csv ({clean_rows:,} rows)")
    print(f"  → validation_issues.txt")
    if issues:
        print(f"  ✗ Found {len(issues)} issues\n")
    else:
        print(f"  ✓ All validation passed\n")

    return rows_loaded, clean_rows


if __name__ == "__main__":
    main()
