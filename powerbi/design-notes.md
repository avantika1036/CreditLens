# CreditLens — Power BI Dashboard Design Notes

## 1. Data Source Connection

Connect Power BI Desktop to PostgreSQL using DirectQuery so all visuals always
reflect the latest model outputs written by the ML pipeline.

```
Home → Get Data → PostgreSQL database
Server:   localhost          (or your host / Docker container IP)
Port:     5432
Database: creditlens
Mode:     DirectQuery
```

Import these three tables:

| Table           | Key columns used in Power BI                                                                 |
|-----------------|----------------------------------------------------------------------------------------------|
| `customers`     | customer_id, age, gender, education, income_category, card_category, credit_limit,           |
|                 | avg_utilization_ratio, total_trans_amt, total_trans_ct, months_inactive_12_mon,              |
|                 | contacts_count_12_mon, churn_risk_score, segment_id, segment_label, is_churned               |
| `transactions`  | txn_id, amount, time_hours, v1, v2, v3, v4, fraud_flag, anomaly_score                       |
| `shap_features` | id, customer_id, feature_name, shap_value                                                    |

---

## 2. Relationships

```
customers.customer_id  ──(1)────(*)──  shap_features.customer_id
```

`transactions` has no foreign key to `customers` in this schema; treat it as a
standalone fact table. Link it to a disconnected Date/Time helper table if
time-series slicing is needed.

---

## 3. DAX Measures

Create a dedicated measures table: **Home → Enter Data → name it `_Measures`**,
then add the following calculated measures.

### 3.1 Customer Measures

```dax
Total Customers =
    COUNTROWS( customers )

Churned Customers =
    CALCULATE(
        COUNTROWS( customers ),
        customers[is_churned] = TRUE()
    )

Churn Rate % =
    DIVIDE( [Churned Customers], [Total Customers], 0 ) * 100

Avg Churn Risk =
    AVERAGE( customers[churn_risk_score] )

High Risk Count =
    CALCULATE(
        COUNTROWS( customers ),
        customers[churn_risk_score] > 0.7
    )

High Risk % =
    DIVIDE( [High Risk Count], [Total Customers], 0 ) * 100

Medium Risk Count =
    CALCULATE(
        COUNTROWS( customers ),
        customers[churn_risk_score] >= 0.4,
        customers[churn_risk_score] <= 0.7
    )

Low Risk Count =
    CALCULATE(
        COUNTROWS( customers ),
        customers[churn_risk_score] < 0.4
    )

Avg Credit Limit =
    AVERAGE( customers[credit_limit] )

Avg Utilization =
    AVERAGE( customers[avg_utilization_ratio] )

Avg Trans Amount =
    AVERAGE( customers[total_trans_amt] )
```

### 3.2 Fraud & Transaction Measures

```dax
Total Transactions =
    COUNTROWS( transactions )

Fraud Flagged =
    CALCULATE(
        COUNTROWS( transactions ),
        transactions[fraud_flag] = TRUE()
    )

Fraud Rate % =
    DIVIDE( [Fraud Flagged], [Total Transactions], 0 ) * 100

Avg Anomaly Score =
    AVERAGE( transactions[anomaly_score] )

High Anomaly Count =
    CALCULATE(
        COUNTROWS( transactions ),
        transactions[anomaly_score] > 0.7
    )

Avg Transaction Amount =
    AVERAGE( transactions[amount] )

Fraud Transaction Amount =
    CALCULATE(
        SUM( transactions[amount] ),
        transactions[fraud_flag] = TRUE()
    )
```

### 3.3 SHAP Measures

```dax
Avg Abs SHAP =
    AVERAGEX(
        shap_features,
        ABS( shap_features[shap_value] )
    )

Max SHAP Value =
    MAXX( shap_features, ABS( shap_features[shap_value] ) )

SHAP Direction =
    IF(
        AVERAGE( shap_features[shap_value] ) > 0,
        "Increases Risk",
        "Decreases Risk"
    )
```

### 3.4 Segment Measures

```dax
Segment Customer Count =
    COUNTROWS( customers )

Segment Avg Risk =
    AVERAGE( customers[churn_risk_score] )

Segment Avg Credit Limit =
    AVERAGE( customers[credit_limit] )

Segment Avg Trans Amt =
    AVERAGE( customers[total_trans_amt] )
```

---

## 4. Calculated Columns

Add these directly on the `customers` table.

```dax
-- Classify each customer into a risk band
Risk Level =
    SWITCH(
        TRUE(),
        customers[churn_risk_score] >= 0.7, "HIGH",
        customers[churn_risk_score] >= 0.4, "MEDIUM",
        "LOW"
    )

-- Ordinal for sorting Risk Level
Risk Level Order =
    SWITCH(
        customers[Risk Level],
        "HIGH",   1,
        "MEDIUM", 2,
        "LOW",    3
    )

-- Churn risk as a display percentage string
Churn Risk % Label =
    FORMAT( customers[churn_risk_score], "0.0%" )
```

Add on `transactions`:

```dax
Anomaly Band =
    SWITCH(
        TRUE(),
        transactions[anomaly_score] >= 0.7, "High",
        transactions[anomaly_score] >= 0.4, "Medium",
        "Low"
    )
```

---

## 5. Dashboard Pages

### Page 1 — Executive Overview

**Purpose:** Single-glance KPI summary for leadership.

**Canvas size:** 1280 × 720 px  |  **Theme:** Dark navy background (#0F2041)

| Visual                    | Type            | Fields / Measures                                                                 | Notes                                              |
|---------------------------|-----------------|-----------------------------------------------------------------------------------|----------------------------------------------------|
| Total Customers           | KPI Card        | `[Total Customers]`                                                               | Trend line off                                     |
| Avg Churn Risk Score      | KPI Card        | `[Avg Churn Risk]`                                                                | Format as 0.000                                    |
| High Risk Customers       | KPI Card        | `[High Risk Count]`, subtitle `[High Risk %]`                                    | Conditional color: red if > 20%                    |
| Actual Churned            | KPI Card        | `[Churned Customers]`, `[Churn Rate %]`                                          |                                                    |
| Fraud Flagged             | KPI Card        | `[Fraud Flagged]`, `[Fraud Rate %]`                                              | Accent color orange                                |
| Churn Risk Distribution   | Histogram       | X-axis: `churn_risk_score` (binned 0.05), Y-axis: `[Total Customers]`            | Add reference line at 0.7 (High Risk threshold)    |
| Risk Level Donut          | Donut Chart     | Legend: `Risk Level`, Values: `[Total Customers]`                                | RED / AMBER / GREEN fill                           |
| Customers by Segment      | Bar Chart       | X-axis: `segment_label`, Y-axis: `[Total Customers]`                             | Sorted descending                                  |
| Churn Risk by Card Type   | Clustered Bar   | X-axis: `card_category`, Y-axis: `[Avg Churn Risk]`                              |                                                    |
| Income Category Slicer    | Slicer          | `income_category`                                                                 | Dropdown style                                     |
| Gender Slicer             | Slicer          | `gender`                                                                          | Tile style                                         |

---

### Page 2 — Customer Segmentation

**Purpose:** Understand how customers cluster by spending and risk profile.

| Visual                          | Type               | Fields / Measures                                                                           | Notes                                                   |
|---------------------------------|--------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------|
| Segment Distribution            | Donut Chart        | Legend: `segment_label`, Values: `[Segment Customer Count]`                                | 5 distinct colors per segment                           |
| Segment KPI Table               | Matrix             | Rows: `segment_label`; Values: `[Segment Customer Count]`, `[Segment Avg Risk]`,           | Conditional formatting on avg risk column               |
|                                 |                    | `[Segment Avg Credit Limit]`, `[Segment Avg Trans Amt]`                                    |                                                          |
| Credit Limit vs Utilization     | Scatter Chart      | X: `avg_utilization_ratio`, Y: `credit_limit`,                                             | Color by `segment_label`; size by `total_trans_amt`     |
|                                 |                    | Legend: `segment_label`, Size: `total_trans_amt`                                           |                                                          |
| Avg Churn Risk by Segment       | Horizontal Bar     | Y-axis: `segment_label`, X-axis: `[Segment Avg Risk]`                                     | Sorted descending; conditional color gradient           |
| Transaction Amount by Segment   | Clustered Bar      | X-axis: `segment_label`, Y-axis: `[Segment Avg Trans Amt]`                                |                                                          |
| Months Inactive by Segment      | Box Plot / Bar     | X-axis: `segment_label`, Y-axis: `months_inactive_12_mon` (average)                       |                                                          |
| Segment Slicer                  | Slicer             | `segment_label`                                                                             | Multi-select                                            |
| Card Category Slicer            | Slicer             | `card_category`                                                                             |                                                          |

---

### Page 3 — Risk Leaderboard

**Purpose:** Surface the highest-risk customers for retention teams.

| Visual                          | Type               | Fields / Measures                                                                           | Notes                                                    |
|---------------------------------|--------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------|
| Top N Risk Slider               | Numeric Range Slicer | Filter `churn_risk_score` minimum                                                         | Default: 0.7                                            |
| High Risk Customer Table        | Table              | `customer_id`, `age`, `gender`, `income_category`, `card_category`,                       | Sort by `churn_risk_score` DESC; highlight HIGH rows    |
|                                 |                    | `credit_limit`, `total_trans_amt`, `Churn Risk % Label`, `Risk Level`, `segment_label`    |                                                          |
| Churn Score Gauge               | Gauge              | Value: `[Avg Churn Risk]`, Min: 0, Max: 1, Target: 0.5                                   | Filtered to page-level selection                        |
| Risk by Age Band                | Clustered Column   | X: Age Band (calculated: `<30 / 30-45 / 45-60 / 60+`), Y: `[Avg Churn Risk]`             | Add `[High Risk Count]` as line on secondary axis       |
| Risk by Education               | Bar Chart          | X-axis: `education`, Y-axis: `[Avg Churn Risk]`                                           | Sorted descending                                       |
| Risk by Inactivity Months       | Line Chart         | X: `months_inactive_12_mon`, Y: `[Avg Churn Risk]`                                        | Shows rising risk with inactivity                       |
| Contacts vs Churn Risk          | Scatter            | X: `contacts_count_12_mon`, Y: `churn_risk_score`, Legend: `Risk Level`                   |                                                          |
| Risk Level Slicer               | Slicer             | `Risk Level` (calculated column)                                                           | Tile: HIGH / MEDIUM / LOW                              |

---

### Page 4 — Fraud Console

**Purpose:** Monitor anomalous transactions flagged by Isolation Forest.

| Visual                          | Type               | Fields / Measures                                                                           | Notes                                                    |
|---------------------------------|--------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------|
| Fraud Flagged KPI               | KPI Card           | `[Fraud Flagged]`                                                                           |                                                          |
| Fraud Rate KPI                  | KPI Card           | `[Fraud Rate %]`                                                                            | Alert color if > 0.5%                                   |
| Avg Anomaly Score KPI           | KPI Card           | `[Avg Anomaly Score]`                                                                       |                                                          |
| Fraud Transaction $ KPI         | KPI Card           | `[Fraud Transaction Amount]`                                                                |                                                          |
| Anomaly Score Distribution      | Histogram          | X: `anomaly_score` (binned 0.05), Y: `[Total Transactions]`                               | Reference line at 0.7                                   |
| Anomaly Band Donut              | Donut Chart        | Legend: `Anomaly Band`, Values: `[Total Transactions]`                                     | High = red, Medium = amber, Low = green                 |
| Top Anomalous Transactions      | Table              | `txn_id`, `amount`, `time_hours`, `v1`, `v2`, `v3`, `v4`, `fraud_flag`, `anomaly_score`  | Sort by `anomaly_score` DESC; top 100                   |
| Amount vs Anomaly Score         | Scatter Chart      | X: `amount`, Y: `anomaly_score`, Color: `fraud_flag`                                      | True fraud points in red; useful for threshold tuning   |
| Fraud by Amount Range           | Clustered Bar      | X: Amount bucket (<100 / 100-500 / 500-1k / 1k+), Y: `[Fraud Flagged]`                   | Reveals which spend tiers are most anomalous            |
| Anomaly Score Slicer            | Numeric Slicer     | `anomaly_score` — minimum threshold                                                        | Default: 0.5                                            |
| Fraud Flag Slicer               | Slicer             | `fraud_flag`  (TRUE / FALSE / ALL)                                                         |                                                          |

---

### Page 5 — SHAP Explainability

**Purpose:** Explain why individual customers are predicted as high churn risk.

| Visual                          | Type               | Fields / Measures                                                                           | Notes                                                    |
|---------------------------------|--------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------|
| Customer ID Slicer              | Slicer             | `shap_features[customer_id]`                                                               | Dropdown; drives all visuals on page                    |
| Selected Customer Risk Card     | KPI Card           | `[Avg Churn Risk]` filtered to selected customer via slicer                                | Cross-filter from SHAP table via relationship           |
| Segment Label Card              | Card               | `customers[segment_label]` filtered to selected customer                                   |                                                          |
| Global Feature Importance       | Horizontal Bar     | Y: `feature_name`, X: `[Avg Abs SHAP]`                                                    | Aggregate over all 500 customers in shap_features       |
|                                 |                    | Sort by `[Avg Abs SHAP]` descending                                                        | Shows which features matter most globally               |
| Per-Customer SHAP Waterfall     | Horizontal Bar     | Y: `feature_name`, X: `shap_value` (can be negative)                                      | Filter to selected customer_id; color: red if > 0,      |
|                                 |                    | Color by: `[SHAP Direction]`                                                               | blue if < 0 (risk-increasing vs risk-decreasing)        |
| SHAP Value Table                | Table              | `feature_name`, `shap_value`, `[SHAP Direction]`                                           | Sorted by ABS(shap_value) DESC for selected customer    |
| Top Risk-Increasing Features    | Bar Chart          | Filter: `shap_value > 0`; Y: `feature_name`, X: `shap_value`                              | Shows what drives this customer toward churn            |
| Top Risk-Decreasing Features    | Bar Chart          | Filter: `shap_value < 0`; Y: `feature_name`, X: `ABS(shap_value)`                         | Shows what protects this customer from churn            |

---

## 6. Formatting & Theme Guidelines

```
Background:         #0F2041  (dark navy)
Card background:    #162848
Accent / highlight: #2563EB  (blue)
High risk color:    #EF4444  (red)
Medium risk color:  #F59E0B  (amber)
Low risk color:     #10B981  (green)
Text primary:       #FFFFFF
Text secondary:     #93B4D8
Font:               Segoe UI  (Power BI default)
```

Apply via **View → Themes → Customize current theme** and paste the hex values above
into the corresponding color slots. This keeps the Power BI palette consistent with the
React frontend and PDF report.

---

## 7. Publishing & Refresh

1. **Publish** the `.pbix` file to Power BI Service (requires Pro or Premium licence).
2. Install the **On-premises data gateway** on the machine running PostgreSQL.
3. In Power BI Service → **Dataset Settings → Gateway connection** → map to your
   PostgreSQL data source.
4. Set a **Scheduled Refresh** (e.g. daily at 06:00) so the dashboard picks up any
   nightly ML pipeline runs automatically.
5. Share the workspace link or embed via **Publish to web** for demo purposes.

---

## 8. Quick DAX Reference Card

```
[Total Customers]         COUNTROWS(customers)
[Churned Customers]       CALCULATE(COUNTROWS(customers), is_churned = TRUE())
[Churn Rate %]            DIVIDE([Churned Customers], [Total Customers], 0) * 100
[Avg Churn Risk]          AVERAGE(customers[churn_risk_score])
[High Risk Count]         CALCULATE(COUNTROWS(customers), churn_risk_score > 0.7)
[High Risk %]             DIVIDE([High Risk Count], [Total Customers], 0) * 100
[Fraud Flagged]           CALCULATE(COUNTROWS(transactions), fraud_flag = TRUE())
[Fraud Rate %]            DIVIDE([Fraud Flagged], [Total Transactions], 0) * 100
[Avg Anomaly Score]       AVERAGE(transactions[anomaly_score])
[Avg Abs SHAP]            AVERAGEX(shap_features, ABS(shap_features[shap_value]))
```