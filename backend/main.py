# backend/main.py

import os
import pickle
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from db.database import get_engine, init_db
from reports.pdf_generator import generate_report

MODEL_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reports")

CHURN_MODEL_PATH  = os.path.join(MODEL_DIR, "churn_model.pkl")
KMEANS_MODEL_PATH = os.path.join(MODEL_DIR, "kmeans_model.pkl")

SEGMENT_MAP = {
    0: "High Spender, Low Risk",
    1: "Dormant Customer",
    2: "Revolving Debt Risk",
    3: "Occasional Transactor",
    4: "Premium Low Utilization"
}

RECOMMENDATIONS = {
    0: "Offer premium rewards upgrade to retain engagement.",
    1: "Send re-engagement campaign with cashback incentive.",
    2: "Provide debt counselling offer and lower APR option.",
    3: "Promote targeted spend categories to increase activity.",
    4: "Upsell credit limit increase or travel benefits."
}

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    state["engine"] = engine

    try:
        init_db()
        print("[Startup] DB schema verified.")
    except Exception as e:
        print(f"[Startup] DB init warning: {e}")

    if os.path.exists(CHURN_MODEL_PATH):
        with open(CHURN_MODEL_PATH, "rb") as f:
            churn_artifact = pickle.load(f)
        state["churn_model"]    = churn_artifact["model"]
        state["churn_encoders"] = churn_artifact["encoders"]
        state["churn_features"] = churn_artifact["feature_cols"]
        print("[Startup] Churn model loaded.")
    else:
        print(f"[Startup] WARNING: churn_model.pkl not found at {CHURN_MODEL_PATH}")
        state["churn_model"] = None

    if os.path.exists(KMEANS_MODEL_PATH):
        with open(KMEANS_MODEL_PATH, "rb") as f:
            kmeans_artifact = pickle.load(f)
        state["kmeans_model"]    = kmeans_artifact["kmeans"]
        state["kmeans_scaler"]   = kmeans_artifact["scaler"]
        state["kmeans_features"] = kmeans_artifact["feature_cols"]
        print("[Startup] KMeans model loaded.")
    else:
        print(f"[Startup] WARNING: kmeans_model.pkl not found at {KMEANS_MODEL_PATH}")
        state["kmeans_model"] = None

    yield
    state.clear()


app = FastAPI(
    title="CreditLens API",
    description="Credit Risk & Spending Behavior Analytics Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CustomerInput(BaseModel):
    age:                     float = Field(..., example=45)
    months_on_book:          float = Field(..., example=36)
    credit_limit:            float = Field(..., example=12000.0)
    avg_utilization_ratio:   float = Field(..., example=0.25)
    total_trans_amt:         float = Field(..., example=4500.0)
    total_trans_ct:          float = Field(..., example=60)
    months_inactive_12_mon:  float = Field(..., example=2)
    contacts_count_12_mon:   float = Field(..., example=3)
    gender:                  int   = Field(default=0, example=0)
    education:               int   = Field(default=0, example=1)
    marital_status:          int   = Field(default=0, example=1)
    income_category:         int   = Field(default=0, example=2)
    card_category:           int   = Field(default=0, example=0)


# ── Root & Health ────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {"status": "ok", "project": "CreditLens"}


@app.get("/health", tags=["Health"])
def health():
    engine = state.get("engine")
    db_ok  = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status":       "ok",
        "database":     "connected" if db_ok else "unreachable",
        "churn_model":  "loaded" if state.get("churn_model") is not None else "missing",
        "kmeans_model": "loaded" if state.get("kmeans_model") is not None else "missing",
    }


# ── Predictions ──────────────────────────────────────────────────────────────

@app.post("/predict/risk", tags=["Predictions"])
def predict_risk(customer: CustomerInput):
    churn_model   = state.get("churn_model")
    kmeans_model  = state.get("kmeans_model")
    kmeans_scaler = state.get("kmeans_scaler")

    if churn_model is None:
        raise HTTPException(status_code=503, detail="Churn model not loaded.")
    if kmeans_model is None:
        raise HTTPException(status_code=503, detail="KMeans model not loaded.")

    churn_feature_cols = state.get("churn_features", [])
    input_map = {
        "age":                    customer.age,
        "months_on_book":         customer.months_on_book,
        "credit_limit":           customer.credit_limit,
        "avg_utilization_ratio":  customer.avg_utilization_ratio,
        "total_trans_amt":        customer.total_trans_amt,
        "total_trans_ct":         customer.total_trans_ct,
        "months_inactive_12_mon": customer.months_inactive_12_mon,
        "contacts_count_12_mon":  customer.contacts_count_12_mon,
        "gender":                 float(customer.gender),
        "education":              float(customer.education),
        "marital_status":         float(customer.marital_status),
        "income_category":        float(customer.income_category),
        "card_category":          float(customer.card_category),
    }

    churn_vec = np.array(
        [input_map.get(f, 0.0) for f in churn_feature_cols],
        dtype=np.float32
    ).reshape(1, -1)

    churn_prob = float(churn_model.predict_proba(churn_vec)[0][1])

    if churn_prob >= 0.70:
        risk_level = "HIGH"
    elif churn_prob >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    kmeans_feature_cols = state.get("kmeans_features", [])
    kmeans_input_map = {
        "credit_limit":           customer.credit_limit,
        "avg_utilization_ratio":  customer.avg_utilization_ratio,
        "total_trans_amt":        customer.total_trans_amt,
        "total_trans_ct":         customer.total_trans_ct,
        "months_inactive_12_mon": customer.months_inactive_12_mon,
        "churn_risk_score":       churn_prob,
    }

    kmeans_vec = np.array(
        [kmeans_input_map.get(f, 0.0) for f in kmeans_feature_cols],
        dtype=np.float32
    ).reshape(1, -1)

    kmeans_vec_scaled = kmeans_scaler.transform(kmeans_vec)
    segment_id        = int(kmeans_model.predict(kmeans_vec_scaled)[0])
    segment_label     = SEGMENT_MAP.get(segment_id, "Unknown")
    recommendation    = RECOMMENDATIONS.get(segment_id, "Monitor account activity.")

    return {
        "churn_risk_score": round(churn_prob, 4),
        "risk_level":       risk_level,
        "segment_id":       segment_id,
        "segment_label":    segment_label,
        "recommendation":   recommendation,
    }


# ── Legacy Stats (kept for backward compat) ──────────────────────────────────

@app.get("/stats/summary", tags=["Stats"])
def stats_summary():
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*)                                                    AS total_customers,
                    SUM(CASE WHEN churn_risk_score > 0.7 THEN 1 ELSE 0 END)   AS high_risk_count,
                    ROUND(AVG(churn_risk_score)::numeric, 4)                   AS avg_churn_score,
                    SUM(CASE WHEN is_churned THEN 1 ELSE 0 END)                AS churned_count
                FROM customers
            """)).fetchone()

            fraud_row = conn.execute(text(
                "SELECT COUNT(*) FROM transactions WHERE fraud_flag = TRUE"
            )).fetchone()

            seg_rows = conn.execute(text("""
                SELECT segment_label, COUNT(*) AS cnt
                FROM customers
                WHERE segment_label IS NOT NULL
                GROUP BY segment_label
                ORDER BY cnt DESC
            """)).fetchall()

        return {
            "total_customers": int(row[0]) if row[0] else 0,
            "high_risk_count": int(row[1]) if row[1] else 0,
            "avg_churn_score": float(row[2]) if row[2] else 0.0,
            "churned_count":   int(row[3]) if row[3] else 0,
            "fraud_count":     int(fraud_row[0]) if fraud_row[0] else 0,
            "segments":        [{"label": r[0], "count": int(r[1])} for r in seg_rows],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/shap", tags=["Stats"])
def stats_shap(limit: int = 10):
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT feature_name, ROUND(AVG(ABS(shap_value))::numeric, 6) AS mean_abs_shap
                FROM shap_features
                GROUP BY feature_name
                ORDER BY mean_abs_shap DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
        return {"shap_importance": [{"feature": r[0], "mean_abs_shap": float(r[1])} for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/fraud", tags=["Stats"])
def stats_fraud(limit: int = 100):
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT txn_id, amount, time_hours, v1, v2, v3, v4,
                       fraud_flag, anomaly_score
                FROM transactions
                ORDER BY anomaly_score DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
        keys = ["txn_id", "amount", "time_hours", "v1", "v2", "v3", "v4",
                "fraud_flag", "anomaly_score"]
        return {"transactions": [dict(zip(keys, r)) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── New Endpoints ─────────────────────────────────────────────────────────────

@app.get("/stats/overview", tags=["Stats"])
def stats_overview():
    """
    Returns a high-level KPI summary:
    total_customers, avg_churn_risk, high_risk_count,
    actual_churned, fraud_flagged_transactions.
    """
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            cust_row = conn.execute(text("""
                SELECT
                    COUNT(*)                                                      AS total_customers,
                    ROUND(AVG(churn_risk_score)::numeric, 4)                     AS avg_churn_risk,
                    SUM(CASE WHEN churn_risk_score > 0.7  THEN 1 ELSE 0 END)     AS high_risk_count,
                    SUM(CASE WHEN is_churned = TRUE       THEN 1 ELSE 0 END)     AS actual_churned
                FROM customers
            """)).fetchone()

            fraud_row = conn.execute(text("""
                SELECT COUNT(*) FROM transactions WHERE fraud_flag = TRUE
            """)).fetchone()

        return {
            "total_customers":             int(cust_row[0])   if cust_row[0]   else 0,
            "avg_churn_risk":              float(cust_row[1]) if cust_row[1]   else 0.0,
            "high_risk_count":             int(cust_row[2])   if cust_row[2]   else 0,
            "actual_churned":              int(cust_row[3])   if cust_row[3]   else 0,
            "fraud_flagged_transactions":  int(fraud_row[0])  if fraud_row[0]  else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/segments", tags=["Stats"])
def stats_segments():
    """
    Returns per-segment breakdown:
    segment_label, count, avg_churn_risk, avg_credit_limit.
    """
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    segment_label,
                    COUNT(*)                                        AS count,
                    ROUND(AVG(churn_risk_score)::numeric, 4)       AS avg_risk,
                    ROUND(AVG(credit_limit)::numeric, 2)           AS avg_credit_limit
                FROM customers
                WHERE segment_label IS NOT NULL
                GROUP BY segment_label
                ORDER BY avg_risk DESC
            """)).fetchall()

        return {
            "segments": [
                {
                    "segment":          r[0],
                    "count":            int(r[1]),
                    "avg_risk":         float(r[2]) if r[2] else 0.0,
                    "avg_credit_limit": float(r[3]) if r[3] else 0.0,
                }
                for r in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/top-risk", tags=["Stats"])
def stats_top_risk(limit: int = Query(default=20, ge=1, le=500)):
    """
    Returns top N customers sorted by churn_risk_score descending.
    Includes customer_id, age, segment_label, credit_limit,
    total_trans_amt, churn_risk_score, is_churned.
    """
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT
                    customer_id,
                    age,
                    segment_label,
                    credit_limit,
                    total_trans_amt,
                    avg_utilization_ratio,
                    churn_risk_score,
                    is_churned
                FROM customers
                WHERE churn_risk_score IS NOT NULL
                ORDER BY churn_risk_score DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()

        keys = [
            "customer_id", "age", "segment_label", "credit_limit",
            "total_trans_amt", "avg_utilization_ratio",
            "churn_risk_score", "is_churned"
        ]
        customers = []
        for r in rows:
            rec = dict(zip(keys, r))
            rec["churn_risk_score"]      = float(rec["churn_risk_score"]) if rec["churn_risk_score"] else 0.0
            rec["credit_limit"]          = float(rec["credit_limit"])     if rec["credit_limit"]     else 0.0
            rec["total_trans_amt"]       = float(rec["total_trans_amt"])  if rec["total_trans_amt"]  else 0.0
            rec["avg_utilization_ratio"] = float(rec["avg_utilization_ratio"]) if rec["avg_utilization_ratio"] else 0.0
            rec["risk_level"] = (
                "HIGH"   if rec["churn_risk_score"] >= 0.70 else
                "MEDIUM" if rec["churn_risk_score"] >= 0.40 else
                "LOW"
            )
            customers.append(rec)

        return {"limit": limit, "customers": customers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shap/{customer_id}", tags=["SHAP"])
def shap_by_customer(customer_id: int, limit: int = Query(default=10, ge=1, le=50)):
    """
    Returns top SHAP features for a given customer_id,
    sorted by absolute SHAP value descending.
    """
    engine = state.get("engine")
    try:
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT 1 FROM customers WHERE customer_id = :cid"
            ), {"cid": customer_id}).fetchone()

            if not exists:
                raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found.")

            rows = conn.execute(text("""
                SELECT feature_name, shap_value
                FROM shap_features
                WHERE customer_id = :cid
                ORDER BY ABS(shap_value) DESC
                LIMIT :limit
            """), {"cid": customer_id, "limit": limit}).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No SHAP values found for customer {customer_id}. Run shap_explainer.py first."
            )

        features = [
            {
                "feature":    r[0],
                "shap_value": round(float(r[1]), 6),
                "direction":  "increases_churn_risk" if r[1] > 0 else "decreases_churn_risk"
            }
            for r in rows
        ]

        churn_score = None
        with engine.connect() as conn:
            score_row = conn.execute(text(
                "SELECT churn_risk_score, segment_label FROM customers WHERE customer_id = :cid"
            ), {"cid": customer_id}).fetchone()
            if score_row:
                churn_score    = float(score_row[0]) if score_row[0] else None
                segment_label  = score_row[1]

        return {
            "customer_id":      customer_id,
            "churn_risk_score": churn_score,
            "segment_label":    segment_label,
            "top_features":     features,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Reports ───────────────────────────────────────────────────────────────────

@app.post("/reports/generate", tags=["Reports"])
def generate_pdf_report(report_month: str = None):
    try:
        filename = generate_report(report_month=report_month)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/download/{filename}", tags=["Reports"])
def download_report(filename: str):
    filepath = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report file not found.")
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=filename
    )