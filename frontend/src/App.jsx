// frontend/src/App.jsx

import { useState } from "react";
import client from "./api/client";

const INITIAL_FORM = {
  age: "",
  months_on_book: "",
  credit_limit: "",
  avg_utilization_ratio: "",
  total_trans_amt: "",
  total_trans_ct: "",
  months_inactive_12_mon: "",
  contacts_count_12_mon: "",
};

const FIELDS = [
  { key: "age",                    label: "Age",                        placeholder: "e.g. 45",      step: "1"    },
  { key: "months_on_book",         label: "Months on Book",             placeholder: "e.g. 36",      step: "1"    },
  { key: "credit_limit",           label: "Credit Limit ($)",           placeholder: "e.g. 12000",   step: "0.01" },
  { key: "avg_utilization_ratio",  label: "Avg Utilization Ratio",      placeholder: "e.g. 0.25",    step: "0.01" },
  { key: "total_trans_amt",        label: "Total Transaction Amount ($)",placeholder: "e.g. 4500",    step: "0.01" },
  { key: "total_trans_ct",         label: "Total Transaction Count",    placeholder: "e.g. 60",      step: "1"    },
  { key: "months_inactive_12_mon", label: "Months Inactive (12 mon)",   placeholder: "e.g. 2",       step: "1"    },
  { key: "contacts_count_12_mon",  label: "Contacts Count (12 mon)",    placeholder: "e.g. 3",       step: "1"    },
];

const RISK_CONFIG = {
  HIGH:   { color: "#ef4444", bg: "#fef2f2", border: "#fca5a5", label: "🔴 HIGH RISK"   },
  MEDIUM: { color: "#f59e0b", bg: "#fffbeb", border: "#fcd34d", label: "🟡 MEDIUM RISK" },
  LOW:    { color: "#10b981", bg: "#f0fdf4", border: "#6ee7b7", label: "🟢 LOW RISK"    },
};

const styles = {
  app: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f2041 0%, #1a3a6b 60%, #0f2041 100%)",
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    padding: "2rem 1rem",
  },
  container: {
    maxWidth: "860px",
    margin: "0 auto",
  },
  header: {
    textAlign: "center",
    marginBottom: "2rem",
  },
  headerTitle: {
    fontSize: "1.9rem",
    fontWeight: "800",
    color: "#ffffff",
    letterSpacing: "-0.5px",
    margin: 0,
  },
  headerSub: {
    color: "#93b4d8",
    marginTop: "0.4rem",
    fontSize: "0.95rem",
  },
  card: {
    background: "#ffffff",
    borderRadius: "16px",
    padding: "2rem",
    boxShadow: "0 8px 40px rgba(0,0,0,0.25)",
    marginBottom: "1.5rem",
  },
  cardTitle: {
    fontSize: "1.1rem",
    fontWeight: "700",
    color: "#0f2041",
    marginBottom: "1.25rem",
    paddingBottom: "0.6rem",
    borderBottom: "2px solid #e8eef6",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
    gap: "1rem",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "0.3rem",
  },
  label: {
    fontSize: "0.78rem",
    fontWeight: "600",
    color: "#4b5a72",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  input: {
    padding: "0.55rem 0.75rem",
    border: "1.5px solid #d1dce8",
    borderRadius: "8px",
    fontSize: "0.95rem",
    color: "#1a2940",
    outline: "none",
    transition: "border-color 0.2s",
    width: "100%",
    boxSizing: "border-box",
  },
  submitBtn: {
    marginTop: "1.5rem",
    width: "100%",
    padding: "0.85rem",
    background: "linear-gradient(90deg, #1a56db, #2563eb)",
    color: "#ffffff",
    border: "none",
    borderRadius: "10px",
    fontSize: "1rem",
    fontWeight: "700",
    cursor: "pointer",
    letterSpacing: "0.03em",
    transition: "opacity 0.2s",
  },
  errorBox: {
    background: "#fef2f2",
    border: "1px solid #fca5a5",
    color: "#b91c1c",
    borderRadius: "10px",
    padding: "0.85rem 1rem",
    fontSize: "0.9rem",
    marginBottom: "1rem",
  },
  resultCard: (risk) => ({
    background: RISK_CONFIG[risk]?.bg || "#f9fafb",
    border: `2px solid ${RISK_CONFIG[risk]?.border || "#e5e7eb"}`,
    borderRadius: "16px",
    padding: "1.75rem",
    boxShadow: "0 4px 20px rgba(0,0,0,0.10)",
  }),
  resultTitle: {
    fontSize: "1.05rem",
    fontWeight: "700",
    color: "#0f2041",
    marginBottom: "1.2rem",
    paddingBottom: "0.5rem",
    borderBottom: "1.5px solid #e8eef6",
  },
  kpiRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))",
    gap: "1rem",
    marginBottom: "1.25rem",
  },
  kpiBox: (color, bg) => ({
    background: bg || "#f9fafb",
    border: `1.5px solid ${color}33`,
    borderRadius: "12px",
    padding: "1rem",
    textAlign: "center",
  }),
  kpiValue: (color) => ({
    fontSize: "1.6rem",
    fontWeight: "800",
    color: color || "#1a2940",
    lineHeight: 1.1,
  }),
  kpiLabel: {
    fontSize: "0.73rem",
    color: "#6b7a90",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginTop: "0.3rem",
  },
  riskBadge: (risk) => ({
    display: "inline-block",
    background: RISK_CONFIG[risk]?.color || "#6b7280",
    color: "#fff",
    borderRadius: "999px",
    padding: "0.3rem 0.85rem",
    fontSize: "0.82rem",
    fontWeight: "700",
    letterSpacing: "0.05em",
  }),
  recBox: {
    background: "#f0f6ff",
    border: "1.5px solid #bfd4f5",
    borderRadius: "10px",
    padding: "0.9rem 1rem",
    color: "#1e3a5f",
    fontSize: "0.93rem",
    lineHeight: "1.5",
  },
  recLabel: {
    fontWeight: "700",
    fontSize: "0.78rem",
    textTransform: "uppercase",
    color: "#2563eb",
    letterSpacing: "0.05em",
    marginBottom: "0.3rem",
  },
  loader: {
    textAlign: "center",
    color: "#2563eb",
    fontWeight: "600",
    padding: "1rem",
    fontSize: "0.95rem",
  },
};

export default function App() {
  const [form,    setForm]    = useState(INITIAL_FORM);
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    const payload = {};
    for (const key of Object.keys(INITIAL_FORM)) {
      const val = parseFloat(form[key]);
      if (isNaN(val)) {
        setError(`Please enter a valid number for "${key.replaceAll("_", " ")}".`);
        setLoading(false);
        return;
      }
      payload[key] = val;
    }

    try {
      const { data } = await client.post("/predict/risk", payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const riskCfg = result ? (RISK_CONFIG[result.risk_level] || RISK_CONFIG.LOW) : null;

  return (
    <div style={styles.app}>
      <div style={styles.container}>

        <div style={styles.header}>
          <h1 style={styles.headerTitle}>CreditLens</h1>
          <p style={styles.headerSub}>Credit Risk &amp; Churn Prediction Platform</p>
        </div>

        <div style={styles.card}>
          <div style={styles.cardTitle}>Customer Profile Input</div>
          <form onSubmit={handleSubmit}>
            <div style={styles.grid}>
              {FIELDS.map(({ key, label, placeholder, step }) => (
                <div key={key} style={styles.fieldGroup}>
                  <label htmlFor={key} style={styles.label}>{label}</label>
                  <input
                    id={key}
                    name={key}
                    type="number"
                    step={step}
                    placeholder={placeholder}
                    value={form[key]}
                    onChange={handleChange}
                    required
                    style={styles.input}
                    onFocus={(e)  => (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e)   => (e.target.style.borderColor = "#d1dce8")}
                  />
                </div>
              ))}
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{ ...styles.submitBtn, opacity: loading ? 0.7 : 1 }}
            >
              {loading ? "Analysing…" : "Predict Churn Risk"}
            </button>
          </form>
        </div>

        {error && (
          <div style={styles.errorBox}>
            ⚠️ {error}
          </div>
        )}

        {loading && (
          <div style={styles.loader}>Running model inference…</div>
        )}

        {result && riskCfg && (
          <div style={styles.resultCard(result.risk_level)}>
            <div style={styles.resultTitle}>Prediction Results</div>

            <div style={styles.kpiRow}>
              <div style={styles.kpiBox(riskCfg.color, riskCfg.bg)}>
                <div style={styles.kpiValue(riskCfg.color)}>
                  {(result.churn_risk_score * 100).toFixed(1)}%
                </div>
                <div style={styles.kpiLabel}>Churn Risk Score</div>
              </div>

              <div style={styles.kpiBox("#2563eb", "#eff6ff")}>
                <div style={{ marginBottom: "0.4rem" }}>
                  <span style={styles.riskBadge(result.risk_level)}>
                    {riskCfg.label}
                  </span>
                </div>
                <div style={styles.kpiLabel}>Risk Level</div>
              </div>

              <div style={styles.kpiBox("#7c3aed", "#f5f3ff")}>
                <div style={styles.kpiValue("#7c3aed")}>
                  {result.segment_id ?? "—"}
                </div>
                <div style={styles.kpiLabel}>Segment ID</div>
              </div>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <div style={{ ...styles.kpiLabel, color: "#7c3aed", marginBottom: "0.35rem" }}>
                Customer Segment
              </div>
              <div style={{
                background: "#f5f3ff",
                border: "1.5px solid #c4b5fd",
                borderRadius: "10px",
                padding: "0.75rem 1rem",
                color: "#4c1d95",
                fontWeight: "600",
                fontSize: "0.97rem",
              }}>
                {result.segment_label}
              </div>
            </div>

            <div>
              <div style={styles.recLabel}>Recommended Action</div>
              <div style={styles.recBox}>
                💡 {result.recommendation}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}