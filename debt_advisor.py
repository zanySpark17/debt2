"""
DebtFree Advisor v3
- Full budget tracker with 50/30/20 rule
- Auto-calculated debt payments
- 3 smart payoff scenarios
- Groq AI chat advisor (knows your full financial picture)

Run:  streamlit run debt_advisor.py
Deps: pip install streamlit plotly pandas groq
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import math
import json

# ── Groq (optional — works without it too) ──────────────────────
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DebtFree Advisor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family:'Sora',sans-serif; }

/* ── layout ── */
.hero { background:linear-gradient(135deg,#0f1f2e,#0d1117,#0f1f2e);
        border:1px solid #30363d; border-radius:16px;
        padding:1.8rem 2.5rem; margin-bottom:1.5rem; }
.hero h1 { font-size:2rem; font-weight:700; color:#e6edf3; margin:0; }
.hero p  { color:#8b949e; margin:.3rem 0 0; font-size:.93rem; }
.accent  { color:#00d4aa; }

/* ── kpi cards ── */
.kpi-row { display:flex; gap:.9rem; flex-wrap:wrap; margin-bottom:1.2rem; }
.kpi { flex:1; min-width:140px; background:#161b22;
       border:1px solid #30363d; border-radius:12px; padding:1rem 1.3rem; }
.kpi-label { font-size:.68rem; color:#8b949e; text-transform:uppercase;
             letter-spacing:.09em; margin-bottom:.25rem; }
.kpi-val   { font-size:1.45rem; font-weight:700; font-family:'JetBrains Mono',monospace; }
.kpi-sub   { font-size:.7rem; color:#6e7681; margin-top:.12rem; }
.green{color:#3fb950;} .red{color:#f85149;}
.yellow{color:#e3b341;} .blue{color:#58a6ff;} .teal{color:#00d4aa;}

/* ── advisor / info boxes ── */
.advisor { background:linear-gradient(135deg,#0d2818,#0a1a0a);
           border:1px solid #00d4aa33; border-left:4px solid #00d4aa;
           border-radius:12px; padding:1.1rem 1.6rem; margin:.5rem 0; }
.advisor-title { color:#00d4aa; font-weight:600; margin-bottom:.5rem; font-size:.92rem; }
.advisor-body  { color:#c9d1d9; font-size:.86rem; line-height:1.75; }

.warn   { background:#1f1500; border:1px solid #e3b34133;
          border-left:4px solid #e3b341; border-radius:12px;
          padding:.9rem 1.4rem; color:#e3b341; font-size:.84rem; margin:.5rem 0; }
.danger { background:#1f0d0d; border:1px solid #f8514933;
          border-left:4px solid #f85149; border-radius:12px;
          padding:.9rem 1.4rem; color:#f85149; font-size:.84rem; margin:.5rem 0; }
.success-box { background:#0d2010; border:1px solid #3fb95033;
               border-left:4px solid #3fb950; border-radius:12px;
               padding:.9rem 1.4rem; color:#3fb950; font-size:.84rem; margin:.5rem 0; }

/* ── scenario cards ── */
.sc-card { background:#161b22; border:1px solid #30363d; border-radius:12px;
           padding:1.1rem 1.4rem; margin-bottom:.7rem; }

/* ── budget bar ── */
.budget-bar-wrap { background:#21262d; border-radius:8px; height:18px;
                   overflow:hidden; margin:.4rem 0; }
.budget-bar { height:100%; border-radius:8px; transition:width .4s; }

/* ── chat ── */
.chat-msg-user { background:#1c2d3a; border:1px solid #30363d;
                 border-radius:12px 12px 4px 12px; padding:.75rem 1rem;
                 margin:.4rem 0; color:#e6edf3; font-size:.88rem;
                 max-width:80%; margin-left:auto; }
.chat-msg-ai   { background:#0d2818; border:1px solid #00d4aa22;
                 border-radius:12px 12px 12px 4px; padding:.75rem 1rem;
                 margin:.4rem 0; color:#c9d1d9; font-size:.88rem;
                 max-width:90%; }
.chat-label-user { text-align:right; font-size:.68rem; color:#8b949e;
                   margin-bottom:.1rem; }
.chat-label-ai   { font-size:.68rem; color:#00d4aa; margin-bottom:.1rem; }

.sec-header { font-size:1.03rem; font-weight:600; color:#e6edf3;
              margin:1.4rem 0 .65rem; padding-bottom:.4rem;
              border-bottom:1px solid #21262d; }

section[data-testid="stSidebar"] { background:#0d1117; border-right:1px solid #21262d; }
div.stButton>button { background:#00d4aa; color:#0d1117; font-weight:700;
                      border:none; border-radius:8px; padding:.42rem 1.3rem;
                      font-family:'Sora',sans-serif; }
div.stButton>button:hover { background:#00f0c0; box-shadow:0 4px 16px rgba(0,212,170,.3); }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════
def init():
    defs = {
        "incomes": [],
        "future_income": [],
        "debts": [],
        "expenses": {
            "Housing":       {"amount": 0.0, "category": "needs"},
            "Transportation":{"amount": 0.0, "category": "needs"},
            "Groceries":     {"amount": 0.0, "category": "needs"},
            "Utilities":     {"amount": 0.0, "category": "needs"},
            "Insurance":     {"amount": 0.0, "category": "needs"},
            "Healthcare":    {"amount": 0.0, "category": "needs"},
            "Childcare":     {"amount": 0.0, "category": "needs"},
            "Dining Out":    {"amount": 0.0, "category": "wants"},
            "Entertainment": {"amount": 0.0, "category": "wants"},
            "Shopping":      {"amount": 0.0, "category": "wants"},
            "Subscriptions": {"amount": 0.0, "category": "wants"},
            "Personal Care": {"amount": 0.0, "category": "wants"},
            "Travel":        {"amount": 0.0, "category": "wants"},
            "Emergency Fund":{"amount": 0.0, "category": "savings"},
            "Retirement 401k":{"amount":0.0, "category": "savings"},
            "Other Savings": {"amount": 0.0, "category": "savings"},
        },
        "strategy": "Avalanche",
        "groq_api_key": "",
        "chat_history": [],
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v
init()


# ════════════════════════════════════════════════════════════════
# FINANCIAL MATH
# ════════════════════════════════════════════════════════════════
FREQ_MULT = {"Weekly":4.333,"Bi-Weekly":2.167,"Monthly":1.0,"Annual":1/12}

DEBT_CFG = {
    "Credit Card":   {"term":0,   "min_pct":0.02, "hint":"2% of balance (standard bank rule)"},
    "Car Loan":      {"term":60,  "min_pct":0,    "hint":"Amortized over your remaining term"},
    "Mortgage":      {"term":360, "min_pct":0,    "hint":"Amortized over 30-year term"},
    "Student Loan":  {"term":120, "min_pct":0,    "hint":"Amortized over 10-year term"},
    "Personal Loan": {"term":48,  "min_pct":0,    "hint":"Amortized over 4-year term"},
    "Medical Debt":  {"term":0,   "min_pct":0.02, "hint":"2% of balance"},
    "Other":         {"term":60,  "min_pct":0,    "hint":"Amortized over 5-year term"},
}

def amortize(balance, apr, months):
    if months <= 0 or balance <= 0: return 0.0
    r = apr / 100 / 12
    if r == 0: return balance / months
    return balance * r * (1+r)**months / ((1+r)**months - 1)

def calc_min(debt):
    cfg = DEBT_CFG.get(debt["type"], DEBT_CFG["Other"])
    if cfg["min_pct"] > 0:
        return max(25.0, debt["balance"] * cfg["min_pct"])
    term = debt.get("term_months") or cfg["term"]
    return amortize(debt["balance"], debt["rate"], term)

def gross_monthly(incomes, month=0, future_inc=None):
    base = sum(i["amount"] * FREQ_MULT[i["freq"]] for i in incomes)
    bonus = sum(
        fi["amount"] * FREQ_MULT[fi["freq"]]
        for fi in (future_inc or [])
        if month >= fi["start_month"]
    )
    return base + bonus

def total_expenses_monthly():
    return sum(v["amount"] for v in st.session_state.expenses.values())

def true_disposable(gross_m):
    """Take-home minus ALL living expenses minus debt minimums."""
    th = gross_m * 0.75
    exp = total_expenses_monthly()
    mins = sum(calc_min(d) for d in st.session_state.debts)
    return th - exp - mins

def simulate(debts, incomes, future_inc, extra_pct, strategy, max_months=600):
    if not debts: return [], []
    balances = [d["balance"] for d in debts]
    rates    = [d["rate"]/100/12 for d in debts]
    mins     = [calc_min(d) for d in debts]
    order = sorted(range(len(debts)),
                   key=lambda i: -debts[i]["rate"] if strategy=="Avalanche" else balances[i])

    timeline, total_int = [], 0.0
    payoff_ev = {i: None for i in range(len(debts))}

    for month in range(1, max_months+1):
        active = [i for i in range(len(debts)) if balances[i] > 0.01]
        if not active: break

        gm = gross_monthly(incomes, month, future_inc)
        th = gm * 0.75
        exp = total_expenses_monthly()
        disposable = max(0.0, th - exp)

        # Update revolving mins
        for i in active:
            if DEBT_CFG.get(debts[i]["type"],{}).get("min_pct",0) > 0:
                mins[i] = max(25.0, balances[i]*DEBT_CFG[debts[i]["type"]]["min_pct"])

        total_min_active = sum(mins[i] for i in active)
        extra = max(0.0, (disposable - total_min_active) * extra_pct)
        available = min(disposable, total_min_active + extra)

        # Interest
        mi = 0.0
        for i in active:
            interest = balances[i] * rates[i]
            balances[i] += interest
            mi += interest
        total_int += mi

        # Minimums
        for i in active:
            pay = min(mins[i], balances[i], available)
            balances[i] -= pay
            available -= pay

        # Extra to target
        available = max(0.0, available)
        for i in order:
            if balances[i] > 0.01 and available > 0:
                pay = min(available, balances[i])
                balances[i] -= pay
                available -= pay

        balances = [max(0.0, b) for b in balances]
        for i in range(len(debts)):
            if payoff_ev[i] is None and balances[i] < 0.01:
                payoff_ev[i] = month

        timeline.append({
            "month": month,
            "balances": balances.copy(),
            "total_remaining": sum(balances),
            "total_interest": total_int,
            "takehome": th,
            "expenses": exp,
        })

    events = []
    for i, d in enumerate(debts):
        m = payoff_ev.get(i)
        if m:
            events.append({
                "name": d["name"], "month": m,
                "date": (date.today()+timedelta(days=m*30.44)).strftime("%b %Y"),
                "freed_min": calc_min(d),
            })
    return timeline, sorted(events, key=lambda x: x["month"])

def freedom_score(debts, gross_m):
    if not debts or gross_m == 0: return 100
    th = gross_m * 0.75
    exp = total_expenses_monthly()
    total_min = sum(calc_min(d) for d in debts)
    total_bal = sum(d["balance"] for d in debts)
    dti = total_min / th if th > 0 else 1
    expense_ratio = exp / th if th > 0 else 1
    avg_rate = sum(d["rate"]*d["balance"] for d in debts) / max(total_bal,1)
    score = 100 - (dti*80) - (expense_ratio*40) - (avg_rate*1.5)
    return max(0, min(100, round(score)))


# ════════════════════════════════════════════════════════════════
# GROQ AI HELPERS
# ════════════════════════════════════════════════════════════════
def build_financial_context():
    debts   = st.session_state.debts
    incomes = st.session_state.incomes
    gm      = gross_monthly(incomes)
    th      = gm * 0.75
    exp     = total_expenses_monthly()
    mins    = sum(calc_min(d) for d in debts)
    disposable = max(0, th - exp - mins)
    avg_rate = (sum(d["rate"]*d["balance"] for d in debts)/sum(d["balance"] for d in debts)) if debts else 0

    exp_breakdown = {k: v["amount"] for k, v in st.session_state.expenses.items() if v["amount"] > 0}
    debt_summary  = [{"name":d["name"],"type":d["type"],"balance":d["balance"],
                      "apr":d["rate"],"min_payment":round(calc_min(d),2)} for d in debts]

    return f"""
You are a smart, empathetic personal financial advisor embedded in a debt payoff app.
The user is a W-2 employee. Here is their COMPLETE financial picture:

INCOME:
- Monthly gross: ${gm:,.0f}
- Monthly take-home (after ~25% W-2 taxes): ${th:,.0f}

MONTHLY EXPENSES: ${exp:,.0f} total
{json.dumps(exp_breakdown, indent=2)}

DEBTS: {json.dumps(debt_summary, indent=2)}
- Total debt: ${sum(d["balance"] for d in debts):,.0f}
- Total min payments: ${mins:,.0f}/mo
- Average APR: {avg_rate:.1f}%

BUDGET HEALTH:
- True disposable income (after taxes + expenses + minimums): ${disposable:,.0f}/mo
- Debt-to-income ratio: {mins/th*100 if th>0 else 0:.1f}%
- Payoff strategy selected: {st.session_state.strategy}
- Freedom Score: {freedom_score(debts, gm)}/100

INSTRUCTIONS:
- Be direct, specific, and use the user's actual numbers.
- Give actionable advice. Don't be vague.
- If they ask about payoff strategies, reference their specific debts by name.
- Keep answers concise (3-6 sentences unless a detailed breakdown is needed).
- Use simple language — no jargon unless asked.
- You can use bullet points for lists but keep prose conversational.
- Never make up numbers not in the context above.
"""

def ask_groq(user_message, api_key):
    if not GROQ_AVAILABLE:
        return "⚠️ Groq library not installed. Run: `pip install groq` then restart."
    try:
        client = Groq(api_key=api_key)
        messages = [{"role": "system", "content": build_financial_context()}]
        for msg in st.session_state.chat_history[-10:]:  # last 10 turns for context
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Groq error: {str(e)}"


# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── GROQ API KEY ─────────────────────────────────────────────
    st.markdown("## 🤖 AI Advisor Setup")
    api_key_input = st.text_input(
        "Groq API Key", type="password",
        value=st.session_state.groq_api_key,
        placeholder="gsk_...",
        help="Free at console.groq.com — takes 2 min to get"
    )
    if api_key_input != st.session_state.groq_api_key:
        st.session_state.groq_api_key = api_key_input
    if st.session_state.groq_api_key:
        st.success("✅ AI Advisor ready")
    else:
        st.caption("Get free key → [console.groq.com](https://console.groq.com)")

    st.markdown("---")

    # ── INCOME ───────────────────────────────────────────────────
    st.markdown("## 💰 Income")
    with st.form("inc_form", clear_on_submit=True):
        il = st.text_input("Label", placeholder="Main Job, Side Gig…")
        ia = st.number_input("Gross Amount ($)", min_value=0.0, step=100.0, format="%.2f")
        if_ = st.selectbox("Frequency", ["Weekly","Bi-Weekly","Monthly","Annual"])
        if st.form_submit_button("➕ Add Income"):
            if ia > 0:
                st.session_state.incomes.append({"label":il or "Income","amount":ia,"freq":if_})
                st.rerun()

    for idx, inc in enumerate(st.session_state.incomes):
        c1,c2 = st.columns([5,1])
        c1.caption(f"**{inc['label']}** ${inc['amount']:,.0f}/{inc['freq']}")
        if c2.button("✕",key=f"di{idx}"):
            st.session_state.incomes.pop(idx); st.rerun()

    st.markdown("---")

    # ── FUTURE INCOME ─────────────────────────────────────────────
    st.markdown("## 📈 Future Income")
    st.caption("Raise, bonus, new job?")
    with st.form("fi_form", clear_on_submit=True):
        fl = st.text_input("Label", placeholder="Annual Raise…")
        fa = st.number_input("Additional Gross ($)", min_value=0.0, step=100.0, format="%.2f")
        ff = st.selectbox("Frequency", ["Weekly","Bi-Weekly","Monthly","Annual"], key="fff")
        fm = st.number_input("Starts in (months)", min_value=1, max_value=120, value=6, step=1)
        if st.form_submit_button("➕ Add"):
            if fa > 0:
                st.session_state.future_income.append(
                    {"label":fl or "Raise","amount":fa,"freq":ff,"start_month":int(fm)})
                st.rerun()

    for idx, fi in enumerate(st.session_state.future_income):
        c1,c2 = st.columns([5,1])
        c1.caption(f"**{fi['label']}** +${fi['amount']:,.0f} in {fi['start_month']}mo")
        if c2.button("✕",key=f"dfi{idx}"):
            st.session_state.future_income.pop(idx); st.rerun()

    st.markdown("---")

    # ── DEBTS ─────────────────────────────────────────────────────
    st.markdown("## 🏦 Add Debt")
    st.caption("Balance + type + APR only. We calc the minimum.")
    with st.form("debt_form", clear_on_submit=True):
        dt = st.selectbox("Type", list(DEBT_CFG.keys()))
        dn = st.text_input("Name", placeholder="Chase Sapphire, Camry…")
        db = st.number_input("Balance ($)", min_value=0.0, step=100.0, format="%.2f")
        dr = st.number_input("APR (%)", min_value=0.0, max_value=35.0, value=18.0, step=0.25, format="%.2f")
        dterm = None
        if dt not in ["Credit Card","Medical Debt"]:
            dterm = st.number_input("Remaining Term (months)",
                                    min_value=1, max_value=480,
                                    value=DEBT_CFG[dt]["term"], step=12)
        st.caption(f"ℹ️ {DEBT_CFG[dt]['hint']}")
        if st.form_submit_button("➕ Add Debt"):
            if db > 0:
                entry = {"name":dn or dt,"type":dt,"balance":db,"rate":dr,"term_months":dterm}
                st.session_state.debts.append(entry)
                st.success(f"Min: ${calc_min(entry):,.0f}/mo")
                st.rerun()

    to_del = None
    for idx, d in enumerate(st.session_state.debts):
        c1,c2 = st.columns([5,1])
        c1.caption(f"**{d['name']}** ${d['balance']:,.0f} @ {d['rate']}%")
        if c2.button("✕",key=f"dd{idx}"):
            to_del = idx
    if to_del is not None:
        st.session_state.debts.pop(to_del); st.rerun()

    st.markdown("---")
    st.markdown("## ⚙️ Payoff Strategy")
    st.session_state.strategy = st.radio(
        "Method", ["Avalanche","Snowball"],
        captions=["Highest APR first","Lowest balance first"])


# ════════════════════════════════════════════════════════════════
# DERIVED GLOBALS
# ════════════════════════════════════════════════════════════════
debts    = st.session_state.debts
incomes  = st.session_state.incomes
future   = st.session_state.future_income
expenses = st.session_state.expenses
strategy = st.session_state.strategy

gross_m    = gross_monthly(incomes)
takehome_m = gross_m * 0.75
total_exp  = total_expenses_monthly()
total_bal  = sum(d["balance"] for d in debts)
total_min  = sum(calc_min(d) for d in debts)
avg_rate   = (sum(d["rate"]*d["balance"] for d in debts)/total_bal) if total_bal>0 else 0
dti        = total_min / takehome_m if takehome_m > 0 else 0
score      = freedom_score(debts, gross_m)
true_disp  = max(0, takehome_m - total_exp - total_min)
exp_ratio  = total_exp / takehome_m if takehome_m > 0 else 0

needs_total   = sum(v["amount"] for v in expenses.values() if v["category"]=="needs")
wants_total   = sum(v["amount"] for v in expenses.values() if v["category"]=="wants")
savings_total = sum(v["amount"] for v in expenses.values() if v["category"]=="savings")


# ════════════════════════════════════════════════════════════════
# MAIN UI
# ════════════════════════════════════════════════════════════════
st.markdown("""
<div class='hero'>
  <h1>💳 <span class='accent'>DebtFree</span> Advisor</h1>
  <p>Full-picture financial platform for W-2 employees — income, real expenses, debt payoff, and AI advice</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💸 Budget (50/30/20)", "🎯 Payoff Plan", "🤖 AI Advisor"])


# ════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════
with tab1:
    sc_col = "green" if score>=70 else ("yellow" if score>=40 else "red")
    dc_col = "green" if dti<.20  else ("yellow" if dti<.36  else "red")
    ex_col = "green" if exp_ratio<.70 else ("yellow" if exp_ratio<.85 else "red")
    td_col = "green" if true_disp>200 else ("yellow" if true_disp>0 else "red")

    st.markdown(f"""
    <div class='kpi-row'>
      <div class='kpi'><div class='kpi-label'>Monthly Take-Home</div>
        <div class='kpi-val green'>${takehome_m:,.0f}</div>
        <div class='kpi-sub'>After ~25% W-2 tax</div></div>

      <div class='kpi'><div class='kpi-label'>Total Expenses</div>
        <div class='kpi-val yellow'>${total_exp:,.0f}/mo</div>
        <div class='kpi-sub'>{exp_ratio:.0%} of take-home</div></div>

      <div class='kpi'><div class='kpi-label'>Debt Minimums</div>
        <div class='kpi-val {"red" if total_min>0 else "green"}'>${total_min:,.0f}/mo</div>
        <div class='kpi-sub'>{len(debts)} account(s)</div></div>

      <div class='kpi'><div class='kpi-label'>True Disposable</div>
        <div class='kpi-val {td_col}'>${true_disp:,.0f}/mo</div>
        <div class='kpi-sub'>After expenses + minimums</div></div>

      <div class='kpi'><div class='kpi-label'>Total Debt</div>
        <div class='kpi-val red'>${total_bal:,.0f}</div>
        <div class='kpi-sub'>Avg APR {avg_rate:.1f}%</div></div>

      <div class='kpi'><div class='kpi-label'>Debt-to-Income</div>
        <div class='kpi-val {dc_col}'>{dti:.0%}</div>
        <div class='kpi-sub'>{"✅ Healthy" if dti<.20 else "⚠️ Elevated" if dti<.36 else "🚨 Danger"}</div></div>

      <div class='kpi'><div class='kpi-label'>Freedom Score™</div>
        <div class='kpi-val {sc_col}'>{score}/100</div>
        <div class='kpi-sub'>{"Excellent" if score>=80 else "Good" if score>=60 else "Fair" if score>=40 else "At Risk"}</div></div>
    </div>
    """, unsafe_allow_html=True)

    if takehome_m > 0:
        # ── Cash Flow Waterfall ───────────────────────────────────
        st.markdown("<div class='sec-header'>💧 Monthly Cash Flow Breakdown</div>", unsafe_allow_html=True)

        wf_labels = ["Take-Home"]
        wf_values = [takehome_m]
        wf_colors = ["#3fb950"]

        cat_totals = {"Needs (Housing, etc.)": needs_total,
                      "Wants (Dining, etc.)":  wants_total,
                      "Savings & Retirement":  savings_total,
                      "Debt Minimums":         total_min}
        for label, val in cat_totals.items():
            if val > 0:
                wf_labels.append(label)
                wf_values.append(-val)
                wf_colors.append("#f85149" if "Debt" in label else "#e3b341" if "Wants" in label else "#58a6ff" if "Savings" in label else "#8b949e")

        wf_labels.append("True Disposable")
        wf_values.append(true_disp)
        wf_colors.append("#00d4aa" if true_disp > 0 else "#f85149")

        running = 0
        measures = []
        bases = []
        for i, v in enumerate(wf_values):
            if i == 0 or i == len(wf_values)-1:
                measures.append("absolute")
                bases.append(0)
            else:
                measures.append("relative")
                bases.append(running)
            running += v

        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=measures,
            x=wf_labels,
            y=wf_values,
            connector={"line":{"color":"#30363d"}},
            increasing={"marker":{"color":"#3fb950"}},
            decreasing={"marker":{"color":"#f85149"}},
            totals={"marker":{"color":"#00d4aa"}},
            text=[f"${abs(v):,.0f}" for v in wf_values],
            textposition="outside",
        ))
        fig_wf.update_layout(
            paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            font=dict(color="#8b949e", family="Sora"),
            xaxis=dict(gridcolor="#21262d", color="#8b949e"),
            yaxis=dict(gridcolor="#21262d", color="#8b949e", tickprefix="$"),
            height=360, margin=dict(l=10,r=10,t=30,b=10),
            showlegend=False,
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        # Quick alerts
        if true_disp < 0:
            st.markdown(f"<div class='danger'>🚨 <b>You're overspending by ${abs(true_disp):,.0f}/month.</b> Your expenses + debt minimums exceed your take-home pay. You must either cut expenses or find additional income immediately.</div>", unsafe_allow_html=True)
        elif true_disp < 200:
            st.markdown(f"<div class='warn'>⚠️ <b>Very tight budget.</b> Only ${true_disp:,.0f}/mo truly free after all expenses and debt minimums. One unexpected bill could cause a missed payment. Building even a $500 emergency buffer should be your first step.</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='success-box'>✅ <b>${true_disp:,.0f}/mo available</b> above all expenses and minimums. This is your debt-payoff ammunition — use it aggressively.</div>", unsafe_allow_html=True)

    # ── Debt table ────────────────────────────────────────────────
    if debts:
        st.markdown("<div class='sec-header'>📋 Debt Accounts</div>", unsafe_allow_html=True)
        ICONS = {"Credit Card":"💳","Car Loan":"🚗","Mortgage":"🏠","Student Loan":"🎓",
                 "Personal Loan":"🤝","Medical Debt":"🏥","Other":"📄"}
        rows = []
        for d in debts:
            mp  = calc_min(d)
            mi  = d["balance"]*d["rate"]/100/12
            rows.append({
                "": ICONS.get(d["type"],"📄"), "Name":d["name"], "Type":d["type"],
                "Balance":f"${d['balance']:,.0f}", "APR":f"{d['rate']}%",
                "Auto Min/mo":f"${mp:,.0f}",
                "Interest/mo":f"${mi:,.0f}",
                "Principal/mo":f"${max(0,mp-mi):,.0f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not incomes:
        st.markdown("<div style='text-align:center;padding:3rem;color:#8b949e;'>👈 Add your income in the sidebar to get started.</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# TAB 2 — BUDGET (50/30/20)
# ════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='sec-header'>📐 The 50/30/20 Rule — Your Budget Framework</div>", unsafe_allow_html=True)

    if takehome_m > 0:
        target_needs   = takehome_m * 0.50
        target_wants   = takehome_m * 0.30
        target_savings = takehome_m * 0.20

        # ── Rule overview ─────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        for col, label, color, target, actual, tip in [
            (col1, "50% Needs",   "#58a6ff", target_needs,   needs_total,   "Rent, utilities, groceries, insurance, transport"),
            (col2, "30% Wants",   "#a371f7", target_wants,   wants_total,   "Dining, entertainment, subscriptions, shopping"),
            (col3, "20% Savings", "#3fb950", target_savings, savings_total, "Emergency fund, 401k, extra debt payments"),
        ]:
            pct = actual / takehome_m * 100 if takehome_m > 0 else 0
            over = actual > target
            with col:
                st.markdown(f"""
                <div class='sc-card'>
                  <div style='font-weight:600;color:{color};font-size:.95rem;margin-bottom:.4rem;'>{label}</div>
                  <div style='font-size:1.3rem;font-weight:700;font-family:JetBrains Mono,monospace;
                              color:{"#f85149" if over else "#e6edf3"};'>${actual:,.0f}</div>
                  <div style='font-size:.75rem;color:#8b949e;margin:.25rem 0;'>Target: ${target:,.0f} ({pct:.0f}% used)</div>
                  <div class='budget-bar-wrap'>
                    <div class='budget-bar' style='width:{min(pct*2,100):.0f}%;
                      background:{"#f85149" if over else color};'></div>
                  </div>
                  <div style='font-size:.72rem;color:#6e7681;margin-top:.3rem;'>{tip}</div>
                  {"<div style='font-size:.75rem;color:#f85149;margin-top:.3rem;'>⚠️ Over by $"+f"{actual-target:,.0f}"+"</div>" if over else ""}
                </div>
                """, unsafe_allow_html=True)

        # ── 50/30/20 Donut ────────────────────────────────────────
        col_chart, col_inputs = st.columns([1, 1.4])
        with col_chart:
            unallocated = max(0, takehome_m - needs_total - wants_total - savings_total - total_min)
            pie_labels  = ["Needs","Wants","Savings","Debt Min.","Unallocated"]
            pie_values  = [needs_total, wants_total, savings_total, total_min, unallocated]
            pie_colors  = ["#58a6ff","#a371f7","#3fb950","#f85149","#30363d"]
            non_zero = [(l,v,c) for l,v,c in zip(pie_labels,pie_values,pie_colors) if v > 0]
            if non_zero:
                fig_pie = go.Figure(go.Pie(
                    labels=[x[0] for x in non_zero],
                    values=[x[1] for x in non_zero],
                    marker_colors=[x[2] for x in non_zero],
                    hole=.55,
                    textinfo="percent",
                    hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
                ))
                fig_pie.update_layout(
                    paper_bgcolor="#0d1117", font=dict(color="#8b949e",family="Sora"),
                    legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
                    height=300, margin=dict(l=0,r=0,t=20,b=0),
                    annotations=[dict(text=f"${takehome_m:,.0f}",
                                      x=.5,y=.5,font_size=15,showarrow=False,
                                      font_color="#e6edf3",font_family="JetBrains Mono")]
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_inputs:
            st.markdown("#### ✏️ Enter Your Monthly Expenses")
            st.caption("Fill in what you actually spend. Suggested amounts shown based on 50/30/20.")

            SUGGESTED = {
                "Housing":        takehome_m * 0.28,
                "Transportation": takehome_m * 0.10,
                "Groceries":      takehome_m * 0.07,
                "Utilities":      takehome_m * 0.04,
                "Insurance":      takehome_m * 0.05,
                "Healthcare":     takehome_m * 0.02,
                "Childcare":      0,
                "Dining Out":     takehome_m * 0.08,
                "Entertainment":  takehome_m * 0.05,
                "Shopping":       takehome_m * 0.07,
                "Subscriptions":  takehome_m * 0.03,
                "Personal Care":  takehome_m * 0.02,
                "Travel":         takehome_m * 0.03,
                "Emergency Fund": takehome_m * 0.05,
                "Retirement 401k":takehome_m * 0.10,
                "Other Savings":  takehome_m * 0.05,
            }
            CAT_LABELS = {"needs":"🏠 Needs","wants":"🎭 Wants","savings":"🏦 Savings"}
            current_cat = None
            for name, cfg in expenses.items():
                if cfg["category"] != current_cat:
                    current_cat = cfg["category"]
                    st.markdown(f"**{CAT_LABELS[current_cat]}**")
                suggested = SUGGESTED.get(name, 0)
                new_val = st.number_input(
                    f"{name} (suggested ${suggested:,.0f})",
                    min_value=0.0,
                    value=float(cfg["amount"]),
                    step=25.0,
                    format="%.0f",
                    key=f"exp_{name}",
                )
                st.session_state.expenses[name]["amount"] = new_val

        # ── Personalized budget advice ────────────────────────────
        st.markdown("<div class='sec-header'>🧠 Budget Intelligence</div>", unsafe_allow_html=True)
        if needs_total > target_needs:
            st.markdown(f"<div class='warn'>🏠 <b>Needs are {needs_total/takehome_m:.0%} of take-home</b> (target: 50%). Your fixed costs are high. Focus: housing (currently ${expenses['Housing']['amount']:,.0f}/mo — the largest lever), or shop around on insurance and utilities.</div>", unsafe_allow_html=True)
        if wants_total > target_wants:
            over_wants = wants_total - target_wants
            st.markdown(f"<div class='warn'>🎭 <b>Wants are over by ${over_wants:,.0f}/mo.</b> Cutting discretionary spending is the fastest way to free up cash for debt payoff. Even trimming ${over_wants*0.5:,.0f}/mo could shave months off your debt timeline.</div>", unsafe_allow_html=True)
        if expenses["Retirement 401k"]["amount"] == 0:
            st.markdown("<div class='warn'>⚠️ <b>No 401k contribution detected.</b> If your employer matches, contribute at least enough to get the full match — that's an instant 50-100% return, better than paying down even high-interest debt.</div>", unsafe_allow_html=True)
        if expenses["Emergency Fund"]["amount"] == 0 and true_disp > 0:
            st.markdown("<div class='warn'>⚠️ <b>No emergency fund contribution.</b> Without a buffer, one car repair or medical bill could force you onto a credit card, erasing months of debt progress. Even $100/mo builds a $1,200 cushion in a year.</div>", unsafe_allow_html=True)
        if true_disp > 500:
            st.markdown(f"<div class='success-box'>💪 <b>You have ${true_disp:,.0f}/mo truly free</b> after all expenses and debt minimums. This is powerful — every dollar of this directed at high-interest debt is a guaranteed {avg_rate:.1f}% return.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align:center;padding:3rem;color:#8b949e;'>Add your income first to see 50/30/20 targets.</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# TAB 3 — PAYOFF PLAN
# ════════════════════════════════════════════════════════════════
with tab3:
    if debts and incomes and total_exp > 0:
        st.markdown("<div class='sec-header'>🎯 Three Smart Scenarios — Based on Your Real Budget</div>", unsafe_allow_html=True)
        st.caption(f"Using true disposable income of **${true_disp:,.0f}/mo** (take-home ${takehome_m:,.0f} − expenses ${total_exp:,.0f} − minimums ${total_min:,.0f})")

        if true_disp <= 0:
            st.markdown("<div class='danger'>🚨 No disposable income available for extra payments. You must reduce expenses before any payoff acceleration is possible. Go to the Budget tab and find cuts.</div>", unsafe_allow_html=True)
        else:
            SCENARIOS = [
                {"label":"📉 Minimums Only",          "extra_pct":0.0,  "color":"#f85149","desc":"Only required minimum payments."},
                {"label":"⚖️ Balanced (Recommended)", "extra_pct":0.50, "color":"#e3b341","desc":"50% of disposable toward extra payments."},
                {"label":"🚀 Aggressive",              "extra_pct":0.90, "color":"#3fb950","desc":"90% of disposable toward extra payments."},
            ]

            fig = go.Figure()
            results = []
            for sc in SCENARIOS:
                tl, events = simulate(debts, incomes, future, sc["extra_pct"], strategy)
                if tl:
                    extra_mo = true_disp * sc["extra_pct"]
                    fig.add_trace(go.Scatter(
                        x=[t["month"] for t in tl],
                        y=[t["total_remaining"] for t in tl],
                        name=sc["label"],
                        line=dict(color=sc["color"],width=2.5),
                        hovertemplate=f'<b>{sc["label"]}</b><br>Month %{{x}}: $%{{y:,.0f}} remaining<extra></extra>'
                    ))
                    results.append({**sc,"tl":tl,"events":events,
                                    "months":tl[-1]["month"],
                                    "interest":tl[-1]["total_interest"],
                                    "extra_mo":extra_mo})

            for fi in future:
                fig.add_vline(x=fi["start_month"],line_dash="dot",line_color="#58a6ff",
                    annotation_text=f"📈 {fi['label']}",annotation_font_color="#58a6ff")

            fig.update_layout(
                paper_bgcolor="#0d1117",plot_bgcolor="#0d1117",
                font=dict(color="#8b949e",family="Sora"),
                xaxis=dict(title="Month",gridcolor="#21262d",color="#8b949e"),
                yaxis=dict(title="Total Debt ($)",gridcolor="#21262d",color="#8b949e",tickprefix="$"),
                legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
                title=dict(text="Your Three Paths to Debt Freedom",font=dict(color="#e6edf3",size=15)),
                height=400,margin=dict(l=10,r=10,t=50,b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            # Scenario cards
            cols = st.columns(len(results))
            for col, res in zip(cols, results):
                sc = res
                pdate = (date.today()+timedelta(days=res["months"]*30.44)).strftime("%b %Y")
                with col:
                    st.markdown(f"""
                    <div class='sc-card'>
                      <div style='font-weight:600;color:{sc["color"]};margin-bottom:.4rem;'>{sc["label"]}</div>
                      <div style='font-size:1.35rem;font-weight:700;
                                  font-family:JetBrains Mono,monospace;color:{sc["color"]};'>{pdate}</div>
                      <div style='font-size:.8rem;color:#8b949e;margin-top:.4rem;line-height:1.65;'>
                        <b style='color:#e6edf3;'>{res["months"]} months</b> ({res["months"]/12:.1f} yrs)<br>
                        Interest: <b style='color:#f85149;'>${res["interest"]:,.0f}</b><br>
                        Extra/mo: <b style='color:#3fb950;'>${res["extra_mo"]:,.0f}</b><br>
                        <span style='color:#6e7681;font-size:.72rem;'>{sc["desc"]}</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            if len(results) >= 2:
                saved_int = results[0]["interest"] - results[-1]["interest"]
                saved_mo  = results[0]["months"]   - results[-1]["months"]
                st.markdown(f"""
                <div class='advisor'>
                  <div class='advisor-title'>🧠 What the Numbers Tell You</div>
                  <div class='advisor-body'>
                    Aggressive vs Minimum Only: saves <b style='color:#3fb950'>${saved_int:,.0f} in interest</b>
                    and <b style='color:#3fb950'>{saved_mo} months ({saved_mo/12:.1f} years)</b> of debt payments.
                    At your average APR of <b>{avg_rate:.1f}%</b>, every extra dollar you put toward debt
                    earns a guaranteed {avg_rate:.1f}% return — better than most savings accounts or CDs.
                  </div>
                </div>
                """, unsafe_allow_html=True)

            # ── Milestones ─────────────────────────────────────────
            if len(results) >= 2:
                st.markdown("<div class='sec-header'>🏁 Payoff Milestones — Balanced Scenario</div>", unsafe_allow_html=True)
                for ev in results[1]["events"]:
                    st.markdown(f"""
                    <div style='background:#161b22;border:1px solid #30363d;border-radius:10px;
                                padding:.8rem 1.2rem;margin-bottom:.4rem;
                                display:flex;justify-content:space-between;align-items:center;'>
                      <div><b style='color:#e6edf3;'>{ev["name"]}</b>
                        <span style='color:#8b949e;font-size:.78rem;'> — month {ev["month"]}</span></div>
                      <div style='text-align:right;'>
                        <div style='color:#00d4aa;font-weight:700;'>{ev["date"]}</div>
                        <div style='color:#3fb950;font-size:.76rem;'>+${ev["freed_min"]:,.0f}/mo freed 🎉</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── Per-debt lines ─────────────────────────────────────
            if len(results) >= 2:
                st.markdown("<div class='sec-header'>📊 Individual Debt Balances — Balanced Scenario</div>", unsafe_allow_html=True)
                tl = results[1]["tl"]
                COLORS = ["#58a6ff","#f85149","#e3b341","#a371f7","#3fb950","#ffa657","#00d4aa"]
                fig2 = go.Figure()
                for idx, d in enumerate(debts):
                    fig2.add_trace(go.Scatter(
                        x=[t["month"] for t in tl],
                        y=[t["balances"][idx] for t in tl],
                        name=d["name"],
                        line=dict(color=COLORS[idx%len(COLORS)],width=2),
                        hovertemplate=f'{d["name"]}: $%{{y:,.0f}}<extra></extra>'
                    ))
                fig2.update_layout(
                    paper_bgcolor="#0d1117",plot_bgcolor="#0d1117",
                    font=dict(color="#8b949e",family="Sora"),
                    xaxis=dict(title="Month",gridcolor="#21262d",color="#8b949e"),
                    yaxis=dict(title="Balance ($)",gridcolor="#21262d",color="#8b949e",tickprefix="$"),
                    legend=dict(bgcolor="#161b22",bordercolor="#30363d",borderwidth=1),
                    height=320,margin=dict(l=10,r=10,t=30,b=10)
                )
                st.plotly_chart(fig2, use_container_width=True)

        # ── Debt-specific advisor tips ─────────────────────────────
        st.markdown("<div class='sec-header'>💡 Personalized Payoff Strategies</div>", unsafe_allow_html=True)
        high_rate = [d for d in debts if d["rate"] >= 20]
        cc_debts  = [d for d in debts if d["type"] == "Credit Card"]
        mortgage  = [d for d in debts if d["type"] == "Mortgage"]

        if high_rate:
            cost = sum(d["balance"]*d["rate"]/100 for d in high_rate)
            st.markdown(f"<div class='danger'>🔥 <b>{', '.join(d['name'] for d in high_rate)}</b> {'are' if len(high_rate)>1 else 'is'} costing you <b>${cost:,.0f}/year</b> in interest. Every $1 extra here is your highest-priority move.</div>", unsafe_allow_html=True)
        if cc_debts:
            cc_bal = sum(d["balance"] for d in cc_debts)
            st.markdown(f"""<div class='advisor'><div class='advisor-title'>💳 Balance Transfer Opportunity</div>
            <div class='advisor-body'>${cc_bal:,.0f} in credit card debt. A 0% APR balance transfer card (12–21 month promos)
            eliminates interest while you pay down principal. Even with a 3% fee (${cc_bal*0.03:,.0f}),
            you'd save thousands. Pay it off before the promo ends.</div></div>""", unsafe_allow_html=True)
        if mortgage:
            m = mortgage[0]
            st.markdown(f"""<div class='advisor'><div class='advisor-title'>🏠 Mortgage — W-2 Tax Strategy</div>
            <div class='advisor-body'>At 22% tax bracket, your {m['rate']:.1f}% mortgage has an effective
            after-tax rate of ~{m['rate']*0.78:.1f}%. Pay off all higher-rate debts first before making
            extra mortgage payments.</div></div>""", unsafe_allow_html=True)

        with st.expander("⚡ 10 Proven Accelerators for W-2 Employees"):
            st.markdown("""
**1. Tax Refund Rule** — Average W-2 refund: $3,000+. Send 100% to highest-rate debt every February.

**2. Bi-Weekly Trick** — Pay half your monthly payment every 2 weeks = 13 payments/year instead of 12. One free extra payment, zero budget change.

**3. Raise → Debt First** — You weren't living on that money. Route 100% of every raise to debt until you're free.

**4. 0% Balance Transfer** — Move credit card debt to 0% promo card. Kill it during the window. Even a 3% fee pays off fast.

**5. Adjust W-4** — Big refund = IRS has your money all year interest-free. Adjust W-4 → get it monthly → apply to debt.

**6. Sell Idle Assets** — Even $1,000 on a 24% card saves $240/year forever.

**7. Automate Extra Payments** — Set it up the day after your paycheck hits. Automation beats willpower every time.

**8. Bonus/Overtime = 100% to Debt** — Treat non-base income as windfalls, not lifestyle money.

**9. Snowball Reinvestment** — When a debt dies, stack its full payment onto the next debt. Your payment grows with every win.

**10. Get Your 401k Match First** — Before any extra debt payment, always capture your full employer match. That's a 50-100% instant return — nothing beats it.
            """)

    elif not incomes:
        st.info("👈 Add income in the sidebar to start.")
    elif not debts:
        st.info("👈 Add debts in the sidebar.")
    else:
        st.warning("💸 Fill in your monthly expenses in the **Budget tab** first — the payoff plan needs real expense data to calculate how much you can put toward debt.")


# ════════════════════════════════════════════════════════════════
# TAB 4 — AI ADVISOR (GROQ)
# ════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("<div class='sec-header'>🤖 AI Financial Advisor — Powered by Groq (Llama 3.3)</div>", unsafe_allow_html=True)

    if not st.session_state.groq_api_key:
        st.markdown("""
        <div class='advisor'>
          <div class='advisor-title'>🔑 Set Up Your Free AI Advisor</div>
          <div class='advisor-body'>
            <b>3 steps to activate:</b><br>
            1. Go to <a href='https://console.groq.com' target='_blank' style='color:#00d4aa;'>console.groq.com</a><br>
            2. Sign up free (no credit card) → Create API Key<br>
            3. Paste the key (starts with <code>gsk_</code>) in the sidebar under "AI Advisor Setup"<br><br>
            The AI knows your full financial picture — income, expenses, every debt — and gives personalized advice.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Context summary shown to user
        with st.expander("📋 What the AI knows about you", expanded=False):
            st.markdown(f"""
            - **Monthly take-home:** ${takehome_m:,.0f}
            - **Total expenses:** ${total_exp:,.0f}/mo
            - **True disposable:** ${true_disp:,.0f}/mo
            - **Total debt:** ${total_bal:,.0f} across {len(debts)} accounts
            - **Average APR:** {avg_rate:.1f}%
            - **Freedom Score:** {score}/100
            - **Strategy:** {strategy}
            """)

        # Suggested questions
        st.markdown("**💬 Try asking:**")
        suggestions = [
            "Which debt should I pay first and why?",
            "How much faster can I pay off debt if I cut dining out by $200/mo?",
            "Should I do a balance transfer on my credit cards?",
            "Explain the difference between avalanche and snowball for my situation",
            "Am I saving enough for retirement while paying off debt?",
            "What's my biggest financial risk right now?",
        ]
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            with cols[i % 3]:
                if st.button(s, key=f"sug_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role":"user","content":s})
                    with st.spinner("Thinking…"):
                        reply = ask_groq(s, st.session_state.groq_api_key)
                    st.session_state.chat_history.append({"role":"assistant","content":reply})
                    st.rerun()

        st.markdown("---")

        # Chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("<div style='text-align:center;color:#8b949e;padding:2rem;'>Ask me anything about your finances 👆</div>", unsafe_allow_html=True)
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"<div class='chat-label-user'>You</div><div class='chat-msg-user'>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-label-ai'>🤖 AI Advisor</div><div class='chat-msg-ai'>{msg['content']}</div>", unsafe_allow_html=True)

        # Input
        with st.form("chat_form", clear_on_submit=True):
            col_in, col_btn = st.columns([5, 1])
            user_input = col_in.text_input("Your question", placeholder="Ask about your specific debts, budget, strategy…", label_visibility="collapsed")
            send = col_btn.form_submit_button("Send ➤")
            if send and user_input.strip():
                st.session_state.chat_history.append({"role":"user","content":user_input})
                with st.spinner("Thinking…"):
                    reply = ask_groq(user_input, st.session_state.groq_api_key)
                st.session_state.chat_history.append({"role":"assistant","content":reply})
                st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()

# ── Footer ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("<div style='text-align:center;color:#484f58;font-size:.73rem;'>DebtFree Advisor v3 • Informational only • Not a substitute for licensed financial advice</div>", unsafe_allow_html=True)
