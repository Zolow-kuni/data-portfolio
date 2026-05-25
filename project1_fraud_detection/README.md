# Project 1 — Fraud & Anomaly Detection System

## What it does

Scans a transaction dataset for suspicious activity using three complementary techniques:

| Method | Logic |
|--------|-------|
| **Z-score** | Flags transactions > 2.5 standard deviations from the mean amount |
| **IQR** | Flags amounts in the top 1% of the distribution |
| **Rule-based scoring** | Assigns a 0–100 risk score based on amount, frequency, transaction type, and time of day |

A transaction is flagged if **any** method triggers. Results are validated against a ground-truth `is_fraud` label and precision/recall are printed.

## Real-world problem

Fraud analysts at payment processors and banks use exactly these layered approaches. Rule engines catch known patterns (e.g., late-night international transactions); statistical methods catch emerging anomalies.

## How to run

```bash
# From the data-portfolio/ root (recommended)
cd project1_fraud_detection
python fraud_detection.py
```

- If `data/project1/creditcard.csv` exists (Kaggle), it loads that.
- Otherwise, it auto-generates `data/transactions.csv` via `generate_data.py`.

To generate synthetic data only:

```bash
python generate_data.py
```

## Outputs (`outputs/` folder)

| File | Description |
|------|-------------|
| `flagged_transactions.csv` | All flagged rows sorted by risk score |
| `risk_score_histogram.png` | Distribution of risk scores with thresholds marked |
| `flagged_vs_normal.png` | Bar chart — flagged vs normal transaction counts |
| `amount_vs_frequency.png` | Scatter: amount vs frequency, coloured by risk score |

## Kaggle dataset

```bash
kaggle datasets download -d mlg-ulb/creditcardfraud -p ../data/project1 --unzip
```

Expected file: `data/project1/creditcard.csv`
Columns used: `Time`, `Amount`, `Class` (fraud label), `V1–V28` (PCA features)
