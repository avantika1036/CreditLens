# backend/etl/pipeline.py

import os
import pandas as pd
from sqlalchemy import text
from db.database import get_engine

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
CHURN_CSV = os.path.join(DATA_DIR, "BankChurners.csv")
FRAUD_CSV = os.path.join(DATA_DIR, "creditcard.csv")
FRAUD_SAMPLE_SIZE = 50000

CHURN_RENAME = {
    "Customer_Age":              "age",
    "Gender":                    "gender",
    "Education_Level":           "education",
    "Marital_Status":            "marital_status",
    "Income_Category":           "income_category",
    "Card_Category":             "card_category",
    "Months_on_book":            "months_on_book",
    "Credit_Limit":              "credit_limit",
    "Avg_Utilization_Ratio":     "avg_utilization_ratio",
    "Total_Trans_Amt":           "total_trans_amt",
    "Total_Trans_Ct":            "total_trans_ct",
    "Months_Inactive_12_mon":    "months_inactive_12_mon",
    "Contacts_Count_12_mon":     "contacts_count_12_mon",
}


def load_customers(engine):
    print("[ETL] Loading BankChurners.csv ...")
    df = pd.read_csv(CHURN_CSV)

    nb_cols = [c for c in df.columns if "Naive_Bayes" in c or "Naive Bayes" in c]
    if nb_cols:
        df.drop(columns=nb_cols, inplace=True)

    if "CLIENTNUM" in df.columns:
        df.drop(columns=["CLIENTNUM"], inplace=True)

    df["is_churned"] = df["Attrition_Flag"].str.strip().str.lower() == "attrited customer"
    df.drop(columns=["Attrition_Flag"], inplace=True)

    df.rename(columns=CHURN_RENAME, inplace=True)

    keep = list(CHURN_RENAME.values()) + ["is_churned"]
    available = [c for c in keep if c in df.columns]
    df = df[available].copy()

    df["churn_risk_score"] = None
    df["segment_id"]       = None
    df["segment_label"]    = None

    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE customers RESTART IDENTITY CASCADE"))
        conn.commit()

    df.to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=500)
    print(f"[ETL] Inserted {len(df)} customer rows into 'customers'.")


def load_transactions(engine):
    print("[ETL] Loading creditcard.csv ...")
    df = pd.read_csv(FRAUD_CSV)

    df.rename(columns={
        "Time":   "time_hours",
        "Amount": "amount",
        "Class":  "fraud_flag",
    }, inplace=True)

    v_cols = [f"V{i}" for i in range(1, 5)]
    missing_v = [c for c in v_cols if c not in df.columns]
    for c in missing_v:
        df[c] = 0.0

    v_rename = {f"V{i}": f"v{i}" for i in range(1, 5)}
    df.rename(columns=v_rename, inplace=True)

    df["fraud_flag"] = df["fraud_flag"].astype(bool)
    df["anomaly_score"] = 0.0

    keep = ["amount", "time_hours", "v1", "v2", "v3", "v4", "fraud_flag", "anomaly_score"]
    df = df[keep].copy()

    if len(df) > FRAUD_SAMPLE_SIZE:
        fraud_rows = df[df["fraud_flag"] == True]
        legit_rows = df[df["fraud_flag"] == False].sample(
            n=min(FRAUD_SAMPLE_SIZE - len(fraud_rows), len(df[df["fraud_flag"] == False])),
            random_state=42
        )
        df = pd.concat([fraud_rows, legit_rows]).sample(frac=1, random_state=42).reset_index(drop=True)

    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE transactions RESTART IDENTITY CASCADE"))
        conn.commit()

    df.to_sql("transactions", engine, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"[ETL] Inserted {len(df)} transaction rows into 'transactions'.")


def run_pipeline():
    engine = get_engine()

    if not os.path.exists(CHURN_CSV):
        raise FileNotFoundError(f"BankChurners.csv not found at: {CHURN_CSV}")
    if not os.path.exists(FRAUD_CSV):
        raise FileNotFoundError(f"creditcard.csv not found at: {FRAUD_CSV}")

    load_customers(engine)
    load_transactions(engine)
    print("[ETL] Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()