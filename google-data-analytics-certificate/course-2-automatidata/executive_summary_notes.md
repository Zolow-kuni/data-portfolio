# Executive Summary – Course 2 Automatidata Project

**To:** Luana Rodriguez & Udo Bankole, Automatidata  
**From:** Subham Joshi  
**Re:** NYC TLC Yellow Taxi 2017 – EDA Results

---

## Project Background

EDA on 408,294 taxi trips from 2017 across 18 variables.

---

## Dataset Snapshot

| Metric | Value |
|--------|-------|
| Total trips | 408,294 |
| Median trip duration | ~11–13 minutes |
| Median trip distance | ~1.6 miles |
| Median total fare | ~$12–15 |
| Dominant payment | Credit card (~67%) |
| Peak hour | 6–8 PM weekdays |

---

## EDA Results Summary

- IQR: ~5–20 min; outliers extend to several hours
- Stable monthly volume; February dip noted
- Q3/Q4 marginally higher average fares
- Peak demand: 8–9 AM and 6–8 PM weekdays
- ~0.5% zero-distance, non-zero-fare trips flagged

---

## Outlier Strategy

Retain all raw records. Apply IQR filtering only to modelling subsets.
Zero-distance trips tagged separately — report to TLC.

---

## Tableau Visualisation

Scatter plot: Total Amount vs Trip Distance.
Calculated field flags trip_distance = 0 (orange).
Majority cluster along positive linear trend.

---

## Recommendations

1. Report zero-distance billing anomalies to TLC
2. Use IQR filtering for all modelling datasets
3. Align fleet deployment with peak demand hours
4. Investigate Q3/Q4 fare elevation by rate code

---

## Next Steps

- Phase 3: Statistical modelling on cleaned dataset
- Zone-level analysis using PULocationID/DOLocationID
- Vendor-level data quality comparison (VendorID 1 vs 2)
