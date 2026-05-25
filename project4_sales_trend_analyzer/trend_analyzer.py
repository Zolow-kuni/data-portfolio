"""
trend_analyzer.py — Project 4: Sales & Inventory Trend Analyzer
Analyses monthly sales trends, anomalies, regional performance, and stock alerts.
Auto-loads Kaggle Superstore CSV if present; otherwise generates synthetic data.
"""
import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
KAGGLE_DIR    = os.path.join(PORTFOLIO_DIR, "data", "project4")
SYNTH_CSV     = os.path.join(PORTFOLIO_DIR, "data", "sales_inventory.csv")
GENERATE_PY   = os.path.join(SCRIPT_DIR, "generate_data.py")
OUTPUT_DIR    = os.path.join(SCRIPT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SUPERSTORE_NAMES = [
    "Sample - Superstore.csv",
    "superstore.csv",
    "Superstore.csv",
    "sample_superstore.csv",
]


# ── Data loading ──────────────────────────────────────────────────────────────
def load_data():
    for fname in SUPERSTORE_NAMES:
        path = os.path.join(KAGGLE_DIR, fname)
        if os.path.exists(path):
            print(f"[load] Kaggle dataset: {path}")
            try:
                raw = pd.read_csv(path, encoding="latin-1")
                return _transform_kaggle(raw), "kaggle"
            except Exception as exc:
                print(f"[load] Warning — could not parse {fname}: {exc}")

    print("[load] Kaggle data not found — synthetic mode.")
    if not os.path.exists(SYNTH_CSV):
        subprocess.run([sys.executable, GENERATE_PY], check=True)
    return pd.read_csv(SYNTH_CSV), "synthetic"


def _transform_kaggle(raw):
    """Map Superstore columns to the standard schema."""
    date_col = next((c for c in ["Order Date", "order_date"] if c in raw.columns), None)
    if not date_col:
        raise ValueError("Cannot find Order Date column in Superstore dataset.")

    raw["_date"] = pd.to_datetime(raw[date_col], dayfirst=False, errors="coerce")
    raw = raw.dropna(subset=["_date"])
    raw["date"] = raw["_date"].dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")

    cat_col  = next((c for c in ["Category", "category"]            if c in raw.columns), None)
    prod_col = next((c for c in ["Sub-Category", "sub_category"]    if c in raw.columns), None)
    reg_col  = next((c for c in ["Region", "region"]                if c in raw.columns), None)
    qty_col  = next((c for c in ["Quantity", "quantity"]            if c in raw.columns), None)
    rev_col  = next((c for c in ["Sales", "sales", "Revenue"]       if c in raw.columns), None)

    agg = (
        raw.groupby(
            ["date",
             raw[cat_col].rename("category")  if cat_col  else pd.Series("Unknown", index=raw.index, name="category"),
             raw[prod_col].rename("product_name") if prod_col else pd.Series("Unknown", index=raw.index, name="product_name"),
             raw[reg_col].rename("region")    if reg_col  else pd.Series("Unknown", index=raw.index, name="region"),
             ]
        )
        .agg(
            units_sold=(qty_col, "sum") if qty_col else ("date", "count"),
            revenue=(rev_col, "sum")    if rev_col else ("date", "count"),
        )
        .reset_index()
    )

    # Add synthetic stock data (not in Superstore)
    rng = np.random.default_rng(0)
    products = agg["product_name"].unique()
    pid_map  = {p: f"P{i:03d}" for i, p in enumerate(products, 1)}
    reorder  = {pid: int(rng.integers(30, 100)) for pid in pid_map.values()}

    agg["product_id"]    = agg["product_name"].map(pid_map)
    agg["stock_level"]   = rng.integers(0, 300, len(agg))
    agg["reorder_point"] = agg["product_id"].map(reorder).fillna(50).astype(int)

    return agg


# ── Analysis ───────────────────────────────────────────────────────────────────
def compute_monthly_metrics(df):
    """Aggregate to monthly level, compute MoM growth and rolling average."""
    monthly = (
        df.groupby("date")[["revenue", "units_sold"]]
        .sum()
        .reset_index()
        .sort_values("date")
    )
    monthly["rev_mom_pct"]   = monthly["revenue"].pct_change() * 100
    monthly["units_mom_pct"] = monthly["units_sold"].pct_change() * 100
    monthly["rev_roll3"]     = monthly["revenue"].rolling(3, min_periods=1).mean()
    monthly["units_roll3"]   = monthly["units_sold"].rolling(3, min_periods=1).mean()

    # Flag months where revenue deviates >15% from rolling average
    monthly["rev_anomaly"] = (
        (monthly["revenue"] - monthly["rev_roll3"]).abs()
        / monthly["rev_roll3"].replace(0, np.nan)
        > 0.15
    )
    return monthly


def get_low_stock(df):
    """Return products whose latest stock falls below their reorder point."""
    latest = df[df["date"] == df["date"].max()].copy()
    return latest[latest["stock_level"] < latest["reorder_point"]]


def regional_ranking(df):
    """Rank regions by total revenue per month."""
    reg = df.groupby(["date", "region"])["revenue"].sum().reset_index()
    reg["rank"] = reg.groupby("date")["revenue"].rank(ascending=False).astype(int)
    return reg.sort_values(["date", "rank"])


def seasonal_summary(df):
    """Average revenue per calendar month across all years."""
    df = df.copy()
    df["cal_month"] = pd.to_datetime(df["date"]).dt.month
    seasonal = df.groupby("cal_month")["revenue"].mean().reset_index()
    seasonal["above_avg"] = seasonal["revenue"] > seasonal["revenue"].mean()
    return seasonal


# ── Visualisations ─────────────────────────────────────────────────────────────
def make_plots(df, monthly, low_stock):
    plt.style.use("seaborn-v0_8-whitegrid")
    MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    # ── 1: Revenue trend with rolling avg + anomaly markers ───────────────────
    fig, ax = plt.subplots(figsize=(13, 5))
    x_ticks = range(len(monthly))
    ax.plot(monthly["date"], monthly["revenue"],
            color="#4C72B0", marker="o", ms=4, linewidth=1.8, label="Monthly Revenue")
    ax.plot(monthly["date"], monthly["rev_roll3"],
            color="#DD8452", linestyle="--", linewidth=2, label="3-Month Rolling Avg")
    anomalies = monthly[monthly["rev_anomaly"]]
    if not anomalies.empty:
        ax.scatter(anomalies["date"], anomalies["revenue"],
                   color="red", zorder=6, s=90, label="Anomaly (>15% from rolling avg)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Monthly Revenue Trend — Rolling Average & Anomaly Markers")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    plt.xticks(rotation=45, ha="right", fontsize=7)
    ax.legend()
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "revenue_trend.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # ── 2: Regional revenue grouped bar (last 6 months) ───────────────────────
    recent_dates = sorted(df["date"].unique())[-6:]
    recent = df[df["date"].isin(recent_dates)]
    reg_cat = recent.groupby(["date", "region", "category"])["revenue"].sum().reset_index()

    regions  = sorted(reg_cat["region"].unique())
    cats     = sorted(reg_cat["category"].unique())
    dates    = sorted(reg_cat["date"].unique())
    x        = np.arange(len(dates))
    n_groups = len(regions) * len(cats)
    width    = 0.8 / n_groups
    cmap     = plt.cm.Set2(np.linspace(0, 1, len(cats)))

    fig, ax = plt.subplots(figsize=(13, 6))
    for ri, region in enumerate(regions):
        for ci, cat in enumerate(cats):
            sub  = reg_cat[(reg_cat["region"] == region) & (reg_cat["category"] == cat)]
            vals = [sub[sub["date"] == d]["revenue"].sum() for d in dates]
            offset = (ri * len(cats) + ci) * width - 0.4 + width / 2
            ax.bar(x + offset, vals, width * 0.9,
                   label=f"{region} / {cat}", color=cmap[ci], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Revenue ($)")
    ax.set_title("Regional Revenue by Category — Last 6 Months")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.legend(fontsize=7, ncol=min(3, n_groups), loc="upper left")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "regional_revenue.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # ── 3: Revenue heatmap (month × category) ─────────────────────────────────
    pivot = df.pivot_table(values="revenue", index="date", columns="category", aggfunc="sum")
    pivot_k = pivot / 1000  # show in thousands
    fig_h = max(6, len(pivot) * 0.35)
    fig_w = max(7, len(pivot.columns) * 2.2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    sns.heatmap(
        pivot_k,
        annot=(len(pivot) <= 30),
        fmt=".0f",
        cmap="YlOrRd",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Revenue (K USD)"},
    )
    ax.set_title("Revenue Heatmap: Month × Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Month")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "revenue_heatmap.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")

    # ── 4: Low-stock alert table ───────────────────────────────────────────────
    if low_stock.empty:
        print("  No low-stock products — skipping alert chart.")
        return

    show_cols = [c for c in ["product_id", "product_name", "region", "category",
                              "stock_level", "reorder_point"] if c in low_stock.columns]
    tbl = low_stock[show_cols].reset_index(drop=True)
    fig_height = max(2.5, len(tbl) * 0.45 + 1.2)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.axis("off")
    the_table = ax.table(
        cellText=tbl.values.tolist(),
        colLabels=tbl.columns.tolist(),
        cellLoc="center",
        loc="center",
    )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(9)
    the_table.scale(1.15, 1.6)
    for j in range(len(tbl.columns)):
        the_table[(0, j)].set_facecolor("#C44E52")
        the_table[(0, j)].set_text_props(color="white", fontweight="bold")
    ax.set_title("Low Stock Alert — Products Below Reorder Point",
                 pad=16, fontsize=11, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "low_stock_alert.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Saved: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    df, source = load_data()
    print(f"[data] {len(df):,} rows loaded (source: {source})")

    monthly   = compute_monthly_metrics(df)
    low_stock = get_low_stock(df)
    regional  = regional_ranking(df)
    seasonal  = seasonal_summary(df)

    # Save trend report
    report_path = os.path.join(OUTPUT_DIR, "trend_report.csv")
    monthly.to_csv(report_path, index=False)

    # Month-name lookup
    MN = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
          7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

    # ── Terminal summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  SALES & INVENTORY TREND REPORT")
    print("=" * 65)
    print(f"  Period          : {df['date'].min()} → {df['date'].max()}")
    print(f"  Total revenue   : ${df['revenue'].sum():>14,.2f}")
    print(f"  Total units sold: {df['units_sold'].sum():>14,}")
    print(f"  Anomaly months  : {int(monthly['rev_anomaly'].sum())}")

    print("\n  Month-over-Month Revenue Growth (last 6 months):")
    for _, row in monthly.dropna(subset=["rev_mom_pct"]).tail(6).iterrows():
        arrow = "↑" if row["rev_mom_pct"] > 0 else "↓"
        print(f"    {row['date']}   {arrow} {row['rev_mom_pct']:+.1f}%")

    print("\n  Seasonal Highlights:")
    best  = seasonal.nlargest(3, "revenue")["cal_month"].tolist()
    worst = seasonal.nsmallest(3, "revenue")["cal_month"].tolist()
    print(f"    Strongest months : {', '.join(MN[m] for m in best)}")
    print(f"    Weakest months   : {', '.join(MN[m] for m in worst)}")

    print("\n  Regional Ranking (latest month):")
    latest_regional = regional[regional["date"] == regional["date"].max()]
    for _, row in latest_regional.iterrows():
        print(f"    #{int(row['rank'])}  {row['region']:<12}  ${row['revenue']:>12,.2f}")

    print(f"\n  Low Stock Alerts: {len(low_stock)} products below reorder point")
    if not low_stock.empty:
        show = [c for c in ["product_name", "region", "stock_level", "reorder_point"]
                if c in low_stock.columns]
        print(low_stock[show].to_string(index=False))

    print("=" * 65)

    print("\n[plots] Generating visualisations …")
    make_plots(df, monthly, low_stock)
    print(f"\n[done] Outputs written to: {OUTPUT_DIR}")
    print(f"  trend_report.csv ({len(monthly)} rows)")


if __name__ == "__main__":
    main()
