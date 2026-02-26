"""
DebtFree Advisor - Smart Debt Payoff Platform for W-2 Employees
Run with: streamlit run debt_advisor.py
Dependencies: pip install streamlit plotly pandas
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import math

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DebtFree Advisor",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

.main { background: #0d1117; }

/* Header */
.hero-header {
    background: linear-gradient(135deg, #1a2332 0%, #0d1117 50%, #1a2332 100%);
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(0,200,150,0.06) 0%, transparent 60%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: #e6edf3;
    margin: 0;
}
.hero-subtitle {
    color: #8b949e;
    font-size: 1rem;
    margin-top: 0.3rem;
}
.accent { color: #00d4aa; }

/* Metric cards */
.metric-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.metric-card {
    flex: 1;
    min-width: 160px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #00d4aa; }
.metric-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.4rem; }
.metric-value { font-size: 1.7rem; font-weight: 700; color: #e6edf3; font-family: 'JetBrains Mono', monospace; }
.metric-value.green { color: #3fb950; }
.metric-value.red { color: #f85149; }
.metric-value.yellow { color: #e3b341; }
.metric-value.blue { color: #58a6ff; }
.metric-delta { font-size: 0.78rem; color: #8b949e; margin-top: 0.2rem; }

/* Advisor box */
.advisor-box {
    background: linear-gradient(135deg, #0d2818 0%, #0d1a0d 100%);
    border: 1px solid #00d4aa44;
    border-left: 4px solid #00d4aa;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
}
.advisor-title { color: #00d4aa; font-weight: 600; font-size: 1rem; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.5rem; }
.advisor-text { color: #c9d1d9; font-size: 0.9rem; line-height: 1.7; }
.advisor-text ul { margin: 0.5rem 0; padding-left: 1.2rem; }
.advisor-text li { margin-bottom: 0.4rem; }

/* Warning box */
.warning-box {
    background: #1f1500;
    border: 1px solid #e3b34144;
    border-left: 4px solid #e3b341;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin: 0.8rem 0;
    color: #e3b341;
    font-size: 0.88rem;
}

/* Debt item row */
.debt-item {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem 1.3rem;
    margin-bottom: 0.7rem;
}

/* Section header */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e6edf3;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #21262d;
}

/* Strategy badge */
.badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 0.2rem;
}
.badge-green { background: #0d2818; color: #3fb950; border: 1px solid #3fb95044; }
.badge-red { background: #2d1117; color: #f85149; border: 1px solid #f8514944; }
.badge-blue { background: #0d1a2d; color: #58a6ff; border: 1px solid #58a6ff44; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}

/* Buttons */
div.stButton > button {
    background: #00d4aa;
    color: #0d1117;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-family: 'Sora', sans-serif;
    transition: all 0.2s;
}
div.stButton > button:hover {
    background: #00f0c0;
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(0,212,170,0.3);
}

/* Tables */
.stDataFrame { border-radius: 10px; overflow: hidden; }

/* Expander */
.streamlit-expanderHeader { color: #58a6ff !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "income": 5000.0,
        "income_freq": "Monthly",
        "debts": [],
        "extra_payment": 0.0,
        "strategy": "Avalanche (Highest Interest First)",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────
FREQ_TO_MONTHLY = {"Weekly": 4.33, "Bi-Weekly": 2.17, "Monthly": 1.0, "Annual": 1/12}

def monthly_income():
    return st.session_state.income * FREQ_TO_MONTHLY[st.session_state.income_freq]

def months_to_payoff(balance, rate_annual, monthly_payment):
    """Returns months to pay off, total paid, total interest."""
    if monthly_payment <= 0 or balance <= 0:
        return None, None, None
    r = rate_annual / 100 / 12
    if r == 0:
        months = math.ceil(balance / monthly_payment)
        return months, months * monthly_payment, 0.0
    if monthly_payment <= balance * r:
        return None, None, None  # payment too low
    months = -math.log(1 - (balance * r) / monthly_payment) / math.log(1 + r)
    months = math.ceil(months)
    total_paid = monthly_payment * months
    return months, total_paid, total_paid - balance

def simulate_payoff(debts, extra_monthly, strategy):
    """
    Simulate month-by-month payoff using chosen strategy.
    Returns: list of dicts with month, remaining balances, total paid, interest paid.
    """
    if not debts:
        return [], []

    # Sort order
    if strategy == "Avalanche (Highest Interest First)":
        order = sorted(range(len(debts)), key=lambda i: -debts[i]["rate"])
    else:  # Snowball
        order = sorted(range(len(debts)), key=lambda i: debts[i]["balance"])

    balances = [d["balance"] for d in debts]
    rates = [d["rate"] / 100 / 12 for d in debts]
    min_payments = [d["min_payment"] for d in debts]

    timeline = []
    total_interest = 0.0
    month = 0
    MAX_MONTHS = 600

    while any(b > 0.01 for b in balances) and month < MAX_MONTHS:
        month += 1
        available = extra_monthly + sum(min_payments[i] for i in range(len(debts)) if balances[i] > 0.01)

        # Apply interest & min payments
        interest_this_month = 0
        for i in range(len(debts)):
            if balances[i] > 0.01:
                interest = balances[i] * rates[i]
                interest_this_month += interest
                balances[i] += interest
                pay = min(min_payments[i], balances[i])
                balances[i] -= pay
                available -= pay

        total_interest += interest_this_month

        # Apply extra to target debt
        available = max(0, available)
        for i in order:
            if balances[i] > 0.01 and available > 0:
                pay = min(available, balances[i])
                balances[i] -= pay
                available -= pay

        # Clamp
        balances = [max(0.0, b) for b in balances]

        timeline.append({
            "month": month,
            "balances": balances.copy(),
            "total_remaining": sum(balances),
            "total_interest_paid": total_interest,
        })

    events = []
    for i, d in enumerate(debts):
        for t in timeline:
            if t["balances"][i] < 0.01:
                events.append({
                    "debt": d["name"],
                    "payoff_month": t["month"],
                    "payoff_date": (date.today() + timedelta(days=t["month"] * 30.4)).strftime("%b %Y"),
                })
                break

    return timeline, events


def debt_freedom_score(debts, income_m):
    """0-100 score based on DTI and interest load."""
    if not debts or income_m == 0:
        return 100
    total_min = sum(d["min_payment"] for d in debts)
    total_balance = sum(d["balance"] for d in debts)
    dti = total_min / income_m
    avg_rate = sum(d["rate"] * d["balance"] for d in debts) / max(total_balance, 1)
    score = 100 - (dti * 150) - (avg_rate * 2)
    return max(0, min(100, round(score)))

def advisor_insights(debts, income_m, extra, strategy):
    insights = []
    if not debts:
        return ["Add your debts to get personalized advice."]

    total_balance = sum(d["balance"] for d in debts)
    total_min = sum(d["min_payment"] for d in debts)
    dti = total_min / income_m if income_m > 0 else 0
    high_rate = [d for d in debts if d["rate"] >= 20]
    cc_debts = [d for d in debts if d["type"] == "Credit Card"]
    available_after = income_m - total_min - extra

    # DTI advice
    if dti > 0.43:
        insights.append(f"🚨 **Danger Zone:** Your debt-to-income ratio is **{dti:.0%}** — above the 43% mortgage qualification threshold. Lenders see you as high-risk. Priority #1: reduce minimum payments by paying off smaller debts fast.")
    elif dti > 0.20:
        insights.append(f"⚠️ **Watch Your DTI:** At **{dti:.0%}**, you're carrying a moderate debt load. Keep it below 20% for financial flexibility.")
    else:
        insights.append(f"✅ **Healthy DTI:** Your debt-to-income ratio of **{dti:.0%}** is manageable. You have room to aggressively pay down debt.")

    # High interest
    if high_rate:
        names = ", ".join(d["name"] for d in high_rate)
        insights.append(f"🔥 **High-Rate Alert:** {names} {'are' if len(high_rate)>1 else 'is'} charging 20%+ APR. This is the most expensive money you owe — every dollar here costs you 20+ cents per year. Eliminate these first.")

    # Extra payment impact
    if extra > 0:
        insights.append(f"💪 **Extra Payment Power:** Your ${extra:,.0f}/mo extra payment is your fastest wealth-building tool. Even small increases dramatically shrink your timeline.")
    else:
        if available_after > 100:
            insights.append(f"💡 **Untapped Potential:** You have ~${available_after:,.0f}/mo of breathing room after minimums. Putting even **${min(200, available_after*0.5):,.0f}** extra toward debt could save thousands in interest.")

    # Strategy
    if strategy == "Avalanche (Highest Interest First)":
        insights.append("📊 **Avalanche Strategy:** Mathematically optimal — you'll pay the least total interest. Best if you're motivated by numbers and saving money.")
    else:
        insights.append("⛄ **Snowball Strategy:** Behaviorally powerful — quick wins on small balances build momentum. Research shows this works better for people who struggle with motivation.")

    # W-2 specific
    insights.append("📋 **W-2 Tax Tip:** As a W-2 employee, mortgage interest is tax-deductible (if you itemize). This effectively lowers your mortgage rate — factor this in before paying extra on your mortgage vs. credit cards.")

    return insights


# ─────────────────────────────────────────────
# SIDEBAR — INCOME & ADD DEBTS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💰 Income Setup")
    st.session_state.income = st.number_input(
        "Gross Income", min_value=0.0, value=st.session_state.income,
        step=100.0, format="%.2f", help="Your before-tax income per pay period"
    )
    st.session_state.income_freq = st.selectbox(
        "Pay Frequency", ["Weekly", "Bi-Weekly", "Monthly", "Annual"],
        index=["Weekly", "Bi-Weekly", "Monthly", "Annual"].index(st.session_state.income_freq)
    )

    # Estimate take-home (rough 25% tax for W-2)
    gross_m = monthly_income()
    est_takehome = gross_m * 0.75
    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;padding:0.8rem 1rem;margin-top:0.5rem;'>
    <div style='font-size:0.72rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.08em;'>Est. Monthly Take-Home</div>
    <div style='font-size:1.3rem;font-weight:700;color:#3fb950;font-family:JetBrains Mono,monospace;'>${est_takehome:,.0f}</div>
    <div style='font-size:0.7rem;color:#6e7681;'>After ~25% W-2 taxes</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ➕ Add a Debt")

    with st.form("add_debt_form", clear_on_submit=True):
        d_type = st.selectbox("Debt Type", ["Credit Card", "Car Loan", "Mortgage", "Student Loan", "Personal Loan", "Other"])
        d_name = st.text_input("Label / Name", placeholder="e.g. Chase Sapphire, Honda Civic")
        d_balance = st.number_input("Current Balance ($)", min_value=0.0, step=100.0, format="%.2f")
        d_rate = st.number_input("Interest Rate (APR %)", min_value=0.0, max_value=100.0, step=0.1, format="%.2f")
        d_min = st.number_input("Minimum Monthly Payment ($)", min_value=0.0, step=10.0, format="%.2f")

        submitted = st.form_submit_button("Add Debt ➕")
        if submitted:
            if d_balance > 0 and d_name:
                st.session_state.debts.append({
                    "name": d_name if d_name else d_type,
                    "type": d_type,
                    "balance": d_balance,
                    "rate": d_rate,
                    "min_payment": d_min,
                })
                st.success(f"Added: {d_name}")
            else:
                st.error("Please enter a name and balance > 0.")

    st.markdown("---")
    st.markdown("### ⚙️ Payoff Settings")
    st.session_state.extra_payment = st.number_input(
        "Extra Monthly Payment ($)", min_value=0.0,
        value=st.session_state.extra_payment, step=50.0, format="%.2f",
        help="Amount you can put toward debt above minimums each month"
    )
    st.session_state.strategy = st.radio(
        "Payoff Strategy",
        ["Avalanche (Highest Interest First)", "Snowball (Lowest Balance First)"],
        index=0 if st.session_state.strategy.startswith("Ava") else 1
    )


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("""
<div class='hero-header'>
  <div class='hero-title'>💳 <span class='accent'>DebtFree</span> Advisor</div>
  <div class='hero-subtitle'>Smart debt payoff platform for W-2 employees — your personal financial advisor</div>
</div>
""", unsafe_allow_html=True)

debts = st.session_state.debts
income_m = monthly_income()
extra = st.session_state.extra_payment
strategy = st.session_state.strategy

# ── SUMMARY METRICS ─────────────────────────
total_balance = sum(d["balance"] for d in debts)
total_min = sum(d["min_payment"] for d in debts)
avg_rate = (sum(d["rate"] * d["balance"] for d in debts) / total_balance) if total_balance > 0 else 0
score = debt_freedom_score(debts, income_m)
dti = total_min / income_m if income_m > 0 else 0

score_color = "green" if score >= 70 else ("yellow" if score >= 40 else "red")
dti_color = "green" if dti < 0.20 else ("yellow" if dti < 0.36 else "red")

st.markdown(f"""
<div class='metric-row'>
  <div class='metric-card'>
    <div class='metric-label'>Total Debt</div>
    <div class='metric-value red'>${total_balance:,.0f}</div>
    <div class='metric-delta'>{len(debts)} account(s)</div>
  </div>
  <div class='metric-card'>
    <div class='metric-label'>Monthly Income</div>
    <div class='metric-value green'>${income_m:,.0f}</div>
    <div class='metric-delta'>{st.session_state.income_freq} → Monthly</div>
  </div>
  <div class='metric-card'>
    <div class='metric-label'>Total Min. Payments</div>
    <div class='metric-value yellow'>${total_min:,.0f}/mo</div>
    <div class='metric-delta'>{dti:.0%} of income</div>
  </div>
  <div class='metric-card'>
    <div class='metric-label'>Avg Interest Rate</div>
    <div class='metric-value {"red" if avg_rate > 15 else "yellow"}'>{avg_rate:.1f}%</div>
    <div class='metric-delta'>Weighted by balance</div>
  </div>
  <div class='metric-card'>
    <div class='metric-label'>Freedom Score™</div>
    <div class='metric-value {score_color}'>{score}/100</div>
    <div class='metric-delta'>{"Excellent" if score>=80 else "Good" if score>=60 else "Fair" if score>=40 else "At Risk"}</div>
  </div>
  <div class='metric-card'>
    <div class='metric-label'>Extra Payment</div>
    <div class='metric-value blue'>${extra:,.0f}/mo</div>
    <div class='metric-delta'>Above minimums</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── DEBT LIST ────────────────────────────────
if debts:
    st.markdown("<div class='section-header'>📋 Your Debts</div>", unsafe_allow_html=True)
    
    to_delete = None
    for i, d in enumerate(debts):
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1.5, 1.3, 1.3, 1.3, 0.7])
        type_icons = {"Credit Card": "💳", "Car Loan": "🚗", "Mortgage": "🏠",
                      "Student Loan": "🎓", "Personal Loan": "🤝", "Other": "📄"}
        icon = type_icons.get(d["type"], "📄")
        m, total_p, int_p = months_to_payoff(d["balance"], d["rate"], d["min_payment"])
        
        with col1:
            st.markdown(f"**{icon} {d['name']}**  \n<span style='font-size:0.78rem;color:#8b949e;'>{d['type']}</span>", unsafe_allow_html=True)
        with col2:
            st.metric("Balance", f"${d['balance']:,.0f}", label_visibility="collapsed")
            st.caption(f"${d['balance']:,.0f} balance")
        with col3:
            st.caption(f"APR: **{d['rate']}%**")
        with col4:
            st.caption(f"Min: **${d['min_payment']:,.0f}/mo**")
        with col5:
            if m:
                st.caption(f"Min-only payoff: **{m} mo**")
            else:
                st.caption("⚠️ Min too low!")
        with col6:
            if st.button("🗑️", key=f"del_{i}", help="Remove this debt"):
                to_delete = i

    if to_delete is not None:
        st.session_state.debts.pop(to_delete)
        st.rerun()

# ── SIMULATION & CHARTS ──────────────────────
if debts:
    st.markdown("<div class='section-header'>📈 Payoff Simulation</div>", unsafe_allow_html=True)

    total_monthly = total_min + extra
    timeline, events = simulate_payoff(debts, extra, strategy)

    if timeline:
        months_total = timeline[-1]["month"]
        total_interest = timeline[-1]["total_interest_paid"]
        payoff_date = (date.today() + timedelta(days=months_total * 30.4)).strftime("%B %Y")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🗓️ Debt-Free Date", payoff_date, f"{months_total} months ({months_total/12:.1f} yrs)")
        with col2:
            st.metric("💸 Total Interest Paid", f"${total_interest:,.0f}")
        with col3:
            st.metric("💰 Total Amount Paid", f"${total_balance + total_interest:,.0f}")

        # ── PAYOFF CURVE CHART ──
        months_list = [t["month"] for t in timeline]
        remaining_list = [t["total_remaining"] for t in timeline]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months_list, y=remaining_list,
            fill='tozeroy',
            line=dict(color='#00d4aa', width=2.5),
            fillcolor='rgba(0,212,170,0.08)',
            name='Total Remaining',
            hovertemplate='Month %{x}: $%{y:,.0f} remaining<extra></extra>'
        ))

        # Per-debt lines
        colors = ["#58a6ff", "#f85149", "#e3b341", "#a371f7", "#3fb950", "#ffa657"]
        for idx, d in enumerate(debts):
            per_debt = [t["balances"][idx] for t in timeline]
            fig.add_trace(go.Scatter(
                x=months_list, y=per_debt,
                line=dict(color=colors[idx % len(colors)], width=1.5, dash='dot'),
                name=d["name"],
                hovertemplate=f'{d["name"]} Month %{{x}}: $%{{y:,.0f}}<extra></extra>'
            ))

        fig.update_layout(
            paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
            font=dict(color='#8b949e', family='Sora'),
            xaxis=dict(title='Month', gridcolor='#21262d', color='#8b949e', zerolinecolor='#21262d'),
            yaxis=dict(title='Balance ($)', gridcolor='#21262d', color='#8b949e', tickprefix='$', zerolinecolor='#21262d'),
            legend=dict(bgcolor='#161b22', bordercolor='#30363d', borderwidth=1),
            title=dict(text='📉 Debt Payoff Timeline', font=dict(color='#e6edf3', size=16)),
            height=380,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── PAYOFF EVENTS ──
        if events:
            st.markdown("<div class='section-header'>🏁 Debt Payoff Milestones</div>", unsafe_allow_html=True)
            ev_df = pd.DataFrame(events)
            ev_df.columns = ["Debt", "Month #", "Payoff Date"]
            st.dataframe(ev_df, use_container_width=True, hide_index=True)

        # ── STRATEGY COMPARISON ──
        st.markdown("<div class='section-header'>⚖️ Strategy Comparison</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            tl_aval, _ = simulate_payoff(debts, extra, "Avalanche (Highest Interest First)")
            if tl_aval:
                st.markdown(f"""
                <div class='metric-card'>
                <div class='metric-label'>🔺 Avalanche Strategy</div>
                <div class='metric-value blue'>{tl_aval[-1]['month']} months</div>
                <div class='metric-delta'>Total interest: ${tl_aval[-1]['total_interest_paid']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            tl_snow, _ = simulate_payoff(debts, extra, "Snowball (Lowest Balance First)")
            if tl_snow:
                st.markdown(f"""
                <div class='metric-card'>
                <div class='metric-label'>⛄ Snowball Strategy</div>
                <div class='metric-value yellow'>{tl_snow[-1]['month']} months</div>
                <div class='metric-delta'>Total interest: ${tl_snow[-1]['total_interest_paid']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)

        if tl_aval and tl_snow:
            interest_diff = tl_snow[-1]['total_interest_paid'] - tl_aval[-1]['total_interest_paid']
            month_diff = tl_snow[-1]['month'] - tl_aval[-1]['month']
            if interest_diff > 0:
                st.markdown(f"""
                <div class='advisor-box'>
                <div class='advisor-title'>🧠 Comparison Insight</div>
                <div class='advisor-text'>
                The <strong>Avalanche method saves you ${interest_diff:,.0f}</strong> in interest 
                and gets you debt-free <strong>{abs(month_diff)} months sooner</strong> than Snowball. 
                However, if you have small balances you can wipe out quickly, Snowball can provide 
                early psychological wins that keep you on track — a motivated payer using Snowball 
                often beats an unmotivated payer on Avalanche.
                </div>
                </div>
                """, unsafe_allow_html=True)

        # ── EXTRA PAYMENT SENSITIVITY ──
        st.markdown("<div class='section-header'>🎚️ What If? — Extra Payment Impact</div>", unsafe_allow_html=True)
        
        extras_to_test = [0, 50, 100, 200, 300, 500, 750, 1000]
        sensitivity = []
        for ex in extras_to_test:
            tl, _ = simulate_payoff(debts, ex, strategy)
            if tl:
                sensitivity.append({
                    "Extra/mo": f"${ex:,}",
                    "Months": tl[-1]["month"],
                    "Years": round(tl[-1]["month"]/12, 1),
                    "Total Interest": f"${tl[-1]['total_interest_paid']:,.0f}",
                    "Interest Saved vs $0": f"${max(0, (tl[0]['total_interest_paid'] if len(tl)>0 else 0)):,.0f}"
                })
        
        if sensitivity:
            base_interest = None
            rows = []
            tl0, _ = simulate_payoff(debts, 0, strategy)
            base_interest = tl0[-1]['total_interest_paid'] if tl0 else 0
            
            sens_extras = []
            sens_months = []
            sens_interest = []
            for ex in extras_to_test:
                tl, _ = simulate_payoff(debts, ex, strategy)
                if tl:
                    sens_extras.append(ex)
                    sens_months.append(tl[-1]["month"])
                    sens_interest.append(tl[-1]["total_interest_paid"])

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=[f"${e:,}" for e in sens_extras],
                y=sens_months,
                marker_color=['#f85149' if m == max(sens_months) else '#00d4aa' if m == min(sens_months) else '#58a6ff' for m in sens_months],
                name='Months to Payoff',
                hovertemplate='Extra $%{x}/mo → %{y} months<extra></extra>'
            ))
            fig2.update_layout(
                paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
                font=dict(color='#8b949e', family='Sora'),
                xaxis=dict(title='Extra Monthly Payment', gridcolor='#21262d', color='#8b949e'),
                yaxis=dict(title='Months to Payoff', gridcolor='#21262d', color='#8b949e'),
                title=dict(text='Impact of Extra Payments on Payoff Timeline', font=dict(color='#e6edf3', size=15)),
                height=320,
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig2, use_container_width=True)

    else:
        st.markdown("<div class='warning-box'>⚠️ One or more minimum payments may be too low to cover interest — the debt would never be paid off. Please increase your minimum payments.</div>", unsafe_allow_html=True)

# ── SMART ADVISOR ────────────────────────────
st.markdown("<div class='section-header'>🧠 Your AI Financial Advisor</div>", unsafe_allow_html=True)

insights = advisor_insights(debts, income_m, extra, strategy)
for insight in insights:
    st.markdown(f"""
    <div class='advisor-box'>
    <div class='advisor-text'>{insight}</div>
    </div>
    """, unsafe_allow_html=True)

# ── FAST PAYOFF STRATEGIES ───────────────────
with st.expander("⚡ 10 Ways to Pay Off Debt Faster (W-2 Employee Edition)", expanded=False):
    st.markdown("""
    <div class='advisor-text'>

    **1. 🎯 Use Tax Refunds as a Lump Sum**  
    The average W-2 refund is $3,000+. Direct 100% to your highest-interest debt immediately in February/March each year.

    **2. 📅 Make Bi-Weekly Payments**  
    Pay half your monthly payment every 2 weeks instead of monthly. You'll make 26 half-payments = 13 full payments/year (1 extra!) — saving months off your timeline.

    **3. 💼 Negotiate a Raise → Dedicate It Entirely**  
    If you get a 5% raise, you weren't living on that money before. Throw 100% of the increase at debt until you're free.

    **4. 💳 Balance Transfer (Credit Cards)**  
    Move high-rate credit card balances to a 0% APR promotional card (usually 12-18 months). Pay aggressively with zero interest going to the principal.

    **5. 🏠 Refinance Your Mortgage**  
    If rates dropped since you got your mortgage, refinancing to a lower rate or shorter term saves tens of thousands. Check if the break-even period makes sense for you.

    **6. 📊 Request a Credit Limit Increase (Don't Spend It)**  
    Improves your credit utilization ratio → raises your credit score → qualifies you for lower-rate refinancing or balance transfers.

    **7. 🛍️ Sell Unused Assets**  
    Old car, gear, electronics, clothes. Even $500 applied to a high-interest balance removes $100+/year in interest immediately.

    **8. 💡 Reduce Lifestyle Inflation**  
    Every $100/month in spending cuts = $1,200/year extra toward debt. Track 3 months of spending — most people find 10-15% they don't notice or care about.

    **9. 🎁 Apply Bonuses, RSUs, and Overtime 100%**  
    W-2 employees often receive year-end bonuses or overtime pay. Treat these as windfalls, not income — send them straight to debt.

    **10. 📈 Request W-4 Adjustment**  
    If you're getting a large tax refund, you're giving the IRS an interest-free loan. Adjust your W-4 to get that money monthly — then apply it to debt immediately instead of waiting for refund season.

    </div>
    """, unsafe_allow_html=True)

# ── EMPTY STATE ──────────────────────────────
if not debts:
    st.markdown("""
    <div style='text-align:center;padding:4rem 2rem;'>
      <div style='font-size:4rem;'>💳</div>
      <div style='font-size:1.4rem;font-weight:600;color:#e6edf3;margin-top:1rem;'>Ready to Become Debt-Free?</div>
      <div style='color:#8b949e;margin-top:0.5rem;max-width:500px;margin-left:auto;margin-right:auto;'>
        Start by entering your income on the left, then add your debts (car loans, credit cards, mortgage, etc.) 
        to get your personalized payoff plan and smart advisor recommendations.
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#484f58;font-size:0.78rem;padding:1rem;'>
DebtFree Advisor • For informational purposes only • Not a substitute for licensed financial advice<br>
Built for W-2 employees working toward financial freedom 💪
</div>
""", unsafe_allow_html=True)
