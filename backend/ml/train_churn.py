# backend/ml/train_churn.py

import os
import pickle
import pandas as pd
import numpy as np
from sqlalchemy import text
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from xgboost import XGBClassifier
from db.database import get_engine

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "churn_model.pkl")

CATEGORICAL_COLS = [
    "gender", "education", "marital_status", "income_category", "card_category"
]

FEATURE_COLS = [
    "age", "months_on_book", "credit_limit", "avg_utilization_ratio",
    "total_trans_amt", "total_trans_ct", "months_inactive_12_mon",
    "contacts_count_12_mon", "gender", "education", "marital_status",
    "income_category", "card_category"
]

TARGET_COL = "is_churned"


def load_data(engine):
    query = """
        SELECT customer_id, age, months_on_book, credit_limit, avg_utilization_ratio,
               total_trans_amt, total_trans_ct, months_inactive_12_mon,
               contacts_count_12_mon, gender, education, marital_status,
               income_category, card_category, is_churned
        FROM customers
    """
    df = pd.read_sql(query, engine)
    return df


def encode_categoricals(df):
    encoders = {}
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = df[col].astype(str).fillna("Unknown")
            df[col] = le.fit_transform(df[col])
            encoders[col] = le
    return df, encoders


def compute_scale_pos_weight(y):
    neg = (y == 0).sum()
    pos = (y == 1).sum()
    if pos == 0:
        return 1.0
    return float(neg) / float(pos)


def train(engine):
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("[Churn] Loading customer data ...")
    df = load_data(engine)
    print(f"[Churn] Rows loaded: {len(df)}")

    df[TARGET_COL] = df[TARGET_COL].astype(int)

    df, encoders = encode_categoricals(df)

    available_features = [f for f in FEATURE_COLS if f in df.columns]
    X = df[available_features].copy()
    y = df[TARGET_COL].copy()

    X = X.fillna(X.median(numeric_only=True))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    spw = compute_scale_pos_weight(y_train)
    print(f"[Churn] scale_pos_weight = {spw:.2f}")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=spw,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred  = model.predict(X_test)

    auc = roc_auc_score(y_test, y_proba)
    print(f"[Churn] ROC-AUC: {auc:.4f}")
    print("[Churn] Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["Retained", "Churned"]))

    print("[Churn] Scoring all customers ...")
    X_all = df[available_features].copy().fillna(df[available_features].median(numeric_only=True))
    all_scores = model.predict_proba(X_all)[:, 1]
    df["churn_risk_score"] = all_scores

    print("[Churn] Writing churn_risk_score to DB ...")
    with engine.connect() as conn:
        for _, row in df[["customer_id", "churn_risk_score"]].iterrows():
            conn.execute(
                text("UPDATE customers SET churn_risk_score = :score WHERE customer_id = :cid"),
                {"score": float(row["churn_risk_score"]), "cid": int(row["customer_id"])}
            )
        conn.commit()
    print("[Churn] DB updated.")

    artifact = {"model": model, "encoders": encoders, "feature_cols": available_features}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"[Churn] Model saved to {MODEL_PATH}")

    return model, encoders


if __name__ == "__main__":
    engine = get_engine()
    train(engine)