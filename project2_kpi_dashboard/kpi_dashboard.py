"""
kpi_dashboard.py — Project 2: Interactive KPI Dashboard
Streamlit dashboard for monitoring operational KPIs with anomaly alerts.

Run with:
    streamlit run kpi_dashboard.py
"""
import os
import sys
import subprocess

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_DIR = os.path.dirname(SCRIPT_DIR)
KAGGLE_DIR    = os.path.join(PORTFOLIO_DIR, "data", "project2")
SYNTH_CSV     = os.path.join(PORTFOLIO_DIR, "data", "kpi_data.csv")
GENERATE_PY   = os.path.join(SCRIPT_DIR, "generate_data.py")

KAGGLE_FILENAMES = [
    "DataCoSupplyChainDataset.csv",
    "dataco_supply_chain.csv",
    "supply_chain.csv",
]


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading data …")
def load_data():
    # Try Kaggle dataset variants
    for fname in KAGGLE_FILENAMES:
        path = os.path.join(KAGGLE_DIR, fname)
        if os.path.exists(path):
            try:
                raw = pd.read_csv(path, encoding="latin-1")
                return _process_kaggle(raw), "kaggle"
            except Exception as exc:
                st.warning(f"Could not parse Kaggle file ({fname}): {exc}")

    # Fall back to synthetic data
    if not os.path.exists(SYNTH_CSV):
        subprocess.run([sys.executable, GENERATE_PY], check=True)
    return pd.read_csv(SYNTH_CSV), "synthetic"


def _process_kaggle(raw):
    """Transform Kaggle supply-chain columns into the standard KPI schema."""
    date_col = next((c for c in ["Order Date (DateOrders)", "Order Date", "order_date"]
                     if c in raw.columns), None)
    dept_col = next((c for c in ["Department Name", "department_name", "Department"]
                     if c in raw.columns), None)

    if date_col:
        raw["month"] = pd.to_datetime(raw[date_col], errors="coerce").dt.strftime("%Y-%m")
    else:
        raw["month"] = "2024-01"

    raw["department"] = raw[dept_col].fillna("Unknown") if dept_col else "Logistics"

    rows = []
    for (month, dept), g in raw.groupby(["month", "department"]):
        # On-time delivery %
        if "Late_delivery_risk" in g:
            otd = round(100 - g["Late_delivery_risk"].mean() * 100, 2)
        else:
            otd = 90.0
        rows.append(dict(month=month, department=dept, kpi_id="on_time_delivery_pct",
                         kpi_name="On-Time Delivery %", actual_value=otd,
                         target_value=95.0, unit="%"))

        # Revenue
        sales_col = next((c for c in ["Sales", "sales", "Revenue"] if c in g.columns), None)
        revenue = round(float(g[sales_col].sum()), 2) if sales_col else 0.0
        rows.append(dict(month=month, department=dept, kpi_id="revenue",
                         kpi_name="Revenue", actual_value=revenue,
                         target_value=500000.0, unit="USD"))

        # Orders processed
        rows.append(dict(month=month, department=dept, kpi_id="orders_processed",
                         kpi_name="Orders Processed", actual_value=float(len(g)),
                         target_value=5000.0, unit="units"))

        # Avg benefit per order
        ben_col = next((c for c in ["Benefit per order", "benefit_per_order"] if c in g.columns), None)
        benefit = round(float(g[ben_col].mean()), 2) if ben_col else 0.0
        rows.append(dict(month=month, department=dept, kpi_id="avg_benefit",
                         kpi_name="Avg Benefit/Order", actual_value=benefit,
                         target_value=50.0, unit="USD"))

    return pd.DataFrame(rows)


# ── Dashboard ─────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="KPI Dashboard",
        page_icon="📊",
        layout="wide",
    )
    st.title("📊 Operational KPI Dashboard")

    df, source = load_data()
    st.caption(
        f"Data source: **{source.upper()}**  •  {len(df):,} KPI records  "
        f"•  {df['month'].nunique()} months  •  {df['department'].nunique()} departments"
    )

    # ── Sidebar filters ────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filters")
        all_depts = sorted(df["department"].unique())
        selected_depts = st.multiselect("Department", all_depts, default=all_depts)

        all_months = sorted(df["month"].unique())
        month_range = st.select_slider(
            "Month Range",
            options=all_months,
            value=(all_months[0], all_months[-1]),
        )

        anomaly_threshold = st.slider(
            "Anomaly threshold (%)", min_value=5, max_value=30, value=10, step=5
        )

    # Apply filters
    mask = (
        df["department"].isin(selected_depts)
        & (df["month"] >= month_range[0])
        & (df["month"] <= month_range[1])
    )
    fdf = df[mask].copy()

    if fdf.empty:
        st.warning("No data matches the selected filters.")
        return

    # % of target (handle division by zero)
    fdf["pct_of_target"] = np.where(
        fdf["target_value"] != 0,
        fdf["actual_value"] / fdf["target_value"] * 100,
        np.nan,
    )

    # ── Metric cards (latest month) ────────────────────────────────────────────
    st.subheader("KPI Summary — Latest Available Month")
    latest_month = fdf["month"].max()
    latest = fdf[fdf["month"] == latest_month]
    kpis = latest["kpi_name"].unique()

    cols = st.columns(min(4, len(kpis)))
    for i, kpi in enumerate(kpis[:8]):
        subset = latest[latest["kpi_name"] == kpi]
        if subset.empty:
            continue
        actual = subset["actual_value"].mean()
        target = subset["target_value"].mean()
        delta  = actual - target
        with cols[i % 4]:
            st.metric(
                label=kpi,
                value=f"{actual:,.1f} {subset['unit'].iloc[0]}",
                delta=f"{delta:+.1f} vs target",
            )

    st.divider()

    # ── Bar chart: Actual vs Target ────────────────────────────────────────────
    st.subheader(f"Actual vs Target — {latest_month}")
    bar_df = (
        latest.groupby("kpi_name")[["actual_value", "target_value"]]
        .mean()
        .reset_index()
        .melt(id_vars="kpi_name", var_name="Metric", value_name="Value")
    )
    bar_df["Metric"] = bar_df["Metric"].map(
        {"actual_value": "Actual", "target_value": "Target"}
    )
    fig_bar = px.bar(
        bar_df,
        x="kpi_name", y="Value", color="Metric", barmode="group",
        color_discrete_map={"Actual": "#4C72B0", "Target": "#DD8452"},
        labels={"kpi_name": "KPI", "Value": "Value"},
    )
    fig_bar.update_layout(xaxis_tickangle=-35, legend_title_text="")
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Trend line chart ───────────────────────────────────────────────────────
    st.subheader("KPI Performance Over Time")
    kpi_choice = st.selectbox("Select KPI to trend", sorted(fdf["kpi_name"].unique()))
    trend_df = (
        fdf[fdf["kpi_name"] == kpi_choice]
        .groupby("month")[["actual_value", "target_value"]]
        .mean()
        .reset_index()
        .sort_values("month")
    )
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_df["month"], y=trend_df["actual_value"],
        mode="lines+markers", name="Actual",
        line=dict(color="#4C72B0", width=2),
        marker=dict(size=6),
    ))
    fig_trend.add_trace(go.Scatter(
        x=trend_df["month"], y=trend_df["target_value"],
        mode="lines", name="Target",
        line=dict(color="#DD8452", width=2, dash="dash"),
    ))
    fig_trend.update_layout(
        title=f"{kpi_choice} — Monthly Trend",
        xaxis_title="Month", yaxis_title="Value",
        legend_title_text="",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── Anomaly alerts ─────────────────────────────────────────────────────────
    st.subheader(f"⚠️ Anomaly Alerts — Deviation > {anomaly_threshold}% from Target")
    lo = 100 - anomaly_threshold
    hi = 100 + anomaly_threshold
    anomalies = fdf[
        (fdf["pct_of_target"] < lo) | (fdf["pct_of_target"] > hi)
    ].copy()
    anomalies["deviation %"] = (anomalies["pct_of_target"] - 100).round(1)

    if anomalies.empty:
        st.success(f"✅ All KPIs are within {anomaly_threshold}% of their targets.")
    else:
        st.error(f"🔴 {len(anomalies)} anomalous readings detected")
        st.dataframe(
            anomalies[["month", "department", "kpi_name",
                        "actual_value", "target_value", "unit", "deviation %"]]
            .sort_values("deviation %")
            .reset_index(drop=True),
            use_container_width=True,
        )

    # ── Colour-coded raw data table ────────────────────────────────────────────
    st.subheader("Raw KPI Data (green = on target, red = below target)")
    display = fdf[
        ["month", "department", "kpi_name", "actual_value", "target_value", "unit", "pct_of_target"]
    ].copy()
    display["pct_of_target"] = display["pct_of_target"].round(1)
    display = display.sort_values(["month", "department", "kpi_name"]).reset_index(drop=True)

    def _color_row(row):
        color = "#d4edda" if (row["pct_of_target"] >= 90) else "#f8d7da"
        return [f"background-color: {color}"] * len(row)

    st.dataframe(
        display.style.apply(_color_row, axis=1),
        use_container_width=True,
        height=400,
    )


if __name__ == "__main__":
    main()
