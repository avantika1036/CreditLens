# backend/ml/shap_explainer.py

import os
import pickle
import pandas as pd
import numpy as np
import shap
from sqlalchemy import text
from db.database import get_engine

MODEL_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
CHURN_PATH = os.path.join(MODEL_DIR, "churn_model.pkl")
SUBSET_LIMIT = 500


def load_customers(engine, limit=SUBSET_LIMIT):
    query = f"""
        SELECT customer_id, age, months_on_book, credit_limit, avg_utilization_ratio,
               total_trans_amt, total_trans_ct, months_inactive_12_mon,
               contacts_count_12_mon, gender, education, marital_status,
               income_category, card_category, is_churned
        FROM customers
        WHERE churn_risk_score IS NOT NULL
        ORDER BY customer_id
        LIMIT {limit}
    """
    df = pd.read_sql(query, engine)
    return df


def encode_with_saved_encoders(df, encoders, categorical_cols):
    for col in categorical_cols:
        if col not in df.columns:
            continue
        le = encoders.get(col)
        if le is None:
            continue
        df[col] = df[col].astype(str).fillna("Unknown")
        known_classes = set(le.classes_)
        df[col] = df[col].apply(lambda x: x if x in known_classes else le.classes_[0])
        df[col] = le.transform(df[col])
    return df


def compute_and_store_shap(engine):
    if not os.path.exists(CHURN_PATH):
        raise FileNotFoundError(f"Churn model not found at {CHURN_PATH}. Run train_churn.py first.")

    print("[SHAP] Loading churn model ...")
    with open(CHURN_PATH, "rb") as f:
        artifact = pickle.load(f)

    model        = artifact["model"]
    encoders     = artifact["encoders"]
    feature_cols = artifact["feature_cols"]

    categorical_cols = list(encoders.keys())

    print(f"[SHAP] Loading {SUBSET_LIMIT} customers from DB ...")
    df = load_customers(engine, limit=SUBSET_LIMIT)
    print(f"[SHAP] Rows loaded: {len(df)}")

    customer_ids = df["customer_id"].values

    df = encode_with_saved_encoders(df, encoders, categorical_cols)

    available = [f for f in feature_cols if f in df.columns]
    X = df[available].copy()
    X = X.fillna(X.median(numeric_only=True))

    print("[SHAP] Computing SHAP values via TreeExplainer ...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    if isinstance(shap_values, list):
        shap_matrix = shap_values[1]
    else:
        shap_matrix = shap_values

    shap_df = pd.DataFrame(shap_matrix, columns=available)
    shap_df["customer_id"] = customer_ids

    records = []
    for _, row in shap_df.iterrows():
        cid = int(row["customer_id"])
        for feat in available:
            records.append({
                "customer_id":  cid,
                "feature_name": feat,
                "shap_value":   float(row[feat])
            })

    print(f"[SHAP] Total SHAP records to insert: {len(records)}")

    print("[SHAP] Clearing existing shap_features rows for these customers ...")
    cid_list = [int(c) for c in customer_ids]
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM shap_features WHERE customer_id = ANY(:cids)"),
            {"cids": cid_list}
        )
        conn.commit()

    print("[SHAP] Inserting SHAP values into DB ...")
    records_df = pd.DataFrame(records)
    records_df.to_sql(
        "shap_features",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000
    )
    print("[SHAP] Done. SHAP values stored in 'shap_features'.")

    top_features = shap_df[available].abs().mean().sort_values(ascending=False)
    print("\n[SHAP] Mean |SHAP| per feature (global importance):")
    print(top_features.to_string())

    return shap_df


if __name__ == "__main__":
    engine = get_engine()
    compute_and_store_shap(engine)
    