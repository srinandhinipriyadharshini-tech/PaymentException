from __future__ import annotations

from datetime import date, datetime, timedelta
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from theme import note


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
            message_type = remedy.get("message_type", "none")
            request_type = "Recall request" if "recall" in message_type.lower() else "Return request" if "return" in message_type.lower() else "No request"
            if case_status == "CLOSED":
                state = "Closed"
            elif case_status == "CLARIFICATION_REQUIRED":
                state = "Needs Clarification"
            elif case_status == "ESCALATED":
                state = "Escalated"
            elif case_status == "NO_REMEDY" or not remedy_available:
                state = "No-Remedy"
            elif case_status == "SUBMITTED_SIMULATED":
                state = "Request Raised"
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
                "Request Type": request_type,
            })
    return cases


def approval_reference(case: dict) -> str:
    rail = case.get("Rail", "PAY")
    case_id = case.get("Case ID", "UNKNOWN")
    return f"SIM-{rail}-{case_id[-6:]}"


def customer_email(case: dict) -> str:
    return selected_email(case)


def selected_email(case: dict) -> str:
    name = case.get("Customer", "customer").lower().replace(" ", ".")
    local_part = name.split(".")[0]
    return f"{local_part[0]}***@example.test"


def persist_case_decision(case: dict, reference_id: str, request_status: str, case_status: str | None = None) -> None:
    try:
        saved = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    approved_at = datetime.now().isoformat()
    for history in saved.get("histories", {}).values():
        for raw in history:
            if raw.get("case_id") != case.get("Case ID"):
                continue
            raw["reference_id"] = reference_id
            raw["approved_at"] = approved_at
            raw["last_updated_at"] = approved_at
            raw["request_status"] = request_status
            if case_status:
                raw["case_status"] = case_status
            elif request_status == "SIMULATED_SUBMITTED":
                raw["case_status"] = "SUBMITTED_SIMULATED"
            HISTORY_PATH.write_text(json.dumps(saved, indent=2), encoding="utf-8")
            return

def state_for(case: dict, age: int) -> str:
    if case["Rail"] in {"RTP", "FEDNOW"} or age > 60:
        return "No-Remedy"
    if age >= 46:
        return "Escalated"
    return "Request Raised"


def policy_state(case: dict, age: int) -> str:
    current_state = case.get("State", "Needs Clarification")
    if current_state == "Closed":
        return "Closed"
    if current_state == "Escalated" and (case.get("Rail") in {"RTP", "FEDNOW"} or age > 60):
        return "No-Remedy"
    if current_state == "Simulated Request Raised":
        return state_for(case, age)
    return current_state


def sla_for(case: dict, age: int) -> str:
    if case["Rail"] in {"RTP", "FEDNOW"}:
        return "Rail finality"
    if age > 60:
        return "Window exceeded"
    return f"{60 - age}d remaining"


def badge(value: str) -> str:
    class_name = {"Simulated Request Raised": "good", "Request Raised": "good", "Return Request Raised": "good", "Recall Request Raised": "good", "Escalated": "warn", "No-Remedy": "bad"}.get(value, "neutral")
    return f'<span class="badge {class_name}">{value}</span>'


def can_admin_approve(state: str) -> bool:
    return state == "Escalated"


def can_admin_close(state: str) -> bool:
    return state == "No-Remedy"


def sync_sla_age_to_case() -> None:
    selected_id = st.session_state.get("deep_dive_case")
    selected_case = next((case for case in st.session_state.admin_cases if case["Case ID"] == selected_id), None)
    if selected_case:
        st.session_state.sla_age = int(selected_case.get("Age", 18))


def _amount_value(value: str) -> float:
    match = re.search(r"[-\d,]+(?:\.\d+)?", value)
    return float(match.group(0).replace(",", "")) if match else 0.0


def _queue_status(case: dict) -> str:
    state = case.get("State", "Ready For Review")
    if state in {"No-Remedy", "Closed"}:
        return "breached" if state == "No-Remedy" else "released"
    if state == "Escalated":
        return "hold"
    if state in {"Request Raised", "Return Request Raised", "Recall Request Raised", "Simulated Request Raised"}:
        return "released"
    return "review"


def render_exception_queue() -> None:
    from theme import exception_row

    page_header("Exception queue", "Payments stopped before settlement. Oldest first - items past SLA are marked.")
    cases = st.session_state.admin_cases
    if not cases:
        queue_band(0, "GBP 0", "None", 0, {"0-30 days": 0, "31-45 days": 0, "46-60 days": 0, "Past SLA": 0})
        note("No payments are held right now", "Nothing needs your attention.", "info")
        return

    age = st.session_state.get("sla_age", max(item.get("Age", 0) for item in cases))
    enriched = []
    for item in cases:
        row = dict(item)
        row["State"] = policy_state(item, age)
        row["SLA"] = item.get("SLA") or sla_for(item, age)
        row["Decision"] = st.session_state.admin_decisions.get(item["Case ID"], "Pending admin action" if row["State"] == "Escalated" else "Not required")
        enriched.append(row)

    visible = sorted(enriched, key=lambda item: item.get("Age", 0), reverse=True)
    state_filter = st.session_state.get("queue_state_filter", "All states")
    rail_filter = st.session_state.get("queue_rail_filter", "All rails")
    customer_filter = st.session_state.get("queue_customer_filter", "All customers")
    visible = [
        item for item in visible
        if (state_filter == "All states" or item["State"] == state_filter)
        and (rail_filter == "All rails" or item["Rail"] == rail_filter)
        and (customer_filter == "All customers" or item["Customer"] == customer_filter)
    ]
    aging = {
        "0-30 days": sum(item.get("Age", 0) <= 30 for item in enriched),
        "31-45 days": sum(31 <= item.get("Age", 0) <= 45 for item in enriched),
        "46-60 days": sum(46 <= item.get("Age", 0) <= 60 for item in enriched),
        "Past SLA": sum(item.get("Age", 0) > 60 for item in enriched),
    }
    queue_band(
        len(enriched),
        f"GBP {sum(_amount_value(item.get('Amount', '')) for item in enriched):,.2f}",
        f"{max(item.get('Age', 0) for item in enriched)} days",
        aging["Past SLA"],
        aging,
    )

    st.sidebar.markdown("# Clearline")
    st.sidebar.caption("Operations queue")
    st.sidebar.selectbox("View", ["Queue", "Assigned to me", "Closed today"], key="queue_view")
    st.sidebar.selectbox("State", ["All states", "Escalated", "No-Remedy", "Ready For Review", "Request Raised", "Closed"], key="queue_state_filter")
    st.sidebar.selectbox("Rail", ["All rails", "ACH", "WIRE", "RTP", "FEDNOW"], key="queue_rail_filter")
    st.sidebar.selectbox("Customer", ["All customers"] + sorted({item["Customer"] for item in enriched}), key="queue_customer_filter")

    st.markdown("## Queue")
    if not visible:
        note("No matching payments", "Try a different sidebar filter.", "info")
        return
    shown = visible[:8]
    for item in shown:
        if st.button(f"{item['Case ID']} · {item['Customer']}", key=f"queue_case_{item['Case ID']}", type="secondary", width="stretch"):
            st.session_state.deep_dive_case = item["Case ID"]
        exception_row(item["Case ID"], item["Amount"], item["Intent"], f"{item['Age']} days", _queue_status(item))
    if len(visible) > 8:
        with st.expander(f"Show all {len(visible)} payments"):
            for item in visible[8:]:
                exception_row(item["Case ID"], item["Amount"], item["Intent"], f"{item['Age']} days", _queue_status(item))

    selected_id = st.session_state.get("deep_dive_case", shown[0]["Case ID"])
    selected = next((item for item in enriched if item["Case ID"] == selected_id), shown[0])
    st.markdown("## Selected payment")
    left, right = st.columns([3, 2], gap="large")
    with left:
        recommendation = (
            f"I found a {selected['Rail']} payment for {selected['Amount']} to {selected['Merchant']}. "
            f"The payment is {selected['Age']} days old and is currently {selected['State']}. "
            f"The evidence is a {selected['Confidence']}% match based on the stated amount, date, and beneficiary. "
            f"The recommended next step is to preserve the evidence and follow the configured policy."
        )
        note("Analyst recommendation", recommendation, "hold" if selected["State"] in {"Escalated", "No-Remedy"} else "info")
        if can_admin_approve(selected["State"]):
            if st.button("Release payment", type="primary", use_container_width=True):
                reference_id = approval_reference(selected)
                persist_case_decision(selected, reference_id, "SIMULATED_SUBMITTED")
                st.session_state.admin_decisions[selected["Case ID"]] = "Admin approved"
                st.session_state.email_events.append({"Case": selected["Case ID"], "Recipient": customer_email(selected), "Subject": f"Payment exception update - {selected['Case ID']}", "Reference": reference_id})
                st.rerun()
        elif can_admin_close(selected["State"]):
            if st.button("Close case", type="primary", use_container_width=True):
                reference_id = approval_reference(selected)
                persist_case_decision(selected, reference_id, "NOT_AVAILABLE", "CLOSED")
                st.session_state.admin_decisions[selected["Case ID"]] = "Closed as no remedy"
                st.rerun()
        if st.button("Escalate", type="secondary", use_container_width=True):
            note("Escalation recorded", "The payment remains held for senior analyst review.", "hold")
    with right:
        st.metric("Match score", f"{selected['Confidence']}%")
        st.metric("Payment age", f"{selected['Age']} days")


def analytics_frames(cases: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    category_labels = ["UNAUTHORISED", "ERRONEOUS", "AUTHORISED_BUT_SCAMMED", "NO_REMEDY"]
    state_labels = ["Needs Clarification", "Escalated", "Ready For Review", "Request Raised", "Return Request Raised", "Recall Request Raised", "Simulated Request Raised", "Manual Review Approved", "No-Remedy"]
    category_counts = pd.Series([str(item.get("Intent", "NO_REMEDY")) for item in cases]).value_counts() if cases else pd.Series(dtype="int64")
    state_counts = pd.Series([item.get("State", "Needs Clarification") for item in cases]).value_counts() if cases else pd.Series(dtype="int64")
    classification = pd.DataFrame({"Cases": [int(category_counts.get(label, 0)) for label in category_labels]}, index=category_labels)
    states = pd.DataFrame({"Cases": [int(state_counts.get(label, 0)) for label in state_labels]}, index=state_labels)
    return classification, states


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
        cases = st.session_state.get("admin_cases", [])
        claims_in_flight = sum(item.get("State") not in {"Closed", "No-Remedy"} for item in cases)
        average_confidence = round(sum(item.get("Confidence", 0) for item in cases) / len(cases)) if cases else 0
        human_handoffs = sum(item.get("State") in {"Escalated", "No-Remedy"} for item in cases)
        metrics = st.columns(4)
        with metrics[0]: metric("Active agents", "04", "All deterministic nodes online", "cyan")
        with metrics[1]: metric("Claims in flight", str(claims_in_flight), "Loaded customer cases", "amber")
        with metrics[2]: metric("Average match", f"{average_confidence}%", "Across loaded customer cases", "cyan")
        with metrics[3]: metric("Human handoffs", str(human_handoffs), "Escalated or blocked cases", "red")
        left, right = st.columns([1.2, .8])
        with left:
            st.markdown("### Agent activity feed")
            activity = pd.DataFrame([
                {
                    "Case": item.get("Case ID", "Unknown"),
                    "Customer": item.get("Customer", "Unknown"),
                    "Event": f"{item.get('Rail', 'Unknown')} payment reviewed against the configured policy",
                    "Status": item.get("State", "Unknown"),
                }
                for item in cases[:8]
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
        note("Policy guard", "These controls are deterministic synthetic rules. Recommendations cannot bypass a policy gate.", "info")
        return

    if view == "Risk analytics":
        classification, states = analytics_frames(st.session_state.get("admin_cases", []))
        left, right = st.columns(2)
        with left:
            st.markdown("### Case categories")
            st.bar_chart(classification, color=["#008f86"])
        with right:
            st.markdown("### Current case states")
            st.bar_chart(states, color=["#d77a16"])
        note("Analytics scope", f"Analytics reflect {len(st.session_state.get('admin_cases', []))} customer cases currently loaded in this admin session.", "info")
        return

    st.markdown("### Recent audit decisions")
    if st.session_state.admin_history:
        st.dataframe(pd.DataFrame(st.session_state.admin_history), use_container_width=True, hide_index=True)
    else:
        note("Audit ledger", "No admin decisions recorded in this session.", "info")
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
    st.sidebar.markdown('<div class="theme-note"><h3>Agent mesh healthy</h3><div>4 deterministic nodes online</div></div>', unsafe_allow_html=True)
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

    if "sla_age" not in st.session_state:
        first_case = st.session_state.admin_cases[0] if st.session_state.admin_cases else {}
        st.session_state.sla_age = int(first_case.get("Age", 18))
    age = st.slider("Transaction age (SLA tester)", min_value=0, max_value=365, key="sla_age", help="Automatically follows the selected case age; adjust it to simulate a different policy date.")
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
            row["State"] = policy_state(item, age)
        row["SLA"] = item.get("SLA") or sla_for(item, age)
        row["Decision"] = st.session_state.admin_decisions.get(item["Case ID"], "Pending admin action" if row["State"] == "Escalated" else "Not required")
        enriched.append(row)
    escalated = sum(item["State"] == "Escalated" for item in enriched)
    active = sum(item["State"] in {"Request Raised", "Return Request Raised", "Recall Request Raised", "Simulated Request Raised"} for item in enriched)
    blocked = sum(item["State"] == "No-Remedy" for item in enriched)
    metrics = st.columns(4)
    with metrics[0]: metric("Escalated cases", str(escalated), "Awaiting admin decision", "amber")
    with metrics[1]: metric("Active requests", str(active), "Return or recall requests", "cyan")
    with metrics[2]: metric("No-remedy decisions", str(blocked), "Rail finality or expired SLA", "red")
    active_customers = len({item["Customer"] for item in st.session_state.admin_cases})
    with metrics[3]: metric("Voice agent activity", str(active_customers), "Customers with activity", "cyan")

    st.markdown("## Cases requiring orchestration")
    filters = st.columns([2, 1, 1])
    with filters[0]: query = st.text_input("Search case, customer or beneficiary", placeholder="Search the queue", label_visibility="collapsed")
    with filters[1]: rail = st.selectbox("Rail", ["All rails", "ACH", "WIRE", "RTP", "FEDNOW"], label_visibility="collapsed")
    with filters[2]: status = st.selectbox("State", ["All states", "Needs Clarification", "Escalated", "Ready For Review", "Agent Approved", "Request Raised", "Return Request Raised", "Recall Request Raised", "Simulated Request Raised", "No-Remedy", "Closed"], label_visibility="collapsed")
    visible = [item for item in enriched if (not query or query.lower() in str(item).lower()) and (rail == "All rails" or item["Rail"] == rail) and (status == "All states" or item["State"] == status)]
    table = pd.DataFrame([{key: item[key] for key in ["Case ID", "Customer", "Amount", "Rail", "Intent", "Request Type", "State", "Decision", "SLA"]} for item in visible])
    st.dataframe(table, use_container_width=True, hide_index=True, column_config={"State": st.column_config.TextColumn("State"), "Confidence": st.column_config.ProgressColumn("Match", min_value=0, max_value=100)})

    if not visible:
        note("No cases available", "Submit a case in the customer workspace or refresh customer cases.", "info")
        return
    case_options = [item["Case ID"] for item in visible]
    if st.session_state.get("deep_dive_case") not in case_options:
        st.session_state.deep_dive_case = case_options[0]
    selected_id = st.selectbox(
        "Select case to review",
        case_options,
        key="deep_dive_case",
        on_change=sync_sla_age_to_case,
        format_func=lambda case_id: next(
            f"{item['Case ID']} · {item['Customer']}"
            for item in visible
            if item["Case ID"] == case_id
        ),
    )
    selected = next(item for item in enriched if item["Case ID"] == selected_id)
    st.markdown("## Deep-dive audit")
    left, right = st.columns([1.08, .92])
    with left:
        st.markdown(f'<div class="audit-block"><div class="eyebrow">Selected case</div><h4>{selected["Case ID"]} · {selected["Customer"]}</h4><p><strong>{selected["Amount"]}</strong> to {selected["Merchant"]} via {selected["Rail"]}<br>{selected["Date"]} · {badge(selected["State"])} · {selected["SLA"]}</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="audit-block"><h4>AI cognitive routing & vector match</h4><p>Cosine similarity match confidence: <strong>{selected["Confidence"]}%</strong></p><div class="terminal"><b>route</b> payment intelligence / claimant history / rail rules<br><b>match</b> User stated beneficiary and amount. Found closest match <strong>{selected["Merchant"]}</strong>. Date tolerance window accepted. Cross-referencing trading names...<br><b>guard</b> 60-day policy gate: <strong>{"BLOCKED" if selected["State"] == "No-Remedy" else "REVIEW" if selected["State"] == "Escalated" else "PASS"}</strong></div></div>', unsafe_allow_html=True)
    with right:
        recommendation = "Preserve evidence and route to policy exception review. Do not raise a recovery request." if selected["State"] == "No-Remedy" else "Hold for senior analyst review before the SLA window closes." if selected["State"] == "Escalated" else f"Safe to approve the configured {selected['Request Type'].lower()}."
        st.markdown(f'<div class="audit-block"><h4>Agentic smart audit verdict</h4><p>Multi-agent pre-flight · 3 checks complete</p><div class="risk">{selected["Risk"]}% <span style="font-size:11px;color:#78909e;font-weight:400">fraud risk · {"LOW" if selected["Risk"] < 20 else "MODERATE"}</span></div><p><strong>Behavioral flag</strong><br>Customer profile is stable. No past buyer remorse claims detected in 12 months.</p><div class="recommendation"><strong>System recommendation</strong><p>{recommendation}</p></div></div>', unsafe_allow_html=True)
        decision = st.session_state.admin_decisions.get(selected["Case ID"])
        if can_admin_approve(selected["State"]) and decision not in {"Admin approved", "Manual review approved"}:
            action_label = "Approve manual review" if selected["Request Type"] == "No request" else f"Approve {selected['Request Type'].lower()}"
            if st.button(action_label, type="primary", use_container_width=True):
                recipient = customer_email(selected)
                decision_label = "Manual review approved" if selected["Request Type"] == "No request" else "Admin approved"
                state_label = "Manual Review Approved" if selected["Request Type"] == "No request" else "Recall Request Raised" if selected["Request Type"] == "Recall request" else "Return Request Raised"
                reference_id = approval_reference(selected)
                request_status = "AGENT_APPROVED" if selected["Request Type"] == "No request" else "SIMULATED_SUBMITTED"
                persist_case_decision(selected, reference_id, request_status)
                st.session_state.admin_decisions[selected["Case ID"]] = decision_label
                for case in st.session_state.admin_cases:
                    if case["Case ID"] == selected["Case ID"]:
                        case["State"] = state_label
                        case["SLA"] = "Manual review approved" if selected["Request Type"] == "No request" else f"{selected['Request Type']} approved"
                        case["Request"] = reference_id
                        break
                st.session_state.admin_history.append({"Case": selected["Case ID"], "Verdict": decision_label, "Operator": "Riya Kapoor", "Evidence": "Escalated case reviewed; customer email triggered; no recovery request created" if selected["Request Type"] == "No request" else "Escalated case approved; customer email triggered"})
                st.session_state.email_events.append({"Case": selected["Case ID"], "Recipient": recipient, "Subject": f"Payment exception update - {selected['Case ID']}", "Reference": reference_id})
                st.session_state.admin_cases = [dict(case) for case in st.session_state.admin_cases]
                st.rerun()
        elif decision in {"Admin approved", "Manual review approved"}:
            note("Approval recorded", "Customer notification already triggered.", "info")
        elif can_admin_close(selected["State"]):
            note("Request blocked by policy", "No late request or final-rail recovery request will be raised automatically.", "hold")
            already_closed = decision == "Closed as no remedy"
            if st.button("Closed as no remedy" if already_closed else "Close as no remedy", type="secondary", disabled=already_closed, use_container_width=True):
                recipient = customer_email(selected)
                reference_id = approval_reference(selected)
                persist_case_decision(selected, reference_id, "NOT_AVAILABLE", "CLOSED")
                selected["Request"] = reference_id
                st.session_state.admin_decisions[selected["Case ID"]] = "Closed as no remedy"
                for case in st.session_state.admin_cases:
                    if case["Case ID"] == selected["Case ID"]:
                        case["State"] = "Closed"
                        case["Request"] = reference_id
                        break
                st.session_state.admin_history.append({"Case": selected["Case ID"], "Verdict": "Closed as no remedy", "Operator": "Riya Kapoor", "Evidence": "No-remedy policy decision"})
                st.session_state.email_events.append({"Case": selected["Case ID"], "Recipient": recipient, "Subject": f"Payment exception update - {selected['Case ID']}", "Reference": reference_id})
                note("Case closed", f"Case {selected['Case ID']} closed as no remedy.", "hold")
            elif already_closed:
                note("Case closed", f"Case {selected['Case ID']} is closed as no remedy. Customer notification triggered.", "hold")
        elif selected["State"] == "Closed":
            note("Case closed", f"Case {selected['Case ID']} is closed as no remedy. Customer notification triggered.", "hold")
        else:
            note("No action required", "This case is already approved; admin approval is not required.", "info")
        with st.expander("Customer notification"):
            recipient = customer_email(selected)
            st.caption("Simulated email channel")
            st.text_input("Recipient", value=recipient, disabled=True, key=f"email_recipient_{selected['Case ID']}")
            st.text_input("Subject", value=f"Payment exception update - {selected['Case ID']}", disabled=True, key=f"email_subject_{selected['Case ID']}")
            email_reference = selected.get("Request", "N/A")
            if selected["State"] == "No-Remedy":
                email_body = f"We reviewed your {selected['Rail']} payment of {selected['Amount']} to {selected['Merchant']}. No recovery remedy is available under the configured policy, so this case is closed. Reference ID: {email_reference}. No recovery request will be raised."
            else:
                email_body = f"We reviewed your {selected['Rail']} payment of {selected['Amount']} to {selected['Merchant']}. Current outcome: {selected['State']}. Reference ID: {email_reference}. No guaranteed recovery is implied."
            st.text_area("Message preview", value=email_body, height=90, disabled=True, key=f"email_body_{selected['Case ID']}")
            if st.session_state.admin_decisions.get(selected["Case ID"]) == "Admin approved":
                note("Customer notification", f"Notification triggered for {recipient}. No external email was sent.", "info")
            else:
                st.caption("Customer email is triggered automatically after admin approval of an escalated case.")

    st.markdown("## Operations analytics")
    classification, states = analytics_frames(enriched)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("### Case categories")
        st.bar_chart(classification, color=["#58d4cd"])
    with chart_right:
        st.markdown("### Current case states")
        st.bar_chart(states, color=["#eab76a"])


if __name__ == "__main__":
    main()