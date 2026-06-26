# backend/ml/train_fraud.py

import os
import pickle
import pandas as pd
import numpy as np
from sqlalchemy import text
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report
from db.database import get_engine

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_model.pkl")

FEATURE_COLS = ["amount", "v1", "v2", "v3", "v4"]
CONTAMINATION = 0.002


def load_data(engine):
    query = """
        SELECT txn_id, amount, time_hours, v1, v2, v3, v4, fraud_flag
        FROM transactions
    """
    df = pd.read_sql(query, engine)
    return df


def train(engine):
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("[Fraud] Loading transaction data ...")
    df = load_data(engine)
    print(f"[Fraud] Rows loaded: {len(df)}")
    print(f"[Fraud] Known fraud count: {df['fraud_flag'].sum()}")

    X = df[FEATURE_COLS].copy()
    X = X.fillna(X.median(numeric_only=True))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"[Fraud] Training IsolationForest (contamination={CONTAMINATION}) ...")
    iso = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        max_samples="auto",
        max_features=1.0,
        bootstrap=False,
        random_state=42,
        n_jobs=-1
    )
    iso.fit(X_scaled)

    anomaly_raw    = iso.predict(X_scaled)
    anomaly_scores = iso.decision_function(X_scaled)

    anomaly_score_normalized = -anomaly_scores
    anomaly_score_normalized = (
        (anomaly_score_normalized - anomaly_score_normalized.min()) /
        (anomaly_score_normalized.max() - anomaly_score_normalized.min() + 1e-9)
    )

    df["anomaly_score"]    = anomaly_score_normalized
    df["predicted_fraud"]  = (anomaly_raw == -1).astype(int)

    print("[Fraud] Classification Report (IsolationForest vs ground-truth fraud_flag):")
    print(classification_report(
        df["fraud_flag"].astype(int),
        df["predicted_fraud"],
        target_names=["Legit", "Fraud"],
        zero_division=0
    ))

    fraud_detected   = df[df["predicted_fraud"] == 1]
    actual_fraud     = df[df["fraud_flag"] == True]
    overlap          = df[(df["predicted_fraud"] == 1) & (df["fraud_flag"] == True)]
    print(f"[Fraud] Predicted anomalies : {len(fraud_detected)}")
    print(f"[Fraud] Actual fraud rows   : {len(actual_fraud)}")
    print(f"[Fraud] Overlap (TP)        : {len(overlap)}")

    print("[Fraud] Writing anomaly_score to DB ...")
    with engine.connect() as conn:
        for _, row in df[["txn_id", "anomaly_score"]].iterrows():
            conn.execute(
                text("UPDATE transactions SET anomaly_score = :score WHERE txn_id = :tid"),
                {"score": float(row["anomaly_score"]), "tid": int(row["txn_id"])}
            )
        conn.commit()
    print("[Fraud] DB updated.")

    artifact = {
        "iso_model":    iso,
        "scaler":       scaler,
        "feature_cols": FEATURE_COLS,
        "contamination": CONTAMINATION
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"[Fraud] Model saved to {MODEL_PATH}")

    return iso, scaler


if __name__ == "__main__":
    engine = get_engine()
    train(engine)