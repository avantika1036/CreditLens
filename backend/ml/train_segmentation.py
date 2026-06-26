# backend/ml/train_segmentation.py

import os
import pickle
import pandas as pd
import numpy as np
from sqlalchemy import text
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from db.database import get_engine

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "kmeans_model.pkl")

N_CLUSTERS = 5

FEATURE_COLS = [
    "credit_limit",
    "avg_utilization_ratio",
    "total_trans_amt",
    "total_trans_ct",
    "months_inactive_12_mon",
    "churn_risk_score"
]

SEGMENT_MAP = {
    0: "High Spender, Low Risk",
    1: "Dormant Customer",
    2: "Revolving Debt Risk",
    3: "Occasional Transactor",
    4: "Premium Low Utilization"
}


def assign_segment_labels(df, centers_df):
    """
    Heuristically reorder raw KMeans cluster IDs to consistent semantic labels
    based on cluster center characteristics so that segment names are stable
    across retrains.
    """
    order_scores = {}
    for cid, row in centers_df.iterrows():
        score = (
            row["credit_limit"]          * 0.3 +
            row["total_trans_amt"]       * 0.3 +
            (-row["avg_utilization_ratio"]) * 0.2 +
            (-row["churn_risk_score"])   * 0.2
        )
        order_scores[cid] = score

    sorted_clusters = sorted(order_scores, key=lambda k: -order_scores[k])
    remap = {old_id: new_id for new_id, old_id in enumerate(sorted_clusters)}

    df["segment_id"] = df["raw_cluster"].map(remap)
    df["segment_label"] = df["segment_id"].map(SEGMENT_MAP)
    return df


def load_data(engine):
    query = """
        SELECT customer_id, credit_limit, avg_utilization_ratio,
               total_trans_amt, total_trans_ct, months_inactive_12_mon,
               churn_risk_score
        FROM customers
        WHERE churn_risk_score IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    return df


def train(engine):
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("[Segmentation] Loading customer data with churn scores ...")
    df = load_data(engine)
    print(f"[Segmentation] Rows loaded: {len(df)}")

    if len(df) == 0:
        raise ValueError("No customers with churn_risk_score found. Run train_churn.py first.")

    X = df[FEATURE_COLS].copy().astype(np.float64)
    X = X.fillna(X.median(numeric_only=True))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X).astype(np.float64)

    print(f"[Segmentation] Training KMeans with {N_CLUSTERS} clusters ...")
    kmeans = KMeans(
    n_clusters=N_CLUSTERS,
    init="k-means++",
    n_init=20,
    max_iter=500,
    random_state=42
    )
    kmeans.fit(X_scaled)
    kmeans.cluster_centers_ = kmeans.cluster_centers_.astype(np.float64)
    df["raw_cluster"] = kmeans.labels_

    centers_raw = scaler.inverse_transform(kmeans.cluster_centers_)
    centers_df  = pd.DataFrame(centers_raw, columns=FEATURE_COLS)

    df = assign_segment_labels(df, centers_df)

    print("[Segmentation] Cluster distribution:")
    print(df.groupby(["segment_id", "segment_label"]).size().reset_index(name="count").to_string(index=False))

    print("[Segmentation] Writing segment_id and segment_label to DB ...")
    with engine.connect() as conn:
        for _, row in df[["customer_id", "segment_id", "segment_label"]].iterrows():
            conn.execute(
                text("""
                    UPDATE customers
                    SET segment_id = :sid, segment_label = :slabel
                    WHERE customer_id = :cid
                """),
                {
                    "sid":    int(row["segment_id"]),
                    "slabel": str(row["segment_label"]),
                    "cid":    int(row["customer_id"])
                }
            )
        conn.commit()
    print("[Segmentation] DB updated.")

    artifact = {"kmeans": kmeans, "scaler": scaler, "feature_cols": FEATURE_COLS, "segment_map": SEGMENT_MAP}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)
    print(f"[Segmentation] Model saved to {MODEL_PATH}")

    return kmeans, scaler


if __name__ == "__main__":
    engine = get_engine()
    train(engine)