// frontend/src/App.jsx
//
// No external UI dependencies beyond React itself — icons are small inline SVGs,
// entrance animations are plain CSS keyframes, and the risk ring is hand-drawn SVG.

import { useState, useEffect } from "react";
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

/* ---------------------------------------------------------------- */
/* Minimal inline icon set (replaces lucide-react)                  */
/* ---------------------------------------------------------------- */
const iconBase = { width: "1em", height: "1em", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" };

const Icon = {
  User: (p) => (<svg {...iconBase} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 4-6 8-6s8 2 8 6" /></svg>),
  Calendar: (p) => (<svg {...iconBase} {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></svg>),
  CreditCard: (p) => (<svg {...iconBase} {...p}><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></svg>),
  Percent: (p) => (<svg {...iconBase} {...p}><path d="M19 5L5 19" /><circle cx="7" cy="7" r="2" /><circle cx="17" cy="17" r="2" /></svg>),
  Dollar: (p) => (<svg {...iconBase} {...p}><path d="M12 2v20" /><path d="M17 6c0-1.7-2.2-3-5-3s-5 1.3-5 3 2.2 3 5 3 5 1.3 5 3-2.2 3-5 3-5-1.3-5-3" /></svg>),
  Hash: (p) => (<svg {...iconBase} {...p}><path d="M5 9h14M5 15h14M9 4l-2 16M17 4l-2 16" /></svg>),
  Clock: (p) => (<svg {...iconBase} {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>),
  Phone: (p) => (<svg {...iconBase} {...p}><path d="M5 4h4l1.5 5L8 11.5a12 12 0 005 5L15.5 14l5 1.5v4a2 2 0 01-2 2C9.5 21.5 2.5 14.5 3 5a2 2 0 012-1z" /></svg>),
  Zap: (p) => (<svg {...iconBase} {...p}><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" /></svg>),
  Brain: (p) => (<svg {...iconBase} {...p}><path d="M9 4a3 3 0 00-3 3v1a3 3 0 00-2 2.8V13a3 3 0 002 2.8v1A3 3 0 009 20" /><path d="M15 4a3 3 0 013 3v1a3 3 0 012 2.8V13a3 3 0 01-2 2.8v1a3 3 0 01-3 3.2" /><path d="M9 4a3 3 0 013 3v10a3 3 0 01-3 3" /></svg>),
  BarChart: (p) => (<svg {...iconBase} {...p}><path d="M4 20V10M12 20V4M20 20v-7" /></svg>),
  Target: (p) => (<svg {...iconBase} {...p}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></svg>),
  Shield: (p) => (<svg {...iconBase} {...p}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" /></svg>),
  TrendUp: (p) => (<svg {...iconBase} {...p}><path d="M3 17l6-6 4 4 8-8" /><path d="M15 7h6v6" /></svg>),
  ArrowRight: (p) => (<svg {...iconBase} {...p}><path d="M5 12h14M13 6l6 6-6 6" /></svg>),
};

const FIELDS = [
  { key: "age",                    label: "Age",                    icon: Icon.User,       placeholder: "45",    step: "1"    },
  { key: "months_on_book",         label: "Months on book",         icon: Icon.Calendar,   placeholder: "36",    step: "1"    },
  { key: "credit_limit",           label: "Credit limit ($)",       icon: Icon.CreditCard, placeholder: "12000", step: "0.01" },
  { key: "avg_utilization_ratio",  label: "Avg utilization ratio",  icon: Icon.Percent,    placeholder: "0.25",  step: "0.01" },
  { key: "total_trans_amt",        label: "Total trans. amt ($)",   icon: Icon.Dollar,     placeholder: "4500",  step: "0.01" },
  { key: "total_trans_ct",         label: "Total transaction count", icon: Icon.Hash,      placeholder: "60",    step: "1"    },
  { key: "months_inactive_12_mon", label: "Months inactive (12mo)", icon: Icon.Clock,      placeholder: "2",     step: "1"    },
  { key: "contacts_count_12_mon",  label: "Contacts (12mo)",        icon: Icon.Phone,      placeholder: "3",     step: "1"    },
];

const FEATURES = [
  { icon: Icon.Zap,       title: "Real-time prediction",  sub: "Sub-second inference" },
  { icon: Icon.Brain,     title: "Explainable AI",        sub: "Transparent factors" },
  { icon: Icon.BarChart,  title: "Customer segmentation", sub: "5 behavioral cohorts" },
  { icon: Icon.Target,    title: "Retention guidance",    sub: "Actionable next steps" },
];

const RISK_CONFIG = {
  HIGH:   { hex: "#F87171", glow: "rgba(248,113,113,0.18)", label: "High risk" },
  MEDIUM: { hex: "#FBBF24", glow: "rgba(251,191,36,0.18)",  label: "Medium risk" },
  LOW:    { hex: "#34D399", glow: "rgba(52,211,153,0.18)",  label: "Low risk" },
};

/* ---------------------------------------------------------------- */
/* One-time font + keyframes injection (replaces framer-motion)     */
/* ---------------------------------------------------------------- */
const ASSETS_ID = "creditlens-assets";
function useInjectedAssets() {
  useEffect(() => {
    if (document.getElementById(ASSETS_ID)) return;
    const style = document.createElement("style");
    style.id = ASSETS_ID;
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
      @keyframes cl-fade-up {
        from { opacity: 0; transform: translateY(24px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      @keyframes cl-fade-in {
        from { opacity: 0; }
        to   { opacity: 1; }
      }
      .cl-anim {
        animation: cl-fade-up 0.6s ease both;
      }
      .cl-anim-fast {
        animation: cl-fade-in 0.4s ease both;
      }
      .cl-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 32px rgba(37,99,235,0.5);
      }
      .cl-btn:active {
        transform: scale(0.97);
      }
    `;
    document.head.appendChild(style);
  }, []);
}

/* ---------------------------------------------------------------- */
/* Hand-drawn SVG risk ring (replaces react-circular-progressbar)   */
/* ---------------------------------------------------------------- */
function useCountUp(target, duration = 800) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => raf && cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);
  return value;
}

function RiskRing({ score, risk }) {
  const cfg = RISK_CONFIG[risk] || RISK_CONFIG.LOW;
  const animated = useCountUp(score, 800);
  const pct = Math.min(100, Math.max(0, animated * 100));
  const size = 168;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const minDash = 0.012; // keep a visible sliver even near 0%
  const dashFrac = Math.max(minDash, pct / 100);
  const dashOffset = c * (1 - dashFrac);

  return (
    <div style={{ width: size, height: size, position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={cfg.hex} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke 0.3s ease" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "1.5rem", fontWeight: 700, color: "#F8FAFC", fontFamily: "'Inter', sans-serif",
      }}>
        {pct.toFixed(1)}%
      </div>
    </div>
  );
}

const styles = {
  page: {
    position: "relative",
    minHeight: "100vh",
    background: `
      radial-gradient(circle at 12% 8%, rgba(37,99,235,0.16), transparent 38%),
      radial-gradient(circle at 88% 92%, rgba(124,58,237,0.16), transparent 38%),
      linear-gradient(135deg, #020617 0%, #0B1222 50%, #020617 100%)
    `,
    fontFamily: "'Inter', -apple-system, system-ui, sans-serif",
    color: "#F1F5F9",
    overflow: "hidden",
  },
  orb1: {
    position: "fixed", width: "420px", height: "420px", background: "#2563EB",
    borderRadius: "50%", filter: "blur(150px)", opacity: 0.28,
    top: "-120px", left: "-120px", pointerEvents: "none",
  },
  orb2: {
    position: "fixed", width: "380px", height: "380px", background: "#7C3AED",
    borderRadius: "50%", filter: "blur(150px)", opacity: 0.26,
    bottom: "-120px", right: "-100px", pointerEvents: "none",
  },
  scroll: { position: "relative", zIndex: 1, padding: "4rem 1.5rem 6rem" },
  container: { maxWidth: "980px", margin: "0 auto" },
  hero: { textAlign: "center", marginBottom: "2.75rem" },
  heroEyebrow: {
    display: "inline-flex", alignItems: "center", gap: "8px",
    background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: "999px", padding: "0.4rem 1rem", fontSize: "0.85rem", fontWeight: 600,
    color: "#A5B4FC", marginBottom: "1.5rem",
  },
  heroTitle: {
    fontSize: "clamp(2.1rem, 5vw, 3.1rem)", fontWeight: 800, letterSpacing: "-0.02em",
    margin: "0 0 0.9rem", lineHeight: 1.12,
    background: "linear-gradient(135deg, #FFFFFF 30%, #C7D2FE 100%)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
  },
  heroSub: { fontSize: "1.1rem", color: "#94A3B8", maxWidth: "560px", margin: "0 auto 1.75rem", lineHeight: 1.6 },
  statRow: { display: "flex", justifyContent: "center", gap: "0.75rem", flexWrap: "wrap" },
  statBadge: {
    background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "999px", padding: "0.5rem 1.1rem", fontSize: "0.85rem", fontWeight: 600, color: "#E2E8F0",
  },
  statBadgeAccent: { color: "#93C5FD", fontWeight: 700 },
  featureGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "2rem" },
  featureCard: {
    background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: "16px", padding: "1.1rem 1.1rem", textAlign: "left",
  },
  featureIconWrap: {
    width: "34px", height: "34px", borderRadius: "10px", background: "rgba(99,102,241,0.18)",
    display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "0.65rem",
    color: "#A5B4FC", fontSize: "18px",
  },
  featureTitle: { fontSize: "0.92rem", fontWeight: 700, color: "#F1F5F9", marginBottom: "0.2rem" },
  featureSub: { fontSize: "0.78rem", color: "#94A3B8" },
  glassCard: {
    background: "rgba(255,255,255,0.06)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)",
    border: "1px solid rgba(255,255,255,0.12)", borderRadius: "22px",
    boxShadow: "0 8px 40px rgba(0,0,0,0.45)", padding: "2.1rem 2.25rem", marginBottom: "1.75rem",
  },
  cardHeadRow: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "0.35rem", fontSize: "20px" },
  cardTitle: { fontSize: "1.25rem", fontWeight: 700, color: "#F8FAFC" },
  cardSubtitle: { fontSize: "0.95rem", color: "#94A3B8", marginBottom: "1.75rem" },
  grid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", columnGap: "1.25rem", rowGap: "1.4rem" },
  fieldGroup: { display: "flex", flexDirection: "column" },
  label: {
    display: "flex", alignItems: "center", gap: "6px", fontSize: "0.88rem", fontWeight: 600,
    color: "#CBD5E1", marginBottom: "0.55rem",
  },
  input: {
    background: "rgba(255,255,255,0.05)", border: "1.5px solid rgba(255,255,255,0.12)", borderRadius: "12px",
    padding: "0.75rem 0.9rem", fontSize: "1.02rem", color: "#F8FAFC", outline: "none",
    width: "100%", boxSizing: "border-box", transition: "all 0.18s ease",
  },
  submitRow: { marginTop: "2rem", display: "flex", justifyContent: "flex-end" },
  submitBtn: {
    display: "inline-flex", alignItems: "center", gap: "8px", padding: "0.95rem 1.9rem",
    background: "linear-gradient(135deg, #2563EB, #7C3AED)", color: "#ffffff", border: "none",
    borderRadius: "14px", fontSize: "1.02rem", fontWeight: 700, cursor: "pointer",
    boxShadow: "0 8px 25px rgba(37,99,235,0.4)", transition: "transform 0.18s ease, box-shadow 0.18s ease",
  },
  errorBox: {
    background: "rgba(248,113,113,0.1)", border: "1.5px solid rgba(248,113,113,0.3)", color: "#FCA5A5",
    borderRadius: "14px", padding: "1rem 1.25rem", fontSize: "0.98rem", fontWeight: 500, marginBottom: "1.75rem",
  },
  resultHeaderRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" },
  riskBadge: (risk) => ({
    display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "0.9rem", fontWeight: 700,
    color: (RISK_CONFIG[risk] || RISK_CONFIG.LOW).hex, background: (RISK_CONFIG[risk] || RISK_CONFIG.LOW).glow,
    border: `1.5px solid ${(RISK_CONFIG[risk] || RISK_CONFIG.LOW).hex}55`, borderRadius: "999px", padding: "0.45rem 1rem",
  }),
  resultGrid: { display: "grid", gridTemplateColumns: "240px 1fr", gap: "2.5rem", alignItems: "center" },
  ringCol: { display: "flex", flexDirection: "column", alignItems: "center" },
  ringLabel: { marginTop: "1rem", fontSize: "0.85rem", color: "#94A3B8", fontWeight: 600, letterSpacing: "0.02em" },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "1rem", marginBottom: "1.25rem" },
  kpiBox: { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "1.1rem 1.25rem" },
  kpiLabel: { fontSize: "0.8rem", color: "#94A3B8", fontWeight: 600, marginBottom: "0.35rem" },
  kpiValue: { fontSize: "1.1rem", fontWeight: 700, color: "#F8FAFC", lineHeight: 1.3 },
  recCard: { background: "rgba(99,102,241,0.12)", border: "1.5px solid rgba(129,140,248,0.3)", borderRadius: "14px", padding: "1.2rem 1.4rem" },
  recLabel: {
    display: "flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", fontWeight: 700, color: "#A5B4FC",
    marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em",
  },
  recText: { fontSize: "1rem", lineHeight: "1.6", color: "#E2E8F0" },
  emptyState: { textAlign: "center", padding: "2.75rem 1.5rem" },
  emptyIconWrap: {
    width: "56px", height: "56px", borderRadius: "16px", background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center",
    margin: "0 auto 1rem", color: "#94A3B8", fontSize: "24px",
  },
  emptyTitle: { fontSize: "1.15rem", fontWeight: 700, color: "#E2E8F0", marginBottom: "0.4rem" },
  emptyBody: { fontSize: "0.98rem", color: "#94A3B8", maxWidth: "380px", margin: "0 auto", lineHeight: "1.55" },
};

export default function App() {
  useInjectedAssets();
  const [form,    setForm]    = useState(INITIAL_FORM);
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [focusKey, setFocusKey] = useState(null);

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
        const fieldLabel = FIELDS.find((f) => f.key === key)?.label || key.replaceAll("_", " ");
        setError(`Enter a valid number for "${fieldLabel}".`);
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
    <div style={styles.page}>
      <div style={styles.orb1} />
      <div style={styles.orb2} />

      <div style={styles.scroll}>
        <div style={styles.container}>

          <div style={styles.hero} className="cl-anim">
            <span style={styles.heroEyebrow}>
              <Icon.Shield />
              CreditLens
            </span>
            <h1 style={styles.heroTitle}>AI-Powered Customer Intelligence</h1>
            <p style={styles.heroSub}>
              Predict churn risk, identify customer segments, and generate retention
              strategies using machine learning.
            </p>
            <div style={styles.statRow}>
              <span style={styles.statBadge}><span style={styles.statBadgeAccent}>99.2%</span> precision</span>
              <span style={styles.statBadge}><span style={styles.statBadgeAccent}>5</span> customer segments</span>
              <span style={styles.statBadge}><span style={styles.statBadgeAccent}>Real-time</span> inference</span>
            </div>
          </div>

          <div style={styles.featureGrid} className="cl-anim">
            {FEATURES.map(({ icon: FeatIcon, title, sub }) => (
              <div key={title} style={styles.featureCard}>
                <div style={styles.featureIconWrap}><FeatIcon /></div>
                <div style={styles.featureTitle}>{title}</div>
                <div style={styles.featureSub}>{sub}</div>
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="cl-anim">
            <div style={styles.glassCard}>
              <div style={styles.cardHeadRow}>
                <span style={{ color: "#A5B4FC", display: "flex" }}><Icon.TrendUp /></span>
                <span style={styles.cardTitle}>Customer profile</span>
              </div>
              <div style={styles.cardSubtitle}>Enter the account details to generate a churn risk prediction.</div>

              <div style={styles.grid}>
                {FIELDS.map(({ key, label, icon: FieldIcon, placeholder, step }) => (
                  <div key={key} style={styles.fieldGroup}>
                    <label htmlFor={key} style={styles.label}>
                      <span style={{ color: "#93C5FD", display: "flex", fontSize: "14px" }}><FieldIcon /></span>
                      {label}
                    </label>
                    <input
                      id={key}
                      name={key}
                      type="number"
                      step={step}
                      placeholder={placeholder}
                      value={form[key]}
                      onChange={handleChange}
                      onFocus={() => setFocusKey(key)}
                      onBlur={() => setFocusKey(null)}
                      required
                      style={{
                        ...styles.input,
                        borderColor: focusKey === key ? "#60A5FA" : "rgba(255,255,255,0.12)",
                        background: focusKey === key ? "rgba(255,255,255,0.09)" : "rgba(255,255,255,0.05)",
                        transform: focusKey === key ? "translateY(-2px)" : "translateY(0)",
                        boxShadow: focusKey === key ? "0 0 0 4px rgba(37,99,235,0.15)" : "none",
                      }}
                    />
                  </div>
                ))}
              </div>

              <div style={styles.submitRow}>
                <button
                  type="submit"
                  disabled={loading}
                  className="cl-btn"
                  style={{ ...styles.submitBtn, opacity: loading ? 0.7 : 1 }}
                >
                  {loading ? "Analyzing…" : "Predict churn risk"}
                  {!loading && <Icon.ArrowRight />}
                </button>
              </div>
            </div>
          </form>

          {error && (
            <div style={styles.errorBox} className="cl-anim-fast">
              {error}
            </div>
          )}

          <div
            key={result ? "result" : loading ? "loading" : "empty"}
            style={styles.glassCard}
            className="cl-anim"
          >
            {!loading && !result && (
              <div style={styles.emptyState}>
                <div style={styles.emptyIconWrap}><Icon.BarChart /></div>
                <div style={styles.emptyTitle}>No prediction yet</div>
                <div style={styles.emptyBody}>
                  Fill in the customer profile above and run the model to see a churn risk score here.
                </div>
              </div>
            )}

            {loading && (
              <div style={styles.emptyState}>
                <div style={styles.emptyTitle}>Running model inference…</div>
              </div>
            )}

            {!loading && result && (
              <>
                <div style={styles.resultHeaderRow}>
                  <div style={styles.cardHeadRow}>
                    <span style={{ color: "#A5B4FC", display: "flex" }}><Icon.Shield /></span>
                    <span style={styles.cardTitle}>Prediction results</span>
                  </div>
                  <span style={styles.riskBadge(result.risk_level)}>
                    {riskCfg.label}
                  </span>
                </div>

                <div style={styles.resultGrid}>
                  <div style={styles.ringCol}>
                    <RiskRing score={result.churn_risk_score} risk={result.risk_level} />
                    <div style={styles.ringLabel}>Churn probability</div>
                  </div>

                  <div>
                    <div style={styles.kpiGrid}>
                      <div style={styles.kpiBox}>
                        <div style={styles.kpiLabel}>Segment ID</div>
                        <div style={styles.kpiValue}>{result.segment_id ?? "—"}</div>
                      </div>
                      <div style={styles.kpiBox}>
                        <div style={styles.kpiLabel}>Segment label</div>
                        <div style={styles.kpiValue}>{result.segment_label ?? "—"}</div>
                      </div>
                    </div>

                    <div style={styles.recCard}>
                      <div style={styles.recLabel}>
                        <Icon.Target />
                        Recommended action
                      </div>
                      <div style={styles.recText}>{result.recommendation}</div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}