# PACE Strategy Notes – Course 2 Automatidata Project

## Plan Stage

**Relevant Variables:** tpep_pickup_datetime, tpep_dropoff_datetime,
trip_distance (miles), total_amount ($), fare_amount ($),
passenger_count, payment_type, vendor_id.

**Units:** Distance in miles. Monetary fields in USD.
Datetime in YYYY-MM-DD HH:MM:SS.

**Initial Presumptions:**
- Most trips will be short (<10 miles, <30 min) — urban taxi patterns
- Credit card will be dominant payment type
- Ride volume will peak during commute hours
- Outliers expected from airport transfers and data entry errors

**Missing/Incomplete Data:** Zero-distance trips (~0.5%),
negative durations, cash tip_amount not recorded by design.

**EDA Practices Required:** Shape inspection, null checks,
descriptive stats, datetime feature engineering,
IQR outlier detection, visualisations.

---

## Analyze Stage

**EDA Steps:** Load → parse datetimes → engineer features
(trip_duration_min, pickup_month, pickup_hour) → describe
→ detect outliers → visualise.

**Structuring Needed:** Filter invalid records for plots.
Group by month, quarter, hour for aggregations.
No joins needed for this phase.

**Visualisation Assumptions:** Box plots for technical audience.
Bar charts for management. High-contrast colours for accessibility.

---

## Construct Stage

**Visualisations Built:**
1. Box plot – trip_duration_min
2. Bar chart – monthly ride volume
3. Bar chart – quarterly average total_amount
4. Line chart – hourly ride volume
5. Tableau scatter plot – total_amount vs trip_distance

**Outlier Plan:** Retain raw data. Apply IQR filtering only to
modelling subsets. Document all exclusions.

---

## Execute Stage

**Key Insights:**
- Median trip duration ~11–13 min; IQR 5–20 min
- Peak demand: 6–9 AM and 5–8 PM weekdays
- February dip in monthly volume
- ~0.5% zero-distance, non-zero-fare trips flagged as anomalies
- Q3/Q4 marginally higher average fares

**Recommendations:**
1. Investigate zero-distance billing anomalies — report to TLC
2. Use IQR filtering for future modelling datasets
3. Align fleet deployment with peak hour demand windows
4. Research seasonal and rate code fare patterns in later phases

**Follow-on Research Questions:**
- Do outlier trips cluster by pickup zone (PULocationID)?
- Is there a vendor_id correlation with data quality issues?
- How does tip_amount vary by payment type and time of day?
