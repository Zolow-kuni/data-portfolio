# ============================================================
# Automatidata – Course 2 End-of-Course Project
# NYC TLC Yellow Taxi 2017 – Exploratory Data Analysis
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

df = pd.read_csv('2017_Yellow_Taxi_Trip_Data.csv')
print(f'Shape: {df.shape[0]:,} rows x {df.shape[1]} columns')
print(df.head())
print(df.dtypes)
print(df.isnull().sum())
print(df.describe())

df['tpep_pickup_datetime']  = pd.to_datetime(df['tpep_pickup_datetime'])
df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'])
df['trip_duration_min'] = (
    (df['tpep_dropoff_datetime'] - df['tpep_pickup_datetime'])
    .dt.total_seconds() / 60)
df['pickup_month']   = df['tpep_pickup_datetime'].dt.month
df['pickup_quarter'] = df['tpep_pickup_datetime'].dt.quarter
df['pickup_hour']    = df['tpep_pickup_datetime'].dt.hour
df['zero_distance']  = df['trip_distance'] == 0
df['invalid_time']   = df['trip_duration_min'] <= 0

df_clean = df[
    (df['trip_duration_min'] > 0) & (df['trip_duration_min'] < 180) &
    (df['trip_distance'] > 0)     & (df['trip_distance'] < 100) &
    (df['total_amount'] > 0)      & (df['total_amount'] < 300)
].copy()

# --- Plot 1: Box Plot – Trip Duration ---
sns.set_style('whitegrid')
PALETTE = '#F7C59F'
ACCENT  = '#2C3E50'

fig, ax = plt.subplots(figsize=(9, 5))
ax.boxplot(df_clean['trip_duration_min'], vert=False, patch_artist=True,
    boxprops=dict(facecolor=PALETTE, color=ACCENT),
    medianprops=dict(color='#E74C3C', linewidth=2),
    whiskerprops=dict(color=ACCENT), capprops=dict(color=ACCENT),
    flierprops=dict(marker='o', color=ACCENT, alpha=0.3, markersize=3))
ax.set_xlabel('Trip Duration (minutes)', fontsize=12)
ax.set_title('Distribution of Trip Durations – NYC TLC 2017',
             fontsize=14, fontweight='bold')
median_val = df_clean['trip_duration_min'].median()
ax.axvline(median_val, color='#E74C3C', linestyle='--', linewidth=1)
ax.text(median_val + 0.5, 1.05, f'Median: {median_val:.1f} min',
        color='#E74C3C', fontsize=10)
plt.tight_layout()
plt.savefig('plot_01_trip_duration_boxplot.png', dpi=150)
plt.show()

# --- Plot 2: Monthly Ride Volume ---
monthly = df.groupby('pickup_month').size().reset_index(name='trip_count')
month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
monthly['month_name'] = monthly['pickup_month'].apply(lambda x: month_labels[x - 1])

fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(monthly['month_name'], monthly['trip_count'],
              color=PALETTE, edgecolor=ACCENT, linewidth=0.8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x / 1000)}K'))
ax.set_title('Monthly Ride Volume – NYC Yellow Taxi 2017',
             fontsize=14, fontweight='bold')
for bar in bars:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 200,
            f'{h / 1000:.0f}K', ha='center', va='bottom', fontsize=9)
plt.tight_layout()
plt.savefig('plot_02_monthly_ride_volume.png', dpi=150)
plt.show()

# --- Plot 3: Quarterly Average Fare ---
quarterly = df_clean.groupby('pickup_quarter')['total_amount'].mean().reset_index()
quarterly.columns = ['Quarter', 'Avg_Total_Amount']

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(['Q1', 'Q2', 'Q3', 'Q4'], quarterly['Avg_Total_Amount'],
              color=[PALETTE] * 4, edgecolor=ACCENT, linewidth=0.8)
ax.set_ylim(0, quarterly['Avg_Total_Amount'].max() * 1.25)
ax.set_title('Quarterly Average Fare – NYC Yellow Taxi 2017',
             fontsize=14, fontweight='bold')
for bar, val in zip(bars, quarterly['Avg_Total_Amount']):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
            f'${val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig('plot_03_quarterly_avg_fare.png', dpi=150)
plt.show()

# --- Plot 4: Hourly Ride Volume ---
hourly = df.groupby('pickup_hour').size().reset_index(name='trip_count')

fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(hourly['pickup_hour'], hourly['trip_count'],
        color=ACCENT, linewidth=2.5, marker='o', markersize=6,
        markerfacecolor=PALETTE)
ax.fill_between(hourly['pickup_hour'], hourly['trip_count'],
                alpha=0.25, color=PALETTE)
ax.set_xticks(range(0, 24))
ax.set_xticklabels([f'{h}:00' for h in range(24)], rotation=45, ha='right')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x / 1000)}K'))
ax.set_title('Ride Volume by Hour of Day – NYC Yellow Taxi 2017',
             fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('plot_04_hourly_ride_volume.png', dpi=150)
plt.show()

# --- Outlier Analysis ---
Q1  = df['trip_duration_min'].quantile(0.25)
Q3  = df['trip_duration_min'].quantile(0.75)
IQR = Q3 - Q1
lower   = Q1 - 1.5 * IQR
upper   = Q3 + 1.5 * IQR
outliers = df[(df['trip_duration_min'] < lower) | (df['trip_duration_min'] > upper)]

print(f'IQR bounds: [{lower:.1f}, {upper:.1f}] min')
print(f'Outliers: {len(outliers):,} ({len(outliers) / len(df) * 100:.2f}%)')
print(df.nlargest(5, 'trip_duration_min')[
    ['tpep_pickup_datetime', 'trip_duration_min', 'trip_distance', 'total_amount']])
print(df.nlargest(5, 'total_amount')[
    ['tpep_pickup_datetime', 'trip_distance', 'total_amount', 'payment_type']])
