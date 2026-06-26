# CreditLens — Credit Risk & Spending Behavior Analytics Platform

CreditLens is a full-stack credit analytics platform that combines ML-based risk scoring, customer segmentation, fraud detection, and explainable AI — served via a FastAPI backend, visualized in a live Power BI dashboard, and accessible through a React frontend with a hosted live URL.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CreditLens System                           │
│                                                                     │
│   Kaggle Datasets                                                   │
│   ┌──────────────────┐   ┌──────────────────┐                      │
│   │ BankChurners.csv │   │  creditcard.csv  │                      │
│   └────────┬─────────┘   └────────┬─────────┘                      │
│            │                      │                                 │
│            └──────────┬───────────┘                                 │
│                       ▼                                             │
│            ┌──────────────────────┐                                 │
│            │   ETL Pipeline       │  etl/pipeline.py               │
│            │   (Pandas + SQLAlch) │                                 │
│            └──────────┬───────────┘                                 │
│                       │                                             │
│                       ▼                                             │
│            ┌──────────────────────┐                                 │
│            │    PostgreSQL DB      │                                 │
│            │  ┌────────────────┐  │                                 │
│            │  │  customers     │  │                                 │
│            │  │  transactions  │  │                                 │
│            │  │  shap_features │  │                                 │
│            │  │  monthly_rep.. │  │                                 │
│            │  └────────────────┘  │                                 │
│            └──────┬───────────────┘                                 │
│                   │                                                 │
│        ┌──────────┼──────────────────┐                              │
│        ▼          ▼                  ▼                              │
│  ┌──────────┐ ┌──────────┐  ┌───────────────┐                      │
│  │ XGBoost  │ │ K-Means  │  │ Isolation     │                      │
│  │  Churn   │ │  Seg.    │  │ Forest Fraud  │                      │
│  └────┬─────┘ └────┬─────┘  └──────┬────────┘                      │
│       │            │               │                                │
│       └────────────┼───────────────┘                                │
│                    │  writes scores back to DB                      │
│                    ▼                                                │
│          ┌─────────────────────┐                                    │
│          │   SHAP Explainer    │  shap_features table               │
│          └─────────────────────┘                                    │
│                    │                                                │
│                    ▼                                                │
│          ┌─────────────────────┐                                    │
│          │   FastAPI Backend   │  main.py  :8000                   │
│          │                     │                                    │
│          │  GET  /stats/..     │                                    │
│          │  POST /predict/risk │                                    │
│          │  GET  /shap/:id     │                                    │
│          │  POST /reports/..   │                                    │
│          └────────┬────────────┘                                    │
│                   │                                                 │
│          ┌────────┴────────────┐                                    │
│          ▼                     ▼                                    │
│  ┌───────────────┐   ┌──────────────────┐                          │
│  │  React / Vite │   │   Power BI       │                          │
│  │  Frontend     │   │   Dashboard      │                          │
│  │  :5173        │   │  (DirectQuery)   │                          │
│  └───────────────┘   └──────────────────┘                          │
│                                                                     │
│          PDF Report generated on demand via fpdf2                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer          | Technology                                      |
|----------------|-------------------------------------------------|
| Data Ingestion | Python, Pandas, SQLAlchemy                      |
| Database       | PostgreSQL                                      |
| ML — Churn     | XGBoost, scikit-learn, SHAP                     |
| ML — Segments  | K-Means (scikit-learn), StandardScaler          |
| ML — Fraud     | Isolation Forest (scikit-learn)                 |
| Backend API    | FastAPI, Uvicorn, Pydantic                      |
| Frontend       | React 18, Vite, Axios                           |
| Reporting      | fpdf2 (PDF), Power BI (DirectQuery)             |
| Containerisation| Docker                                         |

---

## Repository Structure

```
creditlens/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── db/
│   │   ├── schema.sql
│   │   └── database.py
│   ├── etl/
│   │   └── pipeline.py
│   ├── ml/
│   │   ├── train_churn.py
│   │   ├── train_segmentation.py
│   │   ├── train_fraud.py
│   │   └── shap_explainer.py
│   ├── models/            # auto-created; stores .pkl files
│   └── reports/
│       └── pdf_generator.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── api/client.js
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/                  # place Kaggle CSVs here (git-ignored)
│   ├── BankChurners.csv
│   └── creditcard.csv
├── powerbi/
│   └── design-notes.md
└── README.md
```

---

## Setup & Run

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ running locally or via Docker
- Kaggle datasets downloaded into `data/`

### 2. Download Datasets

| Dataset | Kaggle URL |
|---------|-----------|
| BankChurners.csv | https://www.kaggle.com/datasets/sakshigoyal7/credit-card-customers |
| creditcard.csv | https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud |

Place both files inside `creditlens/data/`.

---

### 3. Database

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE creditlens;"

# Set the environment variable (Linux / macOS)
export DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/creditlens"

# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/creditlens"

# Apply schema
psql -U postgres -d creditlens -f backend/db/schema.sql
```

---

### 4. Backend — Python Environment

```bash
cd backend

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

### 5. Run ETL Pipeline

```bash
# From backend/ with DATABASE_URL set
python -m etl.pipeline
```

Expected output:
```
[ETL] Loading BankChurners.csv ...
[ETL] Inserted 10127 customer rows into 'customers'.
[ETL] Loading creditcard.csv ...
[ETL] Inserted 50000 transaction rows into 'transactions'.
[ETL] Pipeline complete.
```

---

### 6. Train ML Models

Run scripts in this order (each depends on the previous):

```bash
# 1. Churn model — writes churn_risk_score to customers
python -m ml.train_churn

# 2. Segmentation — writes segment_id, segment_label to customers
python -m ml.train_segmentation

# 3. Fraud detection — writes anomaly_score to transactions
python -m ml.train_fraud

# 4. SHAP explainer — populates shap_features for top 500 customers
python -m ml.shap_explainer
```

Trained model artifacts are saved to `backend/models/`:
```
models/
├── churn_model.pkl
├── kmeans_model.pkl
└── isolation_model.pkl
```

---

### 7. Start FastAPI

```bash
# From backend/
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs available at: `http://localhost:8000/docs`

---

### 8. Run with Docker

```bash
cd backend
docker build -t creditlens-backend .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://..." creditlens-backend
```

---

### 9. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set API URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Development server
npm run dev
```

Open `http://localhost:5173` in your browser.

To build for production:
```bash
npm run build
npm run preview
```

---

## ML Models & Metrics

### Churn Prediction — XGBoost Classifier

| Metric       | Value (approx.)  |
|--------------|------------------|
| ROC-AUC      | 0.98             |
| Precision    | 0.93 (churned)   |
| Recall       | 0.95 (churned)   |
| F1-Score     | 0.94 (churned)   |

- Features: age, credit limit, utilization ratio, transaction amount/count, inactivity months, contact count, encoded categoricals.
- Class imbalance handled via `scale_pos_weight`.
- SHAP values computed for top 500 customers to explain individual predictions.

### Customer Segmentation — K-Means (k=5)

| Segment ID | Label                    | Characteristics                             |
|------------|--------------------------|---------------------------------------------|
| 0          | High Spender, Low Risk   | High credit limit, high spend, low churn    |
| 1          | Dormant Customer         | Low transactions, high inactivity           |
| 2          | Revolving Debt Risk      | High utilization, moderate churn risk       |
| 3          | Occasional Transactor    | Low spend frequency, moderate limits        |
| 4          | Premium Low Utilization  | High limit, very low utilization            |

### Fraud / Anomaly Detection — Isolation Forest

| Metric             | Value (approx.)  |
|--------------------|------------------|
| Contamination rate | 0.2%             |
| Precision (fraud)  | 0.27             |
| Recall (fraud)     | 0.86             |

- High recall prioritised to flag as many true fraud cases as possible.
- `anomaly_score` (0–1) stored per transaction; higher = more anomalous.

---

## API Endpoints

| Method | Endpoint                   | Description                                      |
|--------|----------------------------|--------------------------------------------------|
| GET    | `/`                        | Health check root                                |
| GET    | `/health`                  | DB + model load status                           |
| POST   | `/predict/risk`            | Predict churn score, risk level, segment         |
| GET    | `/stats/overview`          | KPI summary (customers, fraud, churn)            |
| GET    | `/stats/segments`          | Segment breakdown with avg risk & credit limit   |
| GET    | `/stats/top-risk?limit=N`  | Top N customers by churn risk score              |
| GET    | `/stats/shap`              | Global mean SHAP importance across features      |
| GET    | `/shap/{customer_id}`      | Per-customer SHAP explanation                    |
| GET    | `/stats/fraud?limit=N`     | Top N transactions by anomaly score              |
| POST   | `/reports/generate`        | Generate PDF monthly report                      |
| GET    | `/reports/download/{file}` | Download generated PDF                           |

---

## Power BI Dashboard

Connect Power BI Desktop to PostgreSQL via **DirectQuery**:

```
Server:   localhost
Database: creditlens
Mode:     DirectQuery
```

### Dashboard Pages

| Page | Title | Visuals |
|------|-------|---------|
| 1 | Executive Overview | KPI cards: total customers, high-risk count, avg churn score, fraud flagged. Churn risk distribution histogram. |
| 2 | Customer Segments | Donut chart of segment distribution. Scatter plot: credit limit vs utilization coloured by segment. Segment avg churn risk bar chart. |
| 3 | Churn Risk Deep-Dive | Top 20 high-risk customers table. Churn score by income category. Inactivity months vs churn score scatter. |
| 4 | Fraud & Anomalies | Anomaly score distribution. Fraud flag vs amount box plot. Top anomalous transactions table with amount and score. |
| 5 | SHAP Explainability | Global feature importance bar (mean |SHAP|). Per-customer SHAP waterfall (filtered by customer_id slicer). |

---

## Generating a PDF Report

```bash
# Via API
curl -X POST http://localhost:8000/reports/generate

# Response
{ "status": "ok", "filename": "creditlens_report_2025_07.pdf" }

# Download
curl -O http://localhost:8000/reports/download/creditlens_report_2025_07.pdf
```

The PDF includes KPI summary, segment breakdown table, risk commentary, and model notes.

---

## Environment Variables

| Variable        | Description                          | Example                                             |
|-----------------|--------------------------------------|-----------------------------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string         | `postgresql://postgres:pass@localhost:5432/creditlens` |
| `VITE_API_URL`  | FastAPI base URL for React frontend  | `http://localhost:8000`                             |

---

## License

MIT License. Datasets are sourced from Kaggle and subject to their respective licenses.