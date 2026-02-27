"""
DebtFree Advisor v2 — Smart Debt Payoff Platform for W-2 Employees
Run with: streamlit run debt_advisor.py
Requirements: pip install streamlit plotly pandas
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import math

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="DebtFree Advisor", page_icon="💳", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

.hero { background: linear-gradient(135deg,#0f1f2e,#0d1117,#0f1f2e); border:1px solid #30363d; border-radius:16px; padding:1.8rem 2.5rem; margin-bottom:1.5rem; }
.hero h1 { font-size:2rem; font-weight:700; color:#e6edf3; margin:0; }
.hero p  { color:#8b949e; margin:0.3rem 0 0; font-size:0.95rem; }
.accent  { color:#00d4aa; }

.kpi-row { display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1.2rem; }
.kpi { flex:1; min-width:150px; background:#161b22; border:1px solid #30363d; border-radius:12px; padding:1.1rem 1.4rem; }
.kpi:hover { border-color:#00d4aa44; }
.kpi-label { font-size:0.7rem; color:#8b949e; text-transform:uppercase; letter-spacing:.09em; margin-bottom:.3rem; }
.kpi-val   { font-size:1.55rem; font-weight:700; font-family:'JetBrains Mono',monospace; }
.kpi-sub   { font-size:0.72rem; color:#6e7681; margin-top:.15rem; }
.green{color:#3fb950;} .red{color:#f85149;} .yellow{color:#e3b341;} .blue{color:#58a6ff;} .teal{color:#00d4aa;}

.advisor { background:linear-gradient(135deg,#0d2818,#0a1a0a); border:1px solid #00d4aa33; border-left:4px solid #00d4aa; border-radius:12px; padding:1.2rem 1.8rem; margin:.6rem 0; }
.advisor-title { color:#00d4aa; font-weight:600; margin-bottom:.6rem; font-size:.95rem; }
.advisor-body  { color:#c9d1d9; font-size:.88rem; line-height:1.75; }

.warn   { background:#1f1500; border:1px solid #e3b34133; border-left:4px solid #e3b341; border-radius:12px; padding:1rem 1.5rem; color:#e3b341; font-size:.86rem; margin:.6rem 0; }
.danger { background:#1f0d0d; border:1px solid #f8514933; border-left:4px solid #f85149; border-radius:12px; padding:1rem 1.5rem; color:#f85149; font-size:.86rem; margin:.6rem 0; }

.scenario-card { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:.8rem; }
.sec-header { font-size:1.05rem; font-weight:600; color:#e6edf3; margin:1.5rem 0 .7rem; padding-bottom:.4rem; border-bottom:1px solid #21262d; }

section[data-testid="stSidebar"] { background:#0d1117; border-right:1px solid #21262d; }
div.stButton>button { background:#00d4aa; color:#0d1117; font-weight:700; border:none; border-radius:8px; padding:.45rem 1.4rem; font-family:'Sora',sans-serif; }
div.stButton>button:hover { background:#00f0c0; box-shadow:0 4px 18px rgba(0,212,170,.3); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────
def init():
    defaults = {
        "incomes": [],
        "future_income": [],
        "debts": [],
        "strategy": "Avalanche",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()

# ─────────────────────────────────────────────────────────────────
# FINANCIAL MATH
# ─────────────────────────────────────────────────────────────────
FREQ_MULT = {"Weekly": 4.333, "Bi-Weekly": 2.167, "Monthly": 1.0, "Annual": 1/12}

DEBT_CFG = {
    "Credit Card":   {"term": 0,   "min_pct": 0.02,  "hint": "2% of balance (standard bank rule)"},
    "Car Loan":      {"term": 60,  "min_pct": 0,     "hint": "Amortized over 60-month term"},
    "Mortgage":      {"term": 360, "min_pct": 0,     "hint": "Amortized over 30-year term"},
    "Student Loan":  {"term": 120, "min_pct": 0,     "hint": "Amortized over 10-year term"},
    "Personal Loan": {"term": 48,  "min_pct": 0,     "hint": "Amortized over 4-year term"},
    "Medical Debt":  {"term": 0,   "min_pct": 0.02,  "hint": "2% of balance"},
    "Other":         {"term": 60,  "min_pct": 0,     "hint": "Amortized over 5-year term"},
}

def amortized_payment(balance, annual_rate, months):
    if months <= 0 or balance <= 0:
        return 0.0
    r = annual_rate / 100 / 12
    if r == 0:
        return balance / months
    return balance * r * (1 + r)**months / ((1 + r)**months - 1)

def calc_min(debt):
    cfg = DEBT_CFG.get(debt["type"], DEBT_CFG["Other"])
    if cfg["min_pct"] > 0:
        return max(25.0, debt["balance"] * cfg["min_pct"])
    term = debt.get("term_months") or cfg["term"]
    return amortized_payment(debt["balance"], debt["rate"], term)

def gross_monthly(incomes, month=0, future_incomes=None):
    base = sum(i["amount"] * FREQ_MULT[i["freq"]] for i in incomes)
    extra = 0.0
    if future_incomes:
        for fi in future_incomes:
            if month >= fi["start_month"]:
                extra += fi["amount"] * FREQ_MULT[fi["freq"]]
    return base + extra

def simulate(debts, incomes, future_incomes, extra_pct, strategy, max_months=600):
    if not debts:
        return [], []
    balances = [d["balance"] for d in debts]
    rates    = [d["rate"] / 100 / 12 for d in debts]
    mins     = [calc_min(d) for d in debts]

    order = sorted(range(len(debts)), key=lambda i: -debts[i]["rate"] if strategy=="Avalanche" else balances[i])

    timeline = []
    total_interest = 0.0
    payoff_events = {i: None for i in range(len(debts))}

    for month in range(1, max_months + 1):
        active = [i for i in range(len(debts)) if balances[i] > 0.01]
        if not active:
            break

        gm = gross_monthly(incomes, month, future_incomes)
        takehome = gm * 0.75

        # Update revolving minimums
        for i in active:
            if DEBT_CFG.get(debts[i]["type"], {}).get("min_pct", 0) > 0:
                mins[i] = max(25.0, balances[i] * DEBT_CFG[debts[i]["type"]]["min_pct"])

        total_min_active = sum(mins[i] for i in active)
        extra_budget = max(0.0, takehome * extra_pct)

        # Apply interest
        mi = 0.0
        for i in active:
            interest = balances[i] * rates[i]
            balances[i] += interest
            mi += interest
        total_interest += mi

        # Pay minimums
        available = total_min_active + extra_budget
        for i in active:
            pay = min(mins[i], balances[i], available)
            balances[i] -= pay
            available -= pay

        # Apply extra to target
        available = max(0.0, available)
        for i in order:
            if balances[i] > 0.01 and available > 0:
                pay = min(available, balances[i])
                balances[i] -= pay
                available -= pay

        balances = [max(0.0, b) for b in balances]

        for i in range(len(debts)):
            if payoff_events[i] is None and balances[i] < 0.01:
                payoff_events[i] = month

        timeline.append({
            "month": month,
            "balances": balances.copy(),
            "total_remaining": sum(balances),
            "total_interest": total_interest,
            "takehome": takehome,
        })

    events = []
    for i, d in enumerate(debts):
        m = payoff_events.get(i)
        if m:
            events.append({
                "name": d["name"],
                "month": m,
                "date": (date.today() + timedelta(days=m * 30.44)).strftime("%b %Y"),
                "freed_min": calc_min(d),
            })
    events.sort(key=lambda x: x["month"])
    return timeline, events

def freedom_score(debts, monthly_gross):
    if not debts or monthly_gross == 0:
        return 100
    th = monthly_gross * 0.75
    total_min = sum(calc_min(d) for d in debts)
    total_bal = sum(d["balance"] for d in debts)
    dti = total_min / th
    avg_rate = sum(d["rate"] * d["balance"] for d in debts) / max(total_bal, 1)
    score = 100 - (dti * 120) - (avg_rate * 1.8)
    return max(0, min(100, round(score)))

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💰 Income Sources")
    st.caption("Add all W-2 income streams.")

    with st.form("income_form", clear_on_submit=True):
        i_label  = st.text_input("Label", placeholder="Main Job, Side Gig…")
        i_amount = st.number_input("Gross Amount ($)", min_value=0.0, step=100.0, format="%.2f")
        i_freq   = st.selectbox("Frequency", ["Weekly","Bi-Weekly","Monthly","Annual"])
        if st.form_submit_button("➕ Add Income"):
            if i_amount > 0:
                st.session_state.incomes.append({"label": i_label or "Income", "amount": i_amount, "freq": i_freq})
                st.rerun()
            else:
                st.error("Amount must be > 0")

    for idx, inc in enumerate(st.session_state.incomes):
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{inc['label']}** — ${inc['amount']:,.0f} / {inc['freq']}")
        if c2.button("✕", key=f"di_{idx}"):
            st.session_state.incomes.pop(idx); st.rerun()

    st.markdown("---")
    st.markdown("## 📈 Expected Future Income")
    st.caption("Raise, bonus, new job? Add it so your timeline is realistic.")

    with st.form("fi_form", clear_on_submit=True):
        fi_label   = st.text_input("Label", placeholder="Annual Raise, Year-End Bonus…")
        fi_amount  = st.number_input("Additional Gross ($)", min_value=0.0, step=100.0, format="%.2f")
        fi_freq    = st.selectbox("Frequency", ["Weekly","Bi-Weekly","Monthly","Annual"], key="fif")
        fi_months  = st.number_input("Starts in (months)", min_value=1, max_value=120, value=6, step=1)
        if st.form_submit_button("➕ Add Future Income"):
            if fi_amount > 0:
                st.session_state.future_income.append({
                    "label": fi_label or "Raise", "amount": fi_amount,
                    "freq": fi_freq, "start_month": int(fi_months),
                })
                st.rerun()

    for idx, fi in enumerate(st.session_state.future_income):
        c1, c2 = st.columns([5,1])
        c1.markdown(f"**{fi['label']}** +${fi['amount']:,.0f}/{fi['freq']} in {fi['start_month']} mo")
        if c2.button("✕", key=f"dfi_{idx}"):
            st.session_state.future_income.pop(idx); st.rerun()

    st.markdown("---")
    st.markdown("## 🏦 Add Debt")
    st.caption("Just enter balance, type, and APR. We calculate the minimum.")

    with st.form("debt_form", clear_on_submit=True):
        d_type    = st.selectbox("Debt Type", list(DEBT_CFG.keys()))
        d_name    = st.text_input("Name / Label", placeholder="Chase Sapphire, Toyota Camry…")
        d_balance = st.number_input("Current Balance ($)", min_value=0.0, step=100.0, format="%.2f")
        d_rate    = st.number_input("Interest Rate (APR %)", min_value=0.0, max_value=35.0, value=18.0, step=0.25, format="%.2f")
        d_term    = None
        if d_type not in ["Credit Card", "Medical Debt"]:
            default_term = DEBT_CFG[d_type]["term"]
            d_term = st.number_input(f"Remaining Term (months)", min_value=1, max_value=480, value=default_term, step=12)
        st.caption(f"ℹ️ {DEBT_CFG[d_type]['hint']}")
        if st.form_submit_button("➕ Add Debt"):
            if d_balance > 0:
                entry = {"name": d_name or d_type, "type": d_type, "balance": d_balance, "rate": d_rate, "term_months": d_term}
                min_p = calc_min(entry)
                st.session_state.debts.append(entry)
                st.success(f"Added! Auto min payment: ${min_p:,.0f}/mo")
                st.rerun()
            else:
                st.error("Balance must be > 0")

    st.markdown("---")
    st.markdown("## ⚙️ Strategy")
    st.session_state.strategy = st.radio(
        "Payoff Method", ["Avalanche", "Snowball"],
        captions=["Highest APR first — saves most money", "Lowest balance first — quick wins"]
    )

# ─────────────────────────────────────────────────────────────────
# COMPUTED VALUES
# ─────────────────────────────────────────────────────────────────
debts   = st.session_state.debts
incomes = st.session_state.incomes
future  = st.session_state.future_income
strategy = st.session_state.strategy

gross_m    = gross_monthly(incomes)
takehome_m = gross_m * 0.75
total_bal  = sum(d["balance"] for d in debts)
total_min  = sum(calc_min(d) for d in debts)
avg_rate   = (sum(d["rate"]*d["balance"] for d in debts) / total_bal) if total_bal > 0 else 0
dti        = total_min / takehome_m if takehome_m > 0 else 0
score      = freedom_score(debts, gross_m)
disposable = max(0, takehome_m - total_min)

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class='hero'>
  <h1>💳 <span class='accent'>DebtFree</span> Advisor</h1>
  <p>Smart W-2 debt payoff platform — just enter your numbers, we handle all the financial math</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────
sc = "green" if score>=70 else ("yellow" if score>=40 else "red")
dc = "green" if dti<.20 else ("yellow" if dti<.36 else "red")

st.markdown(f"""
<div class='kpi-row'>
  <div class='kpi'><div class='kpi-label'>Monthly Take-Home</div>
    <div class='kpi-val green'>${takehome_m:,.0f}</div><div class='kpi-sub'>After ~25% W-2 taxes</div></div>
  <div class='kpi'><div class='kpi-label'>Total Debt</div>
    <div class='kpi-val red'>${total_bal:,.0f}</div><div class='kpi-sub'>{len(debts)} account(s)</div></div>
  <div class='kpi'><div class='kpi-label'>Auto Min Payments</div>
    <div class='kpi-val yellow'>${total_min:,.0f}/mo</div><div class='kpi-sub'>Calculated for you</div></div>
  <div class='kpi'><div class='kpi-label'>Debt-to-Income</div>
    <div class='kpi-val {dc}'>{dti:.0%}</div>
    <div class='kpi-sub'>{"✅ Healthy" if dti<.20 else "⚠️ Elevated" if dti<.36 else "🚨 High Risk"}</div></div>
  <div class='kpi'><div class='kpi-label'>Avg Interest Rate</div>
    <div class='kpi-val {"red" if avg_rate>15 else "yellow" if avg_rate>8 else "green"}'>{avg_rate:.1f}%</div>
    <div class='kpi-sub'>Weighted by balance</div></div>
  <div class='kpi'><div class='kpi-label'>Freedom Score™</div>
    <div class='kpi-val {sc}'>{score}/100</div>
    <div class='kpi-sub'>{"Excellent" if score>=80 else "Good" if score>=60 else "Fair" if score>=40 else "At Risk"}</div></div>
  <div class='kpi'><div class='kpi-label'>Free Cash / mo</div>
    <div class='kpi-val teal'>${disposable:,.0f}</div><div class='kpi-sub'>After all minimums</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DEBT TABLE
# ─────────────────────────────────────────────────────────────────
if debts:
    st.markdown("<div class='sec-header'>📋 Your Debts — Auto-Calculated Payments</div>", unsafe_allow_html=True)
    ICONS = {"Credit Card":"💳","Car Loan":"🚗","Mortgage":"🏠","Student Loan":"🎓","Personal Loan":"🤝","Medical Debt":"🏥","Other":"📄"}
    rows = []
    for d in debts:
        min_p = calc_min(d)
        monthly_int = d["balance"] * d["rate"] / 100 / 12
        rows.append({
            "": ICONS.get(d["type"],"📄"),
            "Name": d["name"],
            "Type": d["type"],
            "Balance": f"${d['balance']:,.0f}",
            "APR": f"{d['rate']}%",
            "Auto Min/mo": f"${min_p:,.0f}",
            "Interest/mo": f"${monthly_int:,.0f}",
            "Principal/mo": f"${max(0,min_p-monthly_int):,.0f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    to_del = None
    cols = st.columns(min(len(debts), 5))
    for i, d in enumerate(debts):
        with cols[i % 5]:
            if st.button(f"Remove {d['name']}", key=f"deld_{i}"):
                to_del = i
    if to_del is not None:
        st.session_state.debts.pop(to_del); st.rerun()

# ─────────────────────────────────────────────────────────────────
# SCENARIOS
# ─────────────────────────────────────────────────────────────────
if debts and incomes:
    st.markdown("<div class='sec-header'>🎯 Smart Payoff Scenarios — Your Three Paths</div>", unsafe_allow_html=True)
    st.caption("The advisor automatically calculates all three scenarios from your income. No manual inputs needed.")

    SCENARIOS = [
        {"label": "📉 Minimum Only",          "pct": 0.0,  "color": "#f85149", "desc": "Pay only the required minimums. Worst case — shows you what inaction costs."},
        {"label": "⚖️ Balanced (Recommended)", "pct": 0.20, "color": "#e3b341", "desc": "20% of take-home above minimums. Strong progress without straining your lifestyle."},
        {"label": "🚀 Aggressive",             "pct": 0.35, "color": "#3fb950", "desc": "35% of take-home above minimums. Maximum speed to debt freedom."},
    ]

    fig = go.Figure()
    results = []

    for sc in SCENARIOS:
        tl, events = simulate(debts, incomes, future, sc["pct"], strategy)
        if tl:
            extra_mo = takehome_m * sc["pct"]
            fig.add_trace(go.Scatter(
                x=[t["month"] for t in tl],
                y=[t["total_remaining"] for t in tl],
                name=sc["label"],
                line=dict(color=sc["color"], width=2.5),
                hovertemplate=f'<b>{sc["label"]}</b><br>Month %{{x}}: $%{{y:,.0f}} left<extra></extra>'
            ))
            results.append({"sc": sc, "tl": tl, "events": events,
                             "months": tl[-1]["month"], "interest": tl[-1]["total_interest"],
                             "extra_mo": extra_mo})

    # Future income markers
    for fi in future:
        fig.add_vline(x=fi["start_month"], line_dash="dot", line_color="#58a6ff",
            annotation_text=f"📈 {fi['label']}", annotation_font_color="#58a6ff",
            annotation_position="top left")

    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        font=dict(color="#8b949e", family="Sora"),
        xaxis=dict(title="Month", gridcolor="#21262d", color="#8b949e", zerolinecolor="#21262d"),
        yaxis=dict(title="Total Debt Remaining ($)", gridcolor="#21262d", color="#8b949e", tickprefix="$", zerolinecolor="#21262d"),
        legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
        title=dict(text="📉 Three Scenarios — Choose Your Path to Debt Freedom", font=dict(color="#e6edf3", size=16)),
        height=430, margin=dict(l=20, r=20, t=60, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Scenario summary cards
    cols = st.columns(len(results))
    for col, res in zip(cols, results):
        sc = res["sc"]
        payoff_date = (date.today() + timedelta(days=res["months"]*30.44)).strftime("%b %Y")
        with col:
            st.markdown(f"""
            <div class='scenario-card'>
              <div style='font-weight:600;font-size:1rem;color:{sc["color"]};margin-bottom:.5rem;'>{sc["label"]}</div>
              <div style='font-size:1.4rem;font-weight:700;font-family:JetBrains Mono,monospace;color:{sc["color"]};'>{payoff_date}</div>
              <div style='font-size:.82rem;color:#8b949e;margin-top:.5rem;line-height:1.6;'>
                <b style='color:#e6edf3;'>{res["months"]} months</b> ({res["months"]/12:.1f} yrs)<br>
                Interest paid: <b style='color:#f85149;'>${res["interest"]:,.0f}</b><br>
                Extra/mo: <b style='color:#3fb950;'>${res["extra_mo"]:,.0f}</b><br>
                <span style='color:#6e7681;font-size:.74rem;'>{sc["desc"]}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # Intelligence summary
    if len(results) >= 2:
        saved_int   = results[0]["interest"] - results[-1]["interest"]
        saved_months = results[0]["months"] - results[-1]["months"]
        st.markdown(f"""
        <div class='advisor'>
          <div class='advisor-title'>🧠 What the Numbers Tell You</div>
          <div class='advisor-body'>
            Going from <b>Minimum Only → Aggressive</b> saves you
            <b style='color:#3fb950;'>${saved_int:,.0f} in total interest</b> and
            <b style='color:#3fb950;'>{saved_months} months ({saved_months/12:.1f} years)</b> of your life.
            The extra ${results[-1]["extra_mo"]:,.0f}/mo you'd put toward debt is the single highest-return
            move you can make — a guaranteed <b>{avg_rate:.1f}% return</b> (your average APR) with zero market risk.
            No stock or investment reliably beats paying off {avg_rate:.1f}% debt.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── MILESTONES ──────────────────────────────────────────────
    if len(results) >= 2:
        st.markdown("<div class='sec-header'>🏁 Payoff Milestones — Balanced Scenario</div>", unsafe_allow_html=True)
        for ev in results[1]["events"]:
            st.markdown(f"""
            <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;
                        padding:.85rem 1.3rem;margin-bottom:.5rem;
                        display:flex;justify-content:space-between;align-items:center;'>
              <div>
                <b style='color:#e6edf3;'>{ev["name"]}</b>
                <span style='color:#8b949e;font-size:.8rem;'> — paid off month {ev["month"]}</span>
              </div>
              <div style='text-align:right;'>
                <div style='color:#00d4aa;font-weight:700;'>{ev["date"]}</div>
                <div style='color:#3fb950;font-size:.78rem;'>+${ev["freed_min"]:,.0f}/mo freed up 🎉</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── PER-DEBT CHART ──────────────────────────────────────────
    if len(results) >= 2:
        st.markdown("<div class='sec-header'>📊 Individual Debt Balances — Balanced Scenario</div>", unsafe_allow_html=True)
        tl = results[1]["tl"]
        COLORS = ["#58a6ff","#f85149","#e3b341","#a371f7","#3fb950","#ffa657","#00d4aa","#ec6547"]
        fig2 = go.Figure()
        for idx, d in enumerate(debts):
            fig2.add_trace(go.Scatter(
                x=[t["month"] for t in tl],
                y=[t["balances"][idx] for t in tl],
                name=d["name"],
                line=dict(color=COLORS[idx % len(COLORS)], width=2),
                hovertemplate=f'{d["name"]} Month %{{x}}: $%{{y:,.0f}}<extra></extra>'
            ))
        fig2.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font=dict(color="#8b949e", family="Sora"),
            xaxis=dict(title="Month", gridcolor="#21262d", color="#8b949e"),
            yaxis=dict(title="Balance ($)", gridcolor="#21262d", color="#8b949e", tickprefix="$"),
            legend=dict(bgcolor="#161b22", bordercolor="#30363d", borderwidth=1),
            title=dict(text="Each Debt's Balance Over Time", font=dict(color="#e6edf3", size=15)),
            height=340, margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── ADVISOR INSIGHTS ────────────────────────────────────────
    st.markdown("<div class='sec-header'>🧠 Personalized Financial Advice</div>", unsafe_allow_html=True)

    high_rate = [d for d in debts if d["rate"] >= 20]
    cc_debts  = [d for d in debts if d["type"] == "Credit Card"]
    mortgage  = [d for d in debts if d["type"] == "Mortgage"]

    if dti > 0.43:
        st.markdown(f"<div class='danger'>🚨 <b>Critical DTI at {dti:.0%}:</b> Minimum payments consume a dangerous share of your take-home. This disqualifies you from most mortgages. You need to eliminate at least one debt immediately to free up cash flow. Follow the Aggressive scenario.</div>", unsafe_allow_html=True)
    elif dti > 0.28:
        st.markdown(f"<div class='warn'>⚠️ <b>Elevated DTI at {dti:.0%}:</b> You're in the caution zone. Lenders want to see below 28% for housing costs and 36% total. Avoid new debt and direct every spare dollar to payoff.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='advisor'><div class='advisor-title'>✅ Healthy DTI at {dti:.0%}</div><div class='advisor-body'>You're in a manageable position. Your minimum payments don't dominate your budget — which means you have real power to accelerate payoff with extra payments. Use that leverage.</div></div>", unsafe_allow_html=True)

    if high_rate:
        names = ", ".join(d["name"] for d in high_rate)
        annual_cost = sum(d["balance"] * d["rate"] / 100 for d in high_rate)
        st.markdown(f"""<div class='advisor'><div class='advisor-title'>🔥 High-Rate Debt Alert</div>
        <div class='advisor-body'><b>{names}</b> {'are' if len(high_rate)>1 else 'is'} costing you
        <b style='color:#f85149;'>${annual_cost:,.0f}/year</b> in interest alone. This should receive every
        extra dollar above your other minimums. Avalanche strategy is strongly recommended when high-rate debt exists.</div></div>""", unsafe_allow_html=True)

    if cc_debts:
        cc_bal = sum(d["balance"] for d in cc_debts)
        cc_int = sum(d["balance"] * d["rate"] / 100 for d in cc_debts)
        st.markdown(f"""<div class='advisor'><div class='advisor-title'>💳 Balance Transfer Opportunity</div>
        <div class='advisor-body'>Your credit card balances total <b>${cc_bal:,.0f}</b>, costing
        <b style='color:#f85149;'>${cc_int:,.0f}/year</b> in interest. A <b>0% APR balance transfer card</b>
        (promo periods: 12–21 months) could eliminate that interest entirely while you pay down the principal.
        Even with a 3% transfer fee (${cc_bal*0.03:,.0f}), you'd save significantly if you pay aggressively
        during the promo window.</div></div>""", unsafe_allow_html=True)

    if mortgage:
        m = mortgage[0]
        effective_rate = m["rate"] * (1 - 0.22)
        st.markdown(f"""<div class='advisor'><div class='advisor-title'>🏠 Mortgage Tax Strategy (W-2 Specific)</div>
        <div class='advisor-body'>As a W-2 employee, mortgage interest may be <b>tax-deductible</b> if you itemize.
        At a 22% tax bracket, your {m["rate"]:.1f}% mortgage has an effective after-tax rate of ~<b>{effective_rate:.1f}%</b>.
        This means almost any other debt (credit cards, car loans) should be paid off <i>before</i> making extra mortgage payments.
        Don't over-pay your cheapest debt while expensive debt remains.</div></div>""", unsafe_allow_html=True)

    if future:
        total_raise_m = sum(fi["amount"] * FREQ_MULT[fi["freq"]] for fi in future)
        earliest = min(fi["start_month"] for fi in future)
        st.markdown(f"""<div class='advisor'><div class='advisor-title'>📈 Your Future Income Is Already Modeled</div>
        <div class='advisor-body'>Your upcoming income increase of <b style='color:#3fb950;'>${total_raise_m:,.0f}/mo</b>
        starting in month {earliest} is built into the timeline above (watch for the blue dotted line on the chart).
        <b>Critical rule:</b> When the raise arrives, resist lifestyle inflation. Route 100% of the increase to debt first.
        At your average APR of {avg_rate:.1f}%, that ${total_raise_m:,.0f}/mo saves you
        <b>${total_raise_m * 12 * avg_rate / 100:,.0f}/year</b> in interest.</div></div>""", unsafe_allow_html=True)

    with st.expander("⚡ 10 Proven Ways to Pay Off Debt Faster (W-2 Employee Edition)", expanded=False):
        st.markdown("""
**1. 🎯 Use Your Tax Refund as a Lump Sum**
The average W-2 refund is $3,000+. Direct 100% straight to your highest-rate debt every February/March.

**2. 📅 Switch to Bi-Weekly Payments**
Pay half your monthly payment every 2 weeks. You'll make 13 full payments/year instead of 12 — one free extra payment annually, zero extra budget required.

**3. 💼 Route 100% of Raises to Debt**
When you get a raise, you weren't living on that money before. Direct every dollar of the increase to debt until you're free — then lifestyle-inflate responsibly.

**4. 💳 0% Balance Transfer for Credit Cards**
Move high-rate credit card debt to a 0% promotional card (12–21 months). Even with a 3–5% fee, you'll save thousands if you pay aggressively during the window.

**5. 🏠 Refinance Your Mortgage**
A 1% rate reduction on a $300k mortgage saves ~$2,400/year. If you haven't refinanced in 2+ years, get a quote — the break-even on closing costs is often under 2 years.

**6. 📊 Adjust Your W-4 Withholding**
A large tax refund means you gave the IRS an interest-free loan all year. Adjust your W-4 to break even → get that money monthly → apply it to debt immediately.

**7. 🛍️ Sell Idle Assets**
Old car, equipment, furniture, electronics. Even $500 applied to a 24% credit card saves $120/year in interest — permanently and immediately.

**8. 🎁 Apply All Non-Salary Income to Debt**
Bonuses, overtime, side gigs, gifts. Treat these as windfalls, not income — 100% goes to debt. You weren't budgeting on it anyway.

**9. 💡 The Snowball Reinvestment Rule**
When a debt is paid off, take its full payment amount and add it to the next debt. Your payment grows with every win — this is the compounding effect of the debt payoff strategy.

**10. 🏆 Automate Everything**
Set up automatic extra payments the day after your paycheck hits. Willpower is finite — automation is permanent. What leaves your account automatically never gets spent.
        """)

# ─────────────────────────────────────────────────────────────────
# EMPTY STATES
# ─────────────────────────────────────────────────────────────────
elif not incomes:
    st.markdown("""
    <div style='text-align:center;padding:5rem 2rem;'>
      <div style='font-size:3.5rem;'>👈</div>
      <div style='font-size:1.4rem;font-weight:600;color:#e6edf3;margin-top:1rem;'>Start with your income</div>
      <div style='color:#8b949e;margin-top:.5rem;max-width:460px;margin-left:auto;margin-right:auto;'>
        Add your W-2 income in the left sidebar. Then add your debts — balance, type, and APR only.
        The platform handles all the financial math and shows you exactly when you'll be debt-free.
      </div>
    </div>
    """, unsafe_allow_html=True)
elif not debts:
    st.markdown("""
    <div style='text-align:center;padding:5rem 2rem;'>
      <div style='font-size:3.5rem;'>🏦</div>
      <div style='font-size:1.4rem;font-weight:600;color:#e6edf3;margin-top:1rem;'>Now add your debts</div>
      <div style='color:#8b949e;margin-top:.5rem;max-width:460px;margin-left:auto;margin-right:auto;'>
        Add each debt on the left — just the balance, type, and APR.
        No minimum payment needed. We calculate it for you based on industry-standard rules.
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<div style='text-align:center;color:#484f58;font-size:.75rem;'>DebtFree Advisor v2 • Informational only • Not a substitute for licensed financial advice</div>", unsafe_allow_html=True)
