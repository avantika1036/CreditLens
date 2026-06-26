-- backend/db/schema.sql

CREATE TABLE IF NOT EXISTS customers (
    customer_id       SERIAL PRIMARY KEY,
    age               INT,
    gender            TEXT,
    education         TEXT,
    marital_status    TEXT,
    income_category   TEXT,
    card_category     TEXT,
    months_on_book    INT,
    credit_limit      FLOAT,
    avg_utilization_ratio FLOAT,
    total_trans_amt   FLOAT,
    total_trans_ct    INT,
    months_inactive_12_mon INT,
    contacts_count_12_mon  INT,
    churn_risk_score  FLOAT,
    segment_id        INT,
    segment_label     TEXT,
    is_churned        BOOLEAN
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id        SERIAL PRIMARY KEY,
    amount        FLOAT,
    time_hours    FLOAT,
    v1            FLOAT,
    v2            FLOAT,
    v3            FLOAT,
    v4            FLOAT,
    fraud_flag    BOOLEAN,
    anomaly_score FLOAT
);

CREATE TABLE IF NOT EXISTS shap_features (
    id          SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id) ON DELETE CASCADE,
    feature_name TEXT,
    shap_value  FLOAT
);

CREATE TABLE IF NOT EXISTS monthly_reports (
    id               SERIAL PRIMARY KEY,
    report_month     TEXT,
    total_customers  INT,
    high_risk_count  INT,
    fraud_count      INT,
    avg_churn_score  FLOAT,
    generated_at     TIMESTAMP DEFAULT NOW()
);