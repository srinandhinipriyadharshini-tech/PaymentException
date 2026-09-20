from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Clearline Operations", page_icon=":shield:", layout="wide", initial_sidebar_state="expanded")

HISTORY_PATH = Path(__file__).resolve().parent / "traces" / "case_history.json"

CASES = [
    {"Case ID": "EXC-24091", "Customer": "Maya Patel", "Amount": "GBP 1,250", "Rail": "ACH", "Intent": "Authorised scam", "Confidence": 94, "Age": 18, "Merchant": "Northwind Supplies Ltd", "Date": "02 Jan 2026", "Risk": 12, "Request": "IR-ACH-8F41C2"},
    {"Case ID": "EXC-24088", "Customer": "Jordan Lee", "Amount": "GBP 73,000", "Rail": "WIRE", "Intent": "Unauthorised", "Confidence": 89, "Age": 47, "Merchant": "Northwind Supplies Ltd", "Date": "20 Jul 2026", "Risk": 28, "Request": "IR-WIR-2B01A9"},
    {"Case ID": "EXC-24083", "Customer": "Sam Rivera", "Amount": "GBP 3,200", "Rail": "RTP", "Intent": "No remedy", "Confidence": 97, "Age": 68, "Merchant": "Cedar Works Inc", "Date": "05 Sep 2026", "Risk": 8, "Request": "N/A"},
    {"Case ID": "EXC-24079", "Customer": "Alex Morgan", "Amount": "GBP 9,000", "Rail": "ACH", "Intent": "Erroneous", "Confidence": 91, "Age": 32, "Merchant": "Blue Oak Services Ltd", "Date": "25 Jul 2026", "Risk": 19, "Request": "IR-ACH-35D8AA"},
]


def load_customer_cases() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        saved = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    cases = []
    for customer, history in saved.get("histories", {}).items():
        for raw in history:
            payment = raw.get("selected_payment")
            deadline = raw.get("deadline")
            payment = payment or {}
            payment_date = payment.get("value_date", "")
            age = max((date.today() - date.fromisoformat(payment_date)).days, 0) if payment_date else 0
            case_status = raw.get("case_status", "READY_FOR_REVIEW")
            request_status = raw.get("request_status", "NOT_CREATED")
            remedy = raw.get("remedy") or {}
            remedy_available = remedy.get("available", raw.get("remedy_available", False))
            if case_status == "CLARIFICATION_REQUIRED":
                state = "Needs Clarification"
            elif case_status == "ESCALATED":
                state = "Escalated"
            elif case_status in {"NO_REMEDY", "CLOSED"} or not remedy_available:
                state = "No-Remedy"
            elif case_status == "SUBMITTED_SIMULATED":
                state = "Simulated Request Raised"
            elif request_status == "AGENT_APPROVED":
                state = "Agent Approved"
            else:
                state = "Ready For Review"
            cases.append({
                "Case ID": raw.get("case_id", "Unknown"),
                "Customer": customer,
                "Amount": f"{payment.get('currency', '')} {payment.get('amount', '')}" if payment else "Not matched",
                "Rail": payment.get("rail", "Unknown"),
                "Intent": raw.get("category") or raw.get("claim_category") or "Unclassified",
                "Confidence": round(float(raw.get("confidence", 0)) * 100),
                "Age": age,
                "Merchant": payment.get("creditor_trading_name", "Not matched"),
                "Date": payment_date,
                "Risk": 0,
                "Request": raw.get("reference_id") or "N/A",
                "State": state,
                "SLA": "No remedy" if state == "No-Remedy" else f"{max((date.fromisoformat(deadline) - date.today()).days, 0)}d remaining" if deadline else "Awaiting match" if state == "Needs Clarification" else "No deadline",
            })
    return cases


def state_for(case: dict, age: int) -> str:
    if case["Rail"] in {"RTP", "FEDNOW"} or age > 60:
        return "No-Remedy"
    if age >= 46:
        return "Escalated"
    return "Simulated Request Raised"


def sla_for(case: dict, age: int) -> str:
    if case["Rail"] in {"RTP", "FEDNOW"}:
        return "Rail finality"
    if age > 60:
        return "Window exceeded"
    return f"{60 - age}d remaining"


def badge(value: str) -> str:
    class_name = {"Simulated Request Raised": "good", "Escalated": "warn", "No-Remedy": "bad"}.get(value, "neutral")
    return f'<span class="badge {class_name}">{value}</span>'


def can_admin_approve(state: str) -> bool:
    return state == "Escalated"


def can_admin_close(state: str) -> bool:
    return state == "No-Remedy"


def metric(label: str, value: str, detail: str, tone: str) -> None:
    st.markdown(f'<div class="metric"><div class="metric-label">{label}<span class="metric-mark {tone}"></span></div><div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>', unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
    :root { --ink:#182d4b; --muted:#647995; --line:#d5e3f0; --panel:#ffffff; --cyan:#008f86; --amber:#d77a16; --red:#d84f5b; }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp { color:var(--ink); background:#f4f9fd; background-image:radial-gradient(circle at 8% -8%,rgba(240,111,94,.2),transparent 30%),radial-gradient(circle at 92% 0%,rgba(71,143,236,.15),transparent 28%),linear-gradient(rgba(35,74,112,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(35,74,112,.035) 1px,transparent 1px),linear-gradient(135deg,#eaf5ff 0%,#ffffff 54%,#e3faf4 100%); background-size:auto,auto,48px 48px,48px 48px,auto; background-attachment:fixed; }
    [data-testid="stAppViewContainer"] > .main { background:transparent; }
    [data-testid="stHeader"] { background:rgba(244,249,253,.82); }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#e9f4ff 0%,#f8fcff 55%,#e7faf5 100%); border-right:1px solid #cbdceb; }
    [data-testid="stSidebar"] * { color:var(--ink); }
    [data-testid="stSidebar"] h1 { letter-spacing:.08em; font-size:17px; }
    h1 { font-size:29px !important; letter-spacing:-.05em; } h2 { letter-spacing:-.04em; } h3 { letter-spacing:-.03em; }
    .eyebrow { color:#39718d; text-transform:uppercase; letter-spacing:.16em; font-size:10px; font-weight:800; }
    .subtle { color:var(--muted); font-size:12px; }
    .sandbox { border:1px solid var(--accent); border-radius:12px; padding:17px 20px 13px; background:linear-gradient(100deg,var(--accent-soft),rgba(255,255,255,.92) 70%); box-shadow:0 10px 24px rgba(40,83,126,.08); }
    .sandbox.green { --accent:var(--cyan); --accent-soft:rgba(88,212,205,.2); } .sandbox.amber { --accent:var(--amber); --accent-soft:rgba(234,183,106,.2); } .sandbox.red { --accent:var(--red); --accent-soft:rgba(239,116,124,.18); }
    .sandbox-title { color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-size:10px; font-weight:800; }
    .sandbox h3 { margin:7px 0 2px; font-size:17px; } .sandbox p { margin:0; color:var(--muted); font-size:11px; }
    .sandbox-readout { color:var(--accent); font:11px 'DM Mono'; text-align:right; }
    .metric { border:1px solid var(--line); border-radius:9px; background:rgba(255,255,255,.92); padding:15px 16px; min-height:105px; box-shadow:0 7px 18px rgba(40,83,126,.07); }
    .metric-label { color:#627994; font-size:11px; display:flex; justify-content:space-between; } .metric-mark { width:9px; height:9px; border-radius:50%; } .metric-mark.cyan { background:var(--cyan); box-shadow:0 0 9px var(--cyan); } .metric-mark.amber { background:var(--amber); box-shadow:0 0 9px var(--amber); } .metric-mark.red { background:var(--red); box-shadow:0 0 9px var(--red); }
    .metric-value { font-size:28px; font-weight:800; margin:12px 0 2px; } .metric-detail { color:#607995; font-size:10px; }
    .panel { border:1px solid #d5e3f0; border-radius:9px; background:rgba(255,255,255,.92); padding:16px; }
    .panel-title { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; } .panel-title h3 { margin:0; font-size:15px; }
    .badge { display:inline-block; padding:5px 7px; border-radius:4px; font-size:10px; font-weight:700; } .badge.good { color:#00786f; background:#d8f7f0; } .badge.warn { color:#a35f00; background:#fff0cf; } .badge.bad { color:#b33543; background:#ffe5e8; }
    .audit-block { border:1px solid #d5e3f0; border-radius:9px; background:rgba(255,255,255,.94); padding:16px; margin-bottom:12px; box-shadow:0 7px 18px rgba(40,83,126,.06); }
    .audit-block h4 { margin:0 0 5px; font-size:12px; } .audit-block p { color:#5e7490; font-size:11px; line-height:1.5; margin:6px 0 0; }
    .terminal { background:#edf5fb; border:1px solid #c9ddeb; border-radius:6px; padding:11px; color:#496681; font:10px/1.65 'DM Mono'; margin-top:12px; } .terminal b { color:#007d75; font-weight:500; }
    .risk { color:var(--cyan); font-size:27px; font-weight:800; } .recommendation { border-left:2px solid #7564d8; padding-left:10px; margin-top:13px; }
    .recommendation strong { color:#6354bd; font:10px 'DM Mono'; text-transform:uppercase; } .recommendation p { margin-top:5px; }
    .stDataFrame { border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    div[data-testid="stMetricValue"] { color:var(--ink); } .stButton button { border-radius:6px; }
    </style>
    """, unsafe_allow_html=True)


def render_secondary_view(view: str) -> None:
    view_details = {
        "Live orchestration": ("Live orchestration", "Watch the agent mesh route, pause, and escalate payment exceptions in real time."),
        "Policy controls": ("Policy controls", "Review the deterministic rules that govern recovery, review, and rail finality."),
        "Risk analytics": ("Risk analytics", "Inspect classification drift, triage volatility, and the signals behind manual review."),
        "Audit ledger": ("Audit ledger", "Trace every autonomous recommendation and human approval checkpoint."),
    }
    title, subtitle = view_details[view]
    st.markdown(f'<div class="eyebrow">● Operations / {view}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="subtle">{subtitle}</p>', unsafe_allow_html=True)

    if view == "Live orchestration":
        metrics = st.columns(4)
        with metrics[0]: metric("Active agents", "04", "All deterministic nodes online", "cyan")
        with metrics[1]: metric("Claims in flight", "12", "+4 since last hour", "amber")
        with metrics[2]: metric("Auto-routed", "87%", "Within confidence threshold", "cyan")
        with metrics[3]: metric("Human handoffs", "03", "Awaiting operator decision", "red")
        left, right = st.columns([1.2, .8])
        with left:
            st.markdown("### Agent activity feed")
            activity = pd.DataFrame([
                {"Time": "09:42:18", "Agent": "Policy guard", "Event": "60-day window validated for EXC-24091", "Status": "PASS"},
                {"Time": "09:41:52", "Agent": "Matching agent", "Event": "Northwind Supplies Ltd ranked 1 of 48", "Status": "94% MATCH"},
                {"Time": "09:41:27", "Agent": "Risk agent", "Event": "Behavioral profile attached to EXC-24088", "Status": "REVIEW"},
                {"Time": "09:40:03", "Agent": "Rail rules", "Event": "RTP finality applied to EXC-24083", "Status": "BLOCKED"},
            ])
            st.dataframe(activity, use_container_width=True, hide_index=True)
        with right:
            st.markdown("### Agent mesh")
            for name, detail, state in [("Intake agent", "Extracting claim facts", "Healthy"), ("Matching agent", "Ranking payment candidates", "Healthy"), ("Policy agent", "Evaluating SLA and rail", "Healthy"), ("Risk agent", "Preparing human context", "Healthy")]:
                st.markdown(f'<div class="audit-block"><h4>{name} <span class="badge good">{state}</span></h4><p>{detail}</p></div>', unsafe_allow_html=True)
        return

    if view == "Policy controls":
        st.markdown("### Active rulebook")
        rules = pd.DataFrame([
            {"Control": "Recovery window", "Rule": "Payment age must be 60 days or less", "Outcome": "Raise simulated request"},
            {"Control": "Instant rail finality", "Rule": "RTP and FEDNOW cannot expose recovery remedy", "Outcome": "No-Remedy"},
            {"Control": "Ambiguous match", "Rule": "Leading candidates must clear the ambiguity band", "Outcome": "Clarification required"},
            {"Control": "Human approval", "Rule": "Agent approval required before submission", "Outcome": "Manual checkpoint"},
        ])
        st.dataframe(rules, use_container_width=True, hide_index=True)
        st.info("These controls are deterministic synthetic rules. AI layers may recommend an action, but they cannot bypass a policy gate.")
        return

    if view == "Risk analytics":
        left, right = st.columns(2)
        with left:
            st.markdown("### Classification overrides")
            st.bar_chart(pd.DataFrame({"AI initial": [42, 31, 23, 18], "Human adjustment": [8, 5, 7, 3]}, index=["Unauthorised", "Erroneous", "Scam", "No remedy"]), color=["#008f86", "#7564d8"])
        with right:
            st.markdown("### Triage volatility")
            st.line_chart(pd.DataFrame({"Auto-resolved": [14, 19, 17, 26, 23, 31], "Escalated": [4, 7, 9, 6, 11, 8], "No-remedy": [2, 3, 5, 4, 8, 6]}, index=["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]), color=["#008f86", "#d77a16", "#d84f5b"])
        st.markdown("### Signal interpretation")
        st.success("Human override rate is 16.8%. The largest adjustment cluster is authorised-scam versus erroneous intent, so those cases remain prioritized for audit context.")
        return

    st.markdown("### Recent audit decisions")
    if st.session_state.admin_history:
        st.dataframe(pd.DataFrame(st.session_state.admin_history), use_container_width=True, hide_index=True)
    else:
        st.info("No admin decisions recorded in this session.")
    st.caption("Ledger entries are session records. No real bank or payment network is contacted.")


def main() -> None:
    inject_css()
    if "email_events" not in st.session_state:
        st.session_state.email_events = []
    if "admin_decisions" not in st.session_state:
        st.session_state.admin_decisions = {}
    if "admin_history" not in st.session_state:
        st.session_state.admin_history = []
    if "admin_cases" not in st.session_state:
        st.session_state.admin_cases = load_customer_cases()
    st.sidebar.markdown("# Clearline")
    st.sidebar.caption("OPERATIONS CONSOLE")
    workspace = st.sidebar.selectbox("Workspace", ["Operations workspace", "Audit workspace"], label_visibility="collapsed")
    st.sidebar.markdown("### CONTROL CENTRE")
    selected_view = st.sidebar.radio("Navigate", ["Exception queue", "Live orchestration", "Policy controls", "Risk analytics", "Audit ledger"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.success("Agent mesh healthy\n\n4 deterministic nodes online")
    st.sidebar.caption("Riya Kapoor · Principal operator")
    if st.sidebar.button("Clear history", width="stretch"):
        st.session_state.email_events = []
        st.session_state.admin_decisions = {}
        st.session_state.admin_history = []
        st.session_state.admin_cases = []
        st.rerun()
    if st.sidebar.button("Refresh customer cases", width="stretch"):
        st.session_state.admin_cases = load_customer_cases()
        st.rerun()

    if workspace == "Audit workspace":
        render_secondary_view("Audit ledger")
        return
    if selected_view != "Exception queue":
        render_secondary_view(selected_view)
        return

    st.markdown('<div class="eyebrow">● Operations / Exception queue</div>', unsafe_allow_html=True)
    st.title("Core payment exceptions")
    st.markdown('<p class="subtle">Human-in-the-loop recovery control for high-signal disputes.</p>', unsafe_allow_html=True)

    age = st.slider("Simulate transaction age (SLA tester)", min_value=10, max_value=70, value=18, help="Warp the case clock to validate the 60-day deadline guard.")
    current_state = "No-Remedy" if age > 60 else "Escalated" if age >= 46 else "Simulated Request Raised"
    tone = "red" if current_state == "No-Remedy" else "amber" if current_state == "Escalated" else "green"
    st.markdown(f'<div class="sandbox {tone}"><div class="sandbox-title">Regulatory sandbox · LIVE</div><h3>Day {age} · {"NO-REMEDY ACTIVE" if tone == "red" else "APPROACHING DEADLINE" if tone == "amber" else "WITHIN SAFE WINDOW"}</h3><p>All cases below are evaluated against the same deterministic 60-day policy clock.</p><div class="sandbox-readout">Recovery posture: {"No-remedy active" if tone == "red" else "Analyst attention" if tone == "amber" else "Automatic path"}</div></div>', unsafe_allow_html=True)
    st.progress(min(age / 60, 1.0), text=f"SLA consumption: {age}/60 days")

    enriched = []
    for item in st.session_state.admin_cases:
        row = dict(item)
        if item.get("State") in {"Ready For Review", "Agent Approved"}:
            row["State"] = item["State"]
        else:
            row["State"] = state_for(item, age) if item.get("State") == "Simulated Request Raised" else item["State"]
        row["SLA"] = item.get("SLA") or sla_for(item, age)
        row["Decision"] = st.session_state.admin_decisions.get(item["Case ID"], "Pending admin action" if row["State"] == "Escalated" else "Not required")
        enriched.append(row)
    escalated = sum(item["State"] == "Escalated" for item in enriched)
    active = sum(item["State"] == "Simulated Request Raised" for item in enriched)
    blocked = sum(item["State"] == "No-Remedy" for item in enriched)
    metrics = st.columns(4)
    with metrics[0]: metric("Escalated cases", str(escalated), "Awaiting admin decision", "amber")
    with metrics[1]: metric("Active simulated requests", str(active), "From customer workspace", "cyan")
    with metrics[2]: metric("No-remedy decisions", str(blocked), "Rail finality or expired SLA", "red")
    with metrics[3]: metric("Voice agent activity", "03", "+12% live · active calls", "cyan")

    st.markdown("## Cases requiring orchestration")
    filters = st.columns([2, 1, 1])
    with filters[0]: query = st.text_input("Search case, customer or beneficiary", placeholder="Search the queue", label_visibility="collapsed")
    with filters[1]: rail = st.selectbox("Rail", ["All rails", "ACH", "WIRE", "RTP", "FEDNOW"], label_visibility="collapsed")
    with filters[2]: status = st.selectbox("State", ["All states", "Needs Clarification", "Escalated", "Ready For Review", "Agent Approved", "Simulated Request Raised", "No-Remedy"], label_visibility="collapsed")
    visible = [item for item in enriched if (not query or query.lower() in str(item).lower()) and (rail == "All rails" or item["Rail"] == rail) and (status == "All states" or item["State"] == status)]
    table = pd.DataFrame([{key: item[key] for key in ["Case ID", "Customer", "Amount", "Rail", "Intent", "State", "Decision", "SLA"]} for item in visible])
    st.dataframe(table, use_container_width=True, hide_index=True, column_config={"State": st.column_config.TextColumn("State"), "Confidence": st.column_config.ProgressColumn("Match", min_value=0, max_value=100)})

    if not visible:
        st.info("No customer cases are available. Submit a case in the customer workspace or use Refresh customer cases.")
        return
    selected_id = st.selectbox("Deep-dive case", [item["Case ID"] for item in visible], label_visibility="collapsed")
    selected = next(item for item in enriched if item["Case ID"] == selected_id)
    st.markdown("## Deep-dive audit")
    left, right = st.columns([1.08, .92])
    with left:
        st.markdown(f'<div class="audit-block"><div class="eyebrow">Selected case</div><h4>{selected["Case ID"]} · {selected["Customer"]}</h4><p><strong>{selected["Amount"]}</strong> to {selected["Merchant"]} via {selected["Rail"]}<br>{selected["Date"]} · {badge(selected["State"])} · {selected["SLA"]}</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="audit-block"><h4>AI cognitive routing & vector match</h4><p>Cosine similarity match confidence: <strong>{selected["Confidence"]}%</strong></p><div class="terminal"><b>route</b> payment intelligence / claimant history / rail rules<br><b>match</b> User stated beneficiary and amount. Found closest match <strong>{selected["Merchant"]}</strong>. Date tolerance window accepted. Cross-referencing trading names...<br><b>guard</b> 60-day policy gate: <strong>{"BLOCKED" if selected["State"] == "No-Remedy" else "REVIEW" if selected["State"] == "Escalated" else "PASS"}</strong></div></div>', unsafe_allow_html=True)
    with right:
        recommendation = "Preserve evidence and route to policy exception review. Do not raise a recovery request." if selected["State"] == "No-Remedy" else "Hold for senior analyst review before the SLA window closes." if selected["State"] == "Escalated" else "Safe to approve simulated interbank recovery request."
        st.markdown(f'<div class="audit-block"><h4>Agentic smart audit verdict</h4><p>Multi-agent pre-flight · 3 checks complete</p><div class="risk">{selected["Risk"]}% <span style="font-size:11px;color:#78909e;font-weight:400">fraud risk · {"LOW" if selected["Risk"] < 20 else "MODERATE"}</span></div><p><strong>Behavioral flag</strong><br>Customer profile is stable. No past buyer remorse claims detected in 12 months.</p><div class="recommendation"><strong>System recommendation</strong><p>{recommendation}</p></div></div>', unsafe_allow_html=True)
        decision = st.session_state.admin_decisions.get(selected["Case ID"])
        if can_admin_approve(selected["State"]) and decision != "Admin approved":
            if st.button("Approve simulated request", type="primary", use_container_width=True):
                recipient = selected["Customer"].lower().replace(" ", ".") + "@example.test"
                st.session_state.admin_decisions[selected["Case ID"]] = "Admin approved"
                st.session_state.admin_history.append({"Case": selected["Case ID"], "Verdict": "Admin approved", "Operator": "Riya Kapoor", "Evidence": "Escalated case approved; customer email triggered"})
                st.session_state.email_events.append({"Case": selected["Case ID"], "Recipient": recipient, "Subject": f"Payment exception update - {selected['Case ID']}"})
                st.success(f"Simulated request {selected['Request']} approved and customer email triggered for {recipient}. No guaranteed recovery.")
        elif decision == "Admin approved":
            st.success("Admin approval recorded and customer email already triggered.")
        elif can_admin_close(selected["State"]):
            st.error("Request blocked by policy: no late request or final-rail recovery request will be raised automatically.")
            if st.button("Close as no remedy", type="secondary", use_container_width=True):
                st.session_state.admin_decisions[selected["Case ID"]] = "Closed as no remedy"
                st.session_state.admin_history.append({"Case": selected["Case ID"], "Verdict": "Closed as no remedy", "Operator": "Riya Kapoor", "Evidence": "No-remedy policy decision"})
                st.success(f"Case {selected['Case ID']} closed as no remedy.")
        else:
            st.info("Agent-approved case: admin approval is not required.")
        with st.expander("Customer notification"):
            recipient = selected["Customer"].lower().replace(" ", ".") + "@example.test"
            st.caption("Simulated email channel")
            st.text_input("Recipient", value=recipient, disabled=True, key=f"email_recipient_{selected['Case ID']}")
            st.text_input("Subject", value=f"Payment exception update - {selected['Case ID']}", disabled=True, key=f"email_subject_{selected['Case ID']}")
            email_body = f"We reviewed your {selected['Rail']} payment of {selected['Amount']} to {selected['Merchant']}. Current outcome: {selected['State']}. No guaranteed recovery is implied."
            st.text_area("Message preview", value=email_body, height=90, disabled=True, key=f"email_body_{selected['Case ID']}")
            if st.session_state.admin_decisions.get(selected["Case ID"]) == "Admin approved":
                st.success(f"Customer email triggered for {recipient}. No external email was sent.")
            else:
                st.caption("Customer email is triggered automatically after admin approval of an escalated case.")

    st.markdown("## Operations analytics")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("### Classification overrides")
        st.bar_chart(pd.DataFrame({"AI initial": [42, 31, 23, 18], "Human adjustment": [8, 5, 7, 3]}, index=["Unauthorised", "Erroneous", "Scam", "No remedy"]), color=["#58d4cd", "#9c8cf5"])
    with chart_right:
        st.markdown("### Triage volatility")
        st.line_chart(pd.DataFrame({"Auto-resolved": [14, 19, 17, 26, 23, 31], "Escalated": [4, 7, 9, 6, 11, 8], "No-remedy": [2, 3, 5, 4, 8, 6]}, index=["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]), color=["#58d4cd", "#eab76a", "#ef747c"])


if __name__ == "__main__":
    main()