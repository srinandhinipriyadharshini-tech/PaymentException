from __future__ import annotations

import csv
from datetime import date, datetime
import html
import io
import json
from pathlib import Path
import time

import duckdb
import streamlit as st

from core.models import CaseResult, CaseStatus, Category, RequestStatus
from core.workflow import process_claim
from data.create_database import create_database
from theme import inject_css as inject_theme_css, note, page_header, payment_rail, setup_page

HISTORY_PATH = Path(__file__).resolve().parent / "traces" / "case_history.json"
DATABASE_PATH = Path(__file__).resolve().parent / "data" / "payment_exceptions.duckdb"

USERS = {
    "Maya Patel": {"role": "Synthetic customer 01", "account": "ACCT-SYN-000001"},
    "Jordan Lee": {"role": "Synthetic customer 02", "account": "ACCT-SYN-000002"},
    "Sam Rivera": {"role": "Synthetic customer 03", "account": "ACCT-SYN-000003"},
    "Alex Morgan": {"role": "Synthetic customer 04", "account": "ACCT-SYN-000004"},
    "Priya Shah": {"role": "Synthetic customer 05", "account": "ACCT-SYN-000005"},
    "Taylor Kim": {"role": "Synthetic customer 06", "account": "ACCT-SYN-000006"},
}

VOICE_DEMO_SCENARIOS = {
    "Scenario A - payment within 60 days": "I sent around eight thousand to the plumber last Tuesday.",
    "Scenario B - expired payment": "I had a wrong charge of five hundred dollars back in June.",
    "Scenario C - escalate to manual review": "No, that is not the right account, none of those are mine!",
}

CATEGORY_LABELS = {
    Category.ERRONEOUS: "Erroneous payment",
    Category.UNAUTHORISED: "Unauthorised payment",
    Category.AUTHORISED_BUT_SCAMMED: "Authorised but scammed",
    Category.NO_REMEDY: "No remedy available",
}

REASON_CODES = {
    Category.ERRONEOUS: "SYN_R02",
    Category.UNAUTHORISED: "SYN_R10",
    Category.AUTHORISED_BUT_SCAMMED: "SYN_R10",
    Category.NO_REMEDY: "none",
}


def safe_text(value: object) -> str:
    return html.escape(str(value))


def masked_identifier(value: str) -> str:
    if len(value) <= 4:
        return "****"
    prefix = value.rsplit("-", 1)[0] if "-" in value else value[:2]
    return f"{prefix}-******"


def payment_data_csv() -> str:
    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)
    result = connection.execute("SELECT * FROM payments ORDER BY payment_id")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([item[0] for item in result.description])
    writer.writerows(result.fetchall())
    connection.close()
    return output.getvalue()


def ensure_demo_database() -> None:
    if not DATABASE_PATH.exists():
        create_database(DATABASE_PATH)
        return

    connection = None
    try:
        last_error = None
        for attempt in range(10):
            try:
                connection = duckdb.connect(str(DATABASE_PATH), read_only=True)
                break
            except Exception as exc:
                last_error = exc
                if attempt == 9:
                    raise last_error
                time.sleep(0.25)
        count = connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        fixture = connection.execute("SELECT value_date FROM payments WHERE payment_id = 'PMT-SYN-000006'").fetchone()
        cedar_fixture = connection.execute("SELECT amount, value_date, creditor_trading_name FROM payments WHERE payment_id = 'PMT-SYN-003777'").fetchone()
        if count == 6000 and fixture and str(fixture[0]) == "2026-09-09" and cedar_fixture and str(cedar_fixture[0]) == "152788.25" and str(cedar_fixture[1]) == "2026-09-24" and cedar_fixture[2] == "Cedar Works":
            return
    except Exception as exc:
        raise RuntimeError(
            "The payment database exists but could not be opened. "
            "Close any other database or demo process using data/payment_exceptions.duckdb, then restart the app."
        ) from exc
    finally:
        if connection is not None:
            connection.close()

    raise RuntimeError(
        "The payment database exists but does not match the expected demo fixture. "
        "Recreate it explicitly with: python data/create_database.py"
    )


def refresh_clarification(result: CaseResult) -> CaseResult:
    facts = result.extracted_facts
    if result.clarification_question and not result.ranked_candidates.candidates:
        if facts.day_of_month and facts.amount_min is not None:
            stated_amount = (facts.amount_min + facts.amount_max) / 2 if facts.amount_max is not None else facts.amount_min
            result.clarification_question = f"I captured approximately {stated_amount:.2f} on day {facts.day_of_month}, but could not locate a payment. Please provide the correct date, beneficiary, or amount."
        elif facts.day_of_month:
            result.clarification_question = f"I captured day {facts.day_of_month}. Please provide the correct date, amount, or beneficiary so I can locate the payment."
    return result


def preserve_case_dates(updated: CaseResult, previous: CaseResult) -> CaseResult:
    updated.raised_at = previous.raised_at
    updated.approved_at = previous.approved_at
    updated.last_updated_at = datetime.now()
    return updated


def format_case_date(value: datetime | None) -> str:
    return value.strftime("%d %b %Y, %H:%M") if value else "Not yet"


def load_saved_state() -> tuple[dict[str, list[CaseResult]], dict[str, list[dict]], dict[str, str]]:
    empty = {name: [] for name in USERS}
    if not HISTORY_PATH.exists():
        return empty, {}, {}
    try:
        saved = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        histories = {
            name: [refresh_clarification(CaseResult.model_validate(item)) for item in saved.get("histories", {}).get(name, [])]
            for name in USERS
        }
        drafts = {name: saved.get("drafts", {}).get(name, "") for name in USERS}
        chat_threads = saved.get("chat_threads", {})
        for name, items in histories.items():
            if not items or not drafts[name]:
                continue
            latest = items[-1]
            if latest.clarification_question:
                refreshed = process_claim(drafts[name], DATABASE_PATH, debtor_account=USERS[name]["account"])
                refreshed.case_id = latest.case_id
                preserve_case_dates(refreshed, latest)
                items[-1] = refreshed
                chat_threads.pop(refreshed.case_id, None)
        return histories, chat_threads, drafts
    except (OSError, ValueError):
        return empty, {}, {}


def save_saved_state() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "histories": {
            name: [item.model_dump(mode="json") for item in items]
            for name, items in st.session_state.histories.items()
        },
        "chat_threads": st.session_state.chat_threads,
        "drafts": st.session_state.drafts,
    }
    HISTORY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sync_persisted_case_updates(history: list[CaseResult]) -> None:
    try:
        saved = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    persisted = {
        raw.get("case_id"): raw
        for items in saved.get("histories", {}).values()
        for raw in items
        if raw.get("case_id")
    }
    for index, item in enumerate(history):
        raw = persisted.get(item.case_id)
        if not raw:
            continue
        updated = CaseResult.model_validate(raw)
        item.reference_id = updated.reference_id
        item.approved_at = updated.approved_at
        item.last_updated_at = updated.last_updated_at
        item.request_status = updated.request_status
        item.case_status = updated.case_status


def clear_user_history(user_name: str) -> None:
    case_ids = {item.case_id for item in st.session_state.histories[user_name]}
    st.session_state.histories[user_name] = []
    st.session_state.active_case_id = None
    st.session_state.active_case_ids[user_name] = None
    st.session_state.drafts[user_name] = ""
    st.session_state.transcript_confirmed[user_name] = False
    for key in (
        f"claim_{user_name}",
        f"transcript_{user_name}",
        f"voice_{user_name}",
    ):
        st.session_state.pop(key, None)
    for case_id in case_ids:
        st.session_state.chat_threads.pop(case_id, None)
        st.session_state.sent_replies.pop(case_id, None)
        for key in (
            f"submitted_{user_name}_{case_id}",
            f"customer_confirmed_{user_name}_{case_id}",
            f"agent_approve_{user_name}_{case_id}",
            f"clarification_{user_name}_{case_id}",
        ):
            st.session_state.pop(key, None)
    save_saved_state()


def register_customer_case(history: list[CaseResult], claim_text: str, result: CaseResult) -> CaseResult:
    payment_id = result.selected_payment.payment_id if result.selected_payment else None
    duplicate = next(
        (
            item for item in history
            if payment_id
            and item.selected_payment
            and item.selected_payment.payment_id == payment_id
            and item.case_status is not CaseStatus.CLOSED
        ),
        None,
    )
    if duplicate:
        thread = st.session_state.chat_threads.setdefault(duplicate.case_id, [])
        thread.append({"role": "customer", "text": claim_text})
        thread.append({"role": "agent", "text": "This payment already has an active case. I kept the existing case and did not create another request."})
        return duplicate
    history.append(result)
    st.session_state.chat_threads.setdefault(result.case_id, []).append({"role": "customer", "text": claim_text})
    return result


def sync_active_user() -> None:
    st.session_state.active_user = st.session_state.user_selector


def role_url(role: str) -> str:
    return "http://localhost:8502" if role == "Payment Exception Analyst" else "http://localhost:8501"


def render_role_selector() -> None:
    st.markdown(
        '<details class="role-menu"><summary>User</summary><a href="http://localhost:8501">User</a><a href="http://localhost:8502">Payment Exception Analyst</a></details>',
        unsafe_allow_html=True,
    )


def mark_reply_submitted(input_key: str, flag_key: str) -> None:
    st.session_state[flag_key] = st.session_state.get(input_key, "")
    st.session_state[input_key] = ""


def customer_response(result: CaseResult) -> str:
    response = result.customer_message
    payment = result.selected_payment
    if payment and not result.clarification_question:
        if result.category is Category.AUTHORISED_BUT_SCAMMED:
            return f"We recorded your authorised-but-scammed claim for the {payment.rail} payment. This claim requires manual review. No recovery is promised and no inter-bank request will be raised automatically."
        if result.deadline and result.deadline < date.today():
            return f"We matched the {payment.currency} {payment.amount:,.2f} payment on {payment.value_date} to {payment.creditor_trading_name} via {payment.rail}. The payment-exception deadline passed on {result.deadline}; I am routing this for manual review. No late request will be raised and no customer confirmation is required."
        if result.remedy and not result.remedy.available:
            return response + f" {no_remedy_reason(result)} No inter-bank request will be raised, and no customer confirmation is required."
        response += f" Please confirm that you mean the {payment.currency} {payment.amount:,.2f} payment on {payment.value_date} to {payment.creditor_trading_name}. Once you confirm, we can raise a simulated {request_type_for(result)}. This is not a guarantee of recovery; the receiving institution may decline it or the funds may no longer be available."
    return response


def clarification_response(result: CaseResult) -> str:
    response = result.clarification_question or ""
    candidates = result.ranked_candidates.candidates
    if candidates:
        choices = []
        for index, candidate in enumerate(candidates[:5], 1):
            payment = candidate.payment
            choices.append(
                f"Option {index}: {payment.currency} {payment.amount:,.2f} on {payment.value_date} to {payment.creditor_trading_name} via {payment.rail} ({masked_identifier(payment.payment_id)})"
            )
        response += " " + " ".join(choices)
    return response


def clarification_placeholder(result: CaseResult) -> str:
    question = (result.clarification_question or "").lower()
    if "payment date" in question or "date" in question:
        return "Reply with the payment date, for example: 2026-09-05"
    if "confirm this payment" in question or "approximate amount" in question:
        return "Reply: Yes, I confirm this payment, or No, option 2"
    if "which" in question or "option" in question:
        return "Reply with an option number, for example: option 1"
    return "Reply with the missing amount, date, beneficiary, or option"


def request_id_for(result: CaseResult) -> str:
    rail = result.rail or (result.selected_payment.rail if result.selected_payment else "PAY")
    return f"SIM-{rail}-{result.case_id[-6:]}"


def request_type_for(result: CaseResult) -> str:
    message_type = result.remedy.message_type.lower() if result.remedy else ""
    if "recall" in message_type:
        return "recall request"
    if "return" in message_type:
        return "return request"
    return "inter-bank request"


def no_remedy_reason(result: CaseResult) -> str:
    payment = result.selected_payment
    if payment and payment.rail in {"RTP", "FEDNOW"} and payment.funds_moved:
        return f"This {payment.rail} payment is a final instant-rail transaction and the funds have moved, so the configured rules do not permit a recovery request."
    if result.deadline and result.deadline < date.today():
        return f"The configured recovery deadline passed on {result.deadline}, so no late request is permitted."
    return "No permitted recovery remedy exists for this payment under the configured rail and category rules."


def submission_response(result: CaseResult) -> str:
    payment = result.selected_payment
    request_id = result.reference_id or request_id_for(result)
    request_type = request_type_for(result)
    return (
        f"Thank you for confirming. We raised the simulated {request_type} {request_id}. This is a request only and does not guarantee recovery; the receiving institution may decline it or the funds may no longer be available. "
        f"Payment details: {payment.currency} {payment.amount:,.2f} on {payment.value_date} "
        f"to {payment.creditor_trading_name} via {payment.rail}. "
        f"Deadline: {result.deadline or 'No deadline'}. No real bank was contacted."
    )


def status_badge(label: str, tone: str = "teal") -> str:
    return f'<span class="badge badge-{tone}">{safe_text(label)}</span>'


def result_status(result: CaseResult | None) -> tuple[str, str]:
    if result is None:
        return "No Active Case", "neutral"
    if result.case_status is CaseStatus.CLARIFICATION_REQUIRED:
        return result.case_status.value, "amber"
    if result.case_status is CaseStatus.NO_REMEDY:
        return result.case_status.value, "red"
    if result.case_status is CaseStatus.ESCALATED:
        return result.case_status.value, "amber"
    if result.case_status is CaseStatus.SUBMITTED_SIMULATED:
        return result.case_status.value, "teal"
    return result.case_status.value, "teal"


def render_candidate(result: CaseResult) -> None:
    candidates = result.ranked_candidates.candidates
    if result.clarification_question:
        st.markdown('<div class="alert alert-amber"><strong>Clarification needed</strong><br>More information is required before a payment can be confirmed.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="question">{safe_text(result.clarification_question)}</div>', unsafe_allow_html=True)
        if candidates:
            st.markdown("**Candidate choices**")
            for candidate in candidates[:5]:
                payment = candidate.payment
                st.markdown(
                    f'<div class="candidate-choice"><strong>{safe_text(masked_identifier(payment.payment_id))}</strong> · {safe_text(payment.rail)} · {safe_text(payment.currency)} {payment.amount:,.2f}<br><span class="muted">{safe_text(payment.value_date)} · {safe_text(payment.creditor_trading_name)} · {candidate.confidence:.0%} match</span></div>',
                    unsafe_allow_html=True,
                )
        return

    if not candidates:
        st.markdown('<div class="empty-card">No synthetic payment matched the extracted facts. Ask the customer for an amount, date, rail, or beneficiary.</div>', unsafe_allow_html=True)
        return

    payment = result.selected_payment or candidates[0].payment
    selected_match = next((item for item in candidates if item.payment.payment_id == payment.payment_id), candidates[0])
    st.markdown("**Selected candidate**")
    st.markdown(
        f'<div class="candidate-card"><div class="candidate-top"><strong>{safe_text(masked_identifier(payment.payment_id))}</strong>{status_badge("Selected", "teal")}</div><div class="candidate-grid"><span><b>Rail</b><br>{safe_text(payment.rail)}</span><span><b>Amount</b><br>{safe_text(payment.currency)} {payment.amount:,.2f}</span><span><b>Payment date</b><br>{safe_text(payment.value_date)}</span><span><b>Beneficiary</b><br>{safe_text(payment.creditor_trading_name)}</span></div><div class="evidence"><b>Match score {selected_match.confidence:.0%}</b><br>{safe_text(", ".join(selected_match.match_reasons) or "Payment facts supplied for review")}</div></div>',
        unsafe_allow_html=True,
    )


def render_result(result: CaseResult, history: list[CaseResult], active_user: str) -> None:
    status, tone = result_status(result)
    st.markdown(
        '<div class="ai-signal-card"><div class="ai-brain">🧠</div><div><span class="ai-signal-label">AI result synthesis</span><strong>Facts, payment match, and policy outcome are ready for review.</strong></div><span class="ai-signal-state">VERIFIED</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-kicker">Active case</div>', unsafe_allow_html=True)
    header_left, header_right = st.columns([1.7, 1], gap="large")
    with header_left:
        st.markdown(f"## {safe_text(result.case_id)}")
        st.caption(f"Case owner: {active_user}  ·  Synthetic review workspace")
    with header_right:
        st.markdown(f'<div class="status-box">{status_badge(status, tone)}<br><span class="muted">Current Case State</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="review-title"><span>01</span><div><strong>Classification Confidence</strong><small>Extracted facts and confidence from the customer message</small></div></div>', unsafe_allow_html=True)
    facts = result.extracted_facts
    amount = "Not stated"
    if facts.amount_min is not None and facts.amount_max is not None:
        amount = f"{facts.amount_min:,.2f} - {facts.amount_max:,.2f}"
    date_window = "Not stated"
    if facts.date_min and facts.date_max:
        date_window = f"{facts.date_min} to {facts.date_max}"
    elif facts.day_of_month:
        month_of_year = getattr(facts, "month_of_year", None)
        date_window = f"Day {facts.day_of_month}" + (f" in month {month_of_year}" if month_of_year else " of month")
    fact_rows = {
        "Amount range": amount,
        "Date window": date_window,
        "Beneficiary": facts.beneficiary_description or "Not stated",
        "Stated reason": facts.customer_reason or "Not stated",
        "Rail": facts.rail or "Not stated",
        "Confidence": f"{result.confidence:.0%}",
    }
    st.markdown('<div class="info-card">' + "".join(f'<div class="fact-row"><span>{safe_text(key)}</span><strong>{safe_text(value)}</strong></div>' for key, value in fact_rows.items()) + "</div>", unsafe_allow_html=True)

    st.markdown('<div class="review-title"><span>02</span><div><strong>Possible payments</strong><small>Ranked using amount, date, and beneficiary</small></div></div>', unsafe_allow_html=True)
    render_candidate(result)

    st.markdown('<div class="review-title"><span>03</span><div><strong>Claim classification</strong><small>Deterministic decision after payment selection</small></div></div>', unsafe_allow_html=True)
    if result.claim_category:
        st.markdown(f'<div class="decision-card"><div>{status_badge(CATEGORY_LABELS[result.claim_category], "teal" if result.claim_category != Category.NO_REMEDY else "red")}</div><h3>{result.claim_category.value}</h3><p class="muted">Classification confidence {result.confidence:.0%}</p><p>{safe_text(result.remedy.rationale if result.remedy else "Deterministic synthetic classification result.")}</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-card">Classification waits until a payment is selected.</div>', unsafe_allow_html=True)

    confirmation_key = f"customer_confirmed_{active_user}_{result.case_id}"
    if st.session_state.get(confirmation_key, False) or result.case_status is CaseStatus.SUBMITTED_SIMULATED:
        st.markdown('<div class="review-title"><span>04</span><div><strong>Remedy and deadline</strong><small>Calculated from the synthetic rail rules</small></div></div>', unsafe_allow_html=True)
        if result.remedy:
            remedy_tone = "teal" if result.remedy.available else "red"
            expired = result.deadline is not None and result.deadline < date.today()
            remedy_tone = "red" if expired or not result.remedy.available else "teal"
            deadline = result.deadline or "No deadline"
            availability = "Expired - manual review" if expired else "Available" if result.remedy.available else "Unavailable"
            deadline_label = f"{deadline} (passed)" if expired else str(deadline)
            st.markdown(f'<div class="decision-card"><div>{status_badge(availability, remedy_tone)}</div><h3>{safe_text("Deadline passed; manual review required" if expired else result.remedy.action)}</h3><p class="muted">Deterministic synthetic rule output</p><div class="fact-row"><span>Message type</span><strong>{safe_text(result.remedy.message_type)}</strong></div><div class="fact-row"><span>Reason code</span><strong>{safe_text(result.remedy.reason_code)}</strong></div><div class="fact-row"><span>Deadline</span><strong>{safe_text(deadline_label)}</strong></div></div>', unsafe_allow_html=True)
    elif result.remedy and (not result.remedy.available or (result.deadline and result.deadline < date.today())):
        expired = result.deadline is not None and result.deadline < date.today()
        title = "Recovery window expired" if expired else "No recovery remedy available"
        detail = (
            f"The configured deadline of {result.deadline} has passed. This case requires manual review; no request will be raised automatically."
            if expired
            else f"{no_remedy_reason(result)} No customer confirmation is required."
        )
        st.markdown('<div class="review-title"><span>04</span><div><strong>Policy outcome</strong><small>Calculated from the synthetic rail rules</small></div></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="decision-card"><div>{status_badge("Manual review required" if expired else "No request", "amber" if expired else "red")}</div><h3>{safe_text(title)}</h3><p class="muted">{safe_text(detail)}</p><div class="fact-row"><span>Deadline</span><strong>{safe_text(str(result.deadline or "No deadline"))}</strong></div><div class="fact-row"><span>Customer confirmation</span><strong>Not required</strong></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="waiting-card"><strong>Remedy and deadline</strong><span>Shown after the customer confirms an eligible payment in chat.</span></div>', unsafe_allow_html=True)

setup_page("Clearline | Payment Exceptions", "C")
ensure_demo_database()
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink:#172b49; --muted:#60738d; --line:#d2e0ee; --paper:#eef6fc; --white:#ffffff; --charcoal:#172b49; --teal:#008f86; --teal-soft:#d8f7f0; --amber:#d77a16; --amber-soft:#fff0cf; --red:#d84f5b; --red-soft:#ffe5e8; --coral:#f06f5e; --navy-soft:#e6efff; }
    html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
    .stApp { background-color:#f4f9fd; background-image:radial-gradient(circle at 7% -3%, rgba(240,111,94,.22), transparent 23rem), radial-gradient(circle at 94% 8%, rgba(71,143,236,.15), transparent 24rem), linear-gradient(rgba(23,43,73,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(23,43,73,.035) 1px, transparent 1px), linear-gradient(135deg, #eaf5ff 0%, #ffffff 52%, #e3faf4 100%); background-size:auto, auto, 28px 28px, 28px 28px, auto; }
    .stApp:before { content:""; position:fixed; inset:0; pointer-events:none; background:linear-gradient(115deg, transparent 0 42%, rgba(255,255,255,.22) 50%, transparent 58%); background-size:220% 100%; animation:surface-sheen 18s ease-in-out infinite; opacity:.45; }
    [data-testid="stAppViewContainer"] { background:transparent; }
    [data-testid="stMainBlockContainer"] { max-width:1480px; padding:2rem 3rem 4rem; }
    [data-testid="stVerticalBlock"] { gap:.65rem; }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stToolbar"] { background:transparent; }
    [data-testid="stSidebar"] { display:none; }
    [data-testid="stSidebar"] * { color:#edf4f2; }
    [data-testid="stSidebar"] .stSelectbox label { color:#b9cbc7; }
    h1, h2, h3 { font-family:'Space Grotesk', sans-serif; letter-spacing:0; color:var(--ink); }
    h1 { font-size:2.35rem; margin:.2rem 0 0; }
    h2 { font-size:1.35rem; margin-top:.2rem; }
    h3 { font-size:1rem; margin:.45rem 0 .7rem; }
    .topbar { background:transparent; color:var(--ink); margin:-2rem -3rem 1.8rem; padding:.85rem 3rem; border-bottom:1px solid var(--line); box-shadow:none; }
    .topbar:after { content:""; display:block; height:2px; margin:.75rem 0 -.85rem; background:linear-gradient(90deg, var(--coral), var(--teal), transparent 72%); opacity:.7; }
    .topbar { animation:topbar-in .6s ease-out both; }
    .ops-link { float:right; display:inline-flex; align-items:center; gap:.4rem; margin-top:.1rem; padding:.48rem .72rem; border:1px solid #b9d7ea; border-radius:8px; background:#eaf5ff; color:#245d86 !important; font-size:.74rem; font-weight:700; text-decoration:none !important; box-shadow:0 3px 9px rgba(40,83,126,.08); }
    .ops-link:hover { border-color:#008f86; background:#d8f7f0; color:#006e68 !important; }
    .role-link { display:block; margin-top:-.35rem; color:#087f75 !important; font-size:.68rem; font-weight:700; text-decoration:none !important; }
    .role-link:hover { text-decoration:underline !important; }
    .role-menu { position:relative; z-index:5; }
    .role-menu summary { cursor:pointer; list-style:none; border:1px solid #b9d7ea; border-radius:8px; background:#fff; color:var(--ink); padding:.48rem .65rem; font-size:.74rem; font-weight:700; }
    .role-menu summary::-webkit-details-marker { display:none; }
    .role-menu summary:after { content:"▾"; float:right; color:var(--teal); }
    .role-menu a { display:block; padding:.5rem .65rem; background:#fff; color:var(--ink) !important; font-size:.72rem; font-weight:600; text-decoration:none !important; }
    .role-menu a:hover { background:var(--teal-soft); color:#006e68 !important; }
    .brand-mark { display:inline-flex; align-items:center; gap:.6rem; font-family:'Space Grotesk'; font-weight:700; font-size:1rem; letter-spacing:.01em; }
    .brand-dot { display:inline-grid; place-items:center; width:1.9rem; height:1.9rem; border-radius:9px; background:linear-gradient(145deg, var(--coral), #f09a73); color:#fff; font-size:.7rem; box-shadow:0 4px 12px rgba(231,120,97,.35); }
    .brand-sub { color:var(--muted); font-size:.7rem; margin-left:2.4rem; margin-top:-.12rem; letter-spacing:.02em; }
    .hero { position:relative; overflow:hidden; background:linear-gradient(115deg, rgba(255,255,255,.98), rgba(226,250,245,.94) 72%, rgba(231,240,255,.9)); color:var(--ink); margin:0 0 1.15rem; padding:1.45rem 1.55rem 1.5rem; border:1px solid rgba(210,224,238,.98); border-radius:16px; box-shadow:0 12px 30px rgba(40,83,126,.1); }
    .hero:after { content:""; position:absolute; right:-4rem; top:-5rem; width:15rem; height:15rem; border:1px solid rgba(8,127,117,.18); border-radius:50%; box-shadow:0 0 0 1.5rem rgba(8,127,117,.045), 0 0 0 3rem rgba(8,127,117,.025); }
    .hero { animation:rise-in .45s ease-out both; }
    .hero:before { content:"AI-ASSISTED INTAKE"; position:absolute; right:1.5rem; bottom:1.05rem; color:rgba(0,143,134,.55); font:700 .62rem 'Space Grotesk', sans-serif; letter-spacing:.18em; }
    @keyframes rise-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
    @keyframes topbar-in { from { opacity:0; transform:translateY(-5px); } to { opacity:1; transform:translateY(0); } }
    @keyframes surface-sheen { 0%, 45% { background-position:150% 0; } 70%, 100% { background-position:-50% 0; } }
    .hero h1 { color:var(--ink); }
    .hero-sub { color:var(--muted); margin-top:.25rem; }
    .kicker, .section-kicker { color:var(--teal); font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
    .hero .kicker { color:var(--coral); }
    .section-kicker { margin-top:.3rem; color:var(--coral); }
    .badge { display:inline-block; border-radius:999px; padding:.28rem .62rem; font-size:.7rem; font-weight:700; letter-spacing:.03em; }
    .badge-teal { background:var(--teal-soft); color:#116e66; }
    .badge-amber { background:var(--amber-soft); color:#8c5c15; }
    .badge-red { background:var(--red-soft); color:#9d3c3c; }
    .badge-neutral { background:#e9eeee; color:#5c6b6c; }
    .meta-card { background:rgba(255,255,255,.96); border:1px solid var(--line); border-radius:9px; padding:.72rem .9rem; min-height:3.7rem; display:flex; flex-direction:column; justify-content:center; box-shadow:0 4px 12px rgba(40,83,126,.06); }
    .meta-card span { color:var(--muted); font-size:.68rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; margin-bottom:.3rem; }
    .meta-card strong { font-size:.9rem; }
    .case-ref { text-align:right; padding:.2rem .15rem .8rem; }
    .case-ref span { display:block; color:var(--muted); font-size:.68rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; margin-bottom:.25rem; }
    .case-ref strong { font-size:.86rem; }
    .status-strip { display:flex; flex-wrap:wrap; gap:.65rem 1.35rem; align-items:center; padding:.85rem 1rem; margin:.25rem 0 1.15rem; background:rgba(231,237,247,.82); border:1px solid #cbd8ea; border-radius:11px; font-size:.76rem; box-shadow:inset 4px 0 0 var(--coral), 0 5px 14px rgba(23,35,60,.05); animation:rise-in .55s ease-out both; }
    .ai-signal-card { display:flex; align-items:center; gap:.75rem; padding:.75rem .9rem; margin:.15rem 0 .9rem; border:1px solid #b8ddd7; border-radius:12px; background:linear-gradient(105deg,rgba(216,247,240,.95),rgba(255,255,255,.9)); box-shadow:0 6px 16px rgba(40,83,126,.07); }
    .ai-brain { display:grid; place-items:center; flex:0 0 auto; width:2.15rem; height:2.15rem; border-radius:10px; background:#087f75; color:#fff; font-size:1.2rem; box-shadow:0 0 0 5px rgba(8,127,117,.1), 0 6px 14px rgba(8,127,117,.22); }
    .ai-signal-card strong, .ai-signal-label { display:block; }
    .ai-signal-label { color:#087f75; font-size:.62rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
    .ai-signal-card strong { margin-top:.14rem; color:var(--ink); font-size:.8rem; line-height:1.35; }
    .ai-signal-state { margin-left:auto; color:#087f75; font:700 .62rem 'Space Grotesk',sans-serif; letter-spacing:.1em; }
    .status-strip span { display:inline-flex; align-items:center; gap:.35rem; }
    .review-title { display:flex; align-items:center; gap:.7rem; margin:1.25rem 0 .55rem; }
    .review-title > span { display:grid; place-items:center; width:1.8rem; height:1.8rem; border-radius:7px; background:var(--coral); color:#fff; font-size:.72rem; font-weight:700; box-shadow:0 3px 8px rgba(231,120,97,.25); }
    .review-title strong { display:block; font-family:'Space Grotesk'; font-size:.98rem; }
    .review-title small { display:block; color:var(--muted); font-size:.72rem; margin-top:.12rem; }
    .status-box { text-align:right; padding-top:.3rem; }
    .panel, .info-card, .candidate-card, .decision-card, .output-card, .empty-card { background:rgba(255,255,255,.94); border:1px solid rgba(210,224,238,.98); border-radius:12px; box-shadow:0 8px 20px rgba(40,83,126,.08); backdrop-filter:blur(8px); }
    .info-card, .candidate-card, .decision-card, .output-card, .empty-card { padding:1.05rem 1.15rem; }
    .fact-row { display:flex; justify-content:space-between; gap:1rem; border-bottom:1px solid #edf1f0; padding:.56rem 0; font-size:.85rem; }
    .fact-row:last-child { border-bottom:0; }
    .fact-row span { color:var(--muted); }
    .fact-row strong { text-align:right; }
    .candidate-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:.8rem; }
    .candidate-grid { display:grid; grid-template-columns:repeat(2, 1fr); gap:.8rem; font-size:.84rem; }
    .candidate-grid b, .muted { color:var(--muted); font-size:.78rem; }
    .evidence { background:var(--teal-soft); border-left:3px solid var(--teal); margin-top:1rem; padding:.65rem .75rem; font-size:.8rem; }
    .candidate-choice { border:1px solid #f0d295; background:linear-gradient(105deg, #fff7df, #ffffff); border-radius:9px; padding:.75rem .85rem; margin:.5rem 0; font-size:.84rem; box-shadow:0 3px 9px rgba(215,122,22,.1); }
    .bubble { border-radius:10px; padding:.8rem .95rem; margin:.55rem 0; line-height:1.45; font-size:.86rem; }
    .bubble span { display:block; font-size:.68rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.3rem; }
    .bubble.customer { background:#fff; border:1px solid var(--line); }
    .bubble.customer span { color:var(--muted); }
    .bubble.agent { background:#e4f2ef; border:1px solid #b9ddd6; margin-left:1.5rem; }
    .bubble.agent span { color:#116e66; }
    .wa-message { max-width:88%; border-radius:14px; padding:.78rem .9rem; margin:.6rem 0; line-height:1.5; font-size:.84rem; box-shadow:0 4px 12px rgba(23,35,60,.06); }
    .wa-message span { display:block; font-size:.66rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.25rem; }
    .wa-message.customer { background:#fff; border:1px solid var(--line); margin-right:2rem; }
    .wa-message.customer span { color:var(--muted); }
    .wa-message.agent { background:#e4edf8; border:1px solid #c7d7ea; margin-left:2rem; }
    .wa-message.agent span { color:#315d8b; }
    .chat-note { border-top:1px solid var(--line); margin-top:1rem; padding-top:.85rem; }
    .chat-note span { color:var(--muted); font-size:.7rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
    .chat-confirm { background:var(--amber-soft); border-left:4px solid var(--amber); border-radius:8px; padding:.75rem .85rem; margin-top:1rem; }
    .chat-closed { background:var(--teal-soft); border:1px solid #b6ded5; border-radius:9px; padding:.8rem .9rem; margin-top:1rem; line-height:1.45; }
    .alert { border-radius:8px; padding:.8rem .95rem; margin-bottom:.8rem; }
    .alert-amber { background:var(--amber-soft); border-left:4px solid var(--amber); }
    .alert-clarification { background:#e7f3ef; border-left:4px solid var(--teal); border-radius:8px; padding:.8rem 1rem; margin:.2rem 0 1.2rem; }
    .alert-info { background:var(--teal-soft); border-left:4px solid var(--teal); }
    .question { font-size:1.05rem; font-weight:600; margin:.7rem 0 1rem; }
    .decision-card h3 { margin-bottom:.25rem; }
    .decision-card { position:relative; overflow:hidden; }
    .decision-card:before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--teal); }
    .waiting-card { display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem; padding:.85rem 1rem; border:1px dashed #c6d5d1; border-radius:9px; background:#f7faf9; color:var(--muted); font-size:.8rem; }
    .waiting-card strong { color:var(--ink); font-family:'Space Grotesk'; font-size:.92rem; }
    .output-label { color:var(--muted); font-size:.72rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.4rem; }
    .output-card { min-height:5rem; line-height:1.55; }
    .mono { font-family:Consolas, monospace; font-size:.82rem; }
    .timeline-item { display:grid; grid-template-columns:1.15fr 1.2fr 1.35fr 1.35fr; gap:1rem; border-left:3px solid var(--teal); background:#fff; border-bottom:1px solid var(--line); padding:.75rem .8rem; font-size:.82rem; }
    .timeline-item div { min-width:0; }
    .timeline-item span, .timeline-item small { display:block; color:var(--muted); }
    .timeline-item span { font-size:.66rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; margin-bottom:.18rem; }
    .timeline-item small { margin-top:.2rem; font-size:.68rem; }
    @media (max-width: 800px) { .timeline-item { grid-template-columns:1fr 1fr; gap:.7rem; } }
    .stTextArea textarea, .stTextInput input { border:1px solid #c9d6d3; border-radius:8px; background:#fbfdfc; }
    .stTextArea textarea:focus, .stTextInput input:focus { border-color:var(--teal); box-shadow:0 0 0 2px rgba(23,135,125,.12); }
    .stTextArea textarea:hover, .stTextInput input:hover { border-color:#9eb5c9; }
    .panel, .info-card, .candidate-card, .decision-card, .output-card, .empty-card { transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
    .info-card:hover, .candidate-card:hover, .decision-card:hover, .output-card:hover { transform:translateY(-2px); border-color:#b7d7d2; box-shadow:0 14px 28px rgba(40,83,126,.12); }
    [data-testid="stFileUploader"] { border:1px dashed #afc5c0; border-radius:8px; background:rgba(255,255,255,.55); padding:.25rem; }
    [data-testid="stExpander"] { border:1px solid var(--line); border-radius:9px; background:rgba(255,255,255,.68); }
    [data-testid="stTabs"] button { font-weight:600; }
    div.stButton > button, div[data-testid="stDownloadButton"] button { border-radius:9px; min-height:2.55rem; font-weight:600; border:1px solid #cbd8ea; transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
    div.stButton > button:hover, div[data-testid="stDownloadButton"] button:hover { transform:translateY(-1px); box-shadow:0 5px 12px rgba(23,35,60,.12); }
    div.stButton > button[kind="primary"] { background:var(--teal); border-color:var(--teal); color:#fff; }
    div[data-testid="stDownloadButton"] button { background:var(--navy-soft); color:var(--ink); width:100%; }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:9px; padding:.7rem .85rem; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color:rgba(219,227,237,.85); border-radius:14px; }
    @media (max-width: 800px) { [data-testid="stMainBlockContainer"] { padding:1.2rem 1rem 3rem; } .topbar { margin:-1.2rem -1rem 1.2rem; padding:.8rem 1rem; } .hero { padding:1.1rem; } .wa-message { max-width:100%; margin-left:0 !important; margin-right:0 !important; } }
    /* Customer workspace hierarchy: warm, conversational, and spacious. */
    .theme-header h1, .hero h1 { font-size:clamp(2.15rem, 3.2vw, 3.15rem); line-height:1.02; letter-spacing:-.035em; font-weight:700; }
    .theme-subtitle, .hero-sub { font-size:.98rem; line-height:1.65; max-width:58ch; }
    .section-kicker, .kicker { font-size:.66rem; letter-spacing:.18em; font-weight:800; }
    .review-title strong { font-size:1.08rem; letter-spacing:-.01em; }
    .review-title small { font-size:.76rem; line-height:1.45; }
    .info-card, .candidate-card, .decision-card, .output-card, .empty-card { font-size:.9rem; line-height:1.6; }
    .fact-row { font-size:.88rem; }
    .candidate-grid { font-size:.87rem; }
    .candidate-choice, .wa-message, .bubble { font-size:.88rem; line-height:1.6; }
    .muted, .candidate-grid b { font-size:.76rem; }
    .timeline-item { font-size:.84rem; line-height:1.45; }
    .timeline-item span, .timeline-item small { font-size:.64rem; }
    .stTextArea textarea, .stTextInput input { font-size:.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
inject_theme_css()

if "active_user" not in st.session_state:
    st.session_state.active_user = "Maya Patel"
if "user_selector" not in st.session_state:
    st.session_state.user_selector = st.session_state.active_user
if "active_case_id" not in st.session_state:
    st.session_state.active_case_id = None
if "active_case_ids" not in st.session_state:
    st.session_state.active_case_ids = {name: None for name in USERS}
if "histories" not in st.session_state:
    saved_histories, saved_threads, saved_drafts = load_saved_state()
    st.session_state.histories = saved_histories
    st.session_state.chat_threads = saved_threads
    st.session_state.drafts = saved_drafts
if "drafts" not in st.session_state:
    st.session_state.drafts = {name: "" for name in USERS}
if "transcript_confirmed" not in st.session_state:
    st.session_state.transcript_confirmed = {name: False for name in USERS}
if "voice_transcripts" not in st.session_state:
    st.session_state.voice_transcripts = {name: "" for name in USERS}
if "sent_replies" not in st.session_state:
    st.session_state.sent_replies = {}
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = {}

st.markdown('<div class="topbar"><div class="brand-mark"><span class="brand-dot">CL</span>Clearline</div><div class="brand-sub">Payment exceptions workspace</div></div>', unsafe_allow_html=True)
nav_left, nav_role, nav_demo, nav_user, nav_clear = st.columns([3.5, 2.1, 1.2, 2.2, 1.5], gap="medium")
with nav_role:
    render_role_selector()
with nav_demo:
    st.markdown(f'<div style="padding-top:.45rem;text-align:right">{status_badge("Synthetic demo", "teal")}</div>', unsafe_allow_html=True)
with nav_user:
    st.selectbox("Demo user", list(USERS), key="user_selector", on_change=sync_active_user, label_visibility="collapsed")
    active_user = st.session_state.user_selector
with nav_clear:
    st.markdown('<div style="height:.18rem"></div>', unsafe_allow_html=True)
    if st.button("Clear history", key=f"clear_history_{active_user}", width="stretch"):
        clear_user_history(active_user)
        st.rerun()
profile = USERS[active_user]

history = st.session_state.histories[active_user]
sync_persisted_case_updates(history)
if history:
    for index, item in enumerate(history):
        history[index] = refresh_clarification(item)
    case_ids = {item.case_id for item in history}
    if st.session_state.active_case_ids.get(active_user) not in case_ids:
        st.session_state.active_case_ids[active_user] = history[-1].case_id
    st.session_state.active_case_id = st.session_state.active_case_ids[active_user]
current = next((item for item in history if item.case_id == st.session_state.active_case_ids.get(active_user)), None)
if current and current.clarification_question and st.session_state.drafts.get(active_user):
    refreshed = process_claim(st.session_state.drafts[active_user], DATABASE_PATH, debtor_account=profile["account"])
    refreshed.case_id = current.case_id
    preserve_case_dates(refreshed, current)
    current_index = next((index for index, item in enumerate(history) if item.case_id == current.case_id), None)
    if current_index is not None:
        history[current_index] = refreshed
        current = refreshed
        st.session_state.chat_threads.pop(current.case_id, None)
        save_saved_state()
if current and current.clarification_question:
    thread = st.session_state.chat_threads.get(current.case_id, [])
    for message in thread:
        if message.get("role") == "agent" and (
            message.get("text", "").startswith("I captured approximately")
            or message.get("text", "").startswith("I captured day")
            or message.get("text", "").startswith("Which of the similarly matched payments do you mean?")
        ):
            message["text"] = clarification_response(current)
status, status_tone = result_status(current)

page_header("Raise payment exception", "Keep the customer informed while the payment is checked.")
payment_rail([
    {"label": "Received", "time": format_case_date(current.raised_at) if current else "Awaiting message", "state": "done" if current else "current"},
    {"label": "Matched", "time": "Payment identified" if current and current.selected_payment else "Pending", "state": "done" if current and current.selected_payment else "current"},
    {"label": "Reviewed", "time": "Policy decision" if current else "Pending", "state": "done" if current and current.case_status not in {CaseStatus.RECEIVED, CaseStatus.CLARIFICATION_REQUIRED} else "pending"},
    {"label": "Outcome", "time": current.case_status.value.replace("_", " ").title() if current else "Pending", "state": "current" if current else "pending"},
])

head_a, head_b, head_c = st.columns([1.8, 1, 1], gap="large")
with head_a:
    st.markdown(f'<div class="case-ref"><span>Case reference</span><strong>{safe_text(current.case_id if current else "New case")}</strong></div>', unsafe_allow_html=True)
with head_b:
    case_label = current.case_status.value if current else "NO_ACTIVE_CASE"
    st.markdown(f'<div class="case-ref"><span>Case status</span><strong>{status_badge(case_label, status_tone)}</strong></div>', unsafe_allow_html=True)
with head_c:
    claim_label = current.claim_category.value if current and current.claim_category else "Not classified"
    request_label = current.request_status.value if current else RequestStatus.NOT_CREATED.value
    st.markdown(f'<div class="case-ref"><span>Claim category</span><strong>{safe_text(claim_label)}</strong></div>', unsafe_allow_html=True)

st.markdown(f'<div class="status-strip"><span><b>Case status</b> {status_badge(case_label, status_tone)}</span><span><b>Claim category</b> {safe_text(claim_label)}</span><span><b>Request status</b> {safe_text(request_label)}</span></div>', unsafe_allow_html=True)

if current and current.clarification_question:
    st.markdown(f'<div class="alert-clarification"><strong>Clarification needed from customer</strong><br><span class="muted">More information is required before the payment can be confirmed.</span></div>', unsafe_allow_html=True)
elif current and current.case_status is CaseStatus.ESCALATED:
    if current.category is Category.AUTHORISED_BUT_SCAMMED and current.selected_payment:
        escalation_message = "The payment was matched, but authorised-scam claims require manual review. No recovery is promised and no request will be raised automatically."
    elif current.selected_payment and current.deadline and current.deadline < date.today():
        escalation_message = f"The payment was matched, but the configured deadline passed on {current.deadline}. No late request will be raised."
    else:
        escalation_message = "The payment could not be matched from the conversation. Review the customer account and transaction history before raising any request."
    st.markdown(f'<div class="alert-clarification"><strong>Manual research required</strong><br><span class="muted">{safe_text(escalation_message)}</span></div>', unsafe_allow_html=True)

st.divider()
left, right = st.columns([1.05, .95], gap="large")
with left:
    st.markdown('<div class="section-kicker">01 / Claim conversation</div>', unsafe_allow_html=True)
    st.markdown("### Customer Intake")
    claim_key = f"claim_{active_user}"
    if st.session_state.pop(f"reset_{claim_key}", False):
        st.session_state[claim_key] = ""
    claim = st.text_area("Customer message", value=st.session_state.drafts[active_user], height=125, key=claim_key, placeholder="Example: I never authorised the ACH payment of GBP 1250 on 2026-01-02 to Northwind.")
    audio = st.audio_input("🎙️ Record customer voice message", key=f"voice_{active_user}")
    if audio:
        st.audio(audio, format=audio.type)
        st.caption("Voice recording captured. This offline demo maps the recording to a deterministic transcription scenario.")
        scenario_options = ["Select a demo scenario"] + list(VOICE_DEMO_SCENARIOS)
        voice_scenario = st.selectbox("Demo transcription scenario", scenario_options, key=f"voice_scenario_{active_user}")
        scenario_selected = voice_scenario != "Select a demo scenario"
        if scenario_selected:
            st.markdown(f'<div class="output-card"><div class="output-label">Voice transcription preview</div>{safe_text(VOICE_DEMO_SCENARIOS[voice_scenario])}</div>', unsafe_allow_html=True)
        else:
            note("Voice scenario", "Choose a scenario to preview the deterministic transcript before processing the recording.", "info")
        if st.button("Transcribe & process voice", key=f"transcribe_voice_{active_user}", type="primary", disabled=not scenario_selected, width="stretch"):
            voice_text = VOICE_DEMO_SCENARIOS[voice_scenario]
            st.session_state.voice_transcripts[active_user] = voice_text
            st.session_state.drafts[active_user] = voice_text
            with st.spinner("Transcribing voice and searching candidate payments..."):
                voice_result = process_claim(voice_text, debtor_account=profile["account"])
                active_result = register_customer_case(history, voice_text, voice_result)
            st.session_state.active_case_ids[active_user] = active_result.case_id
            st.session_state.active_case_id = active_result.case_id
            st.session_state.drafts[active_user] = voice_text if voice_result.clarification_question else ""
            st.session_state[f"reset_{claim_key}"] = True
            save_saved_state()
            st.rerun()
    if st.session_state.voice_transcripts[active_user]:
        st.markdown(f'<div class="output-card"><div class="output-label">Captured customer transcript</div>{safe_text(st.session_state.voice_transcripts[active_user])}</div>', unsafe_allow_html=True)
    transcript_key = f"transcript_{active_user}"
    if st.session_state.pop(f"reset_transcript_{active_user}", False):
        st.session_state[transcript_key] = ""
    transcript = st.text_area("Typed transcript fallback / review", key=transcript_key, height=80, placeholder="Paste the transcript, confirm it, then process the claim.")
    if audio or transcript.strip():
        transcript_state = "Confirmed" if st.session_state.transcript_confirmed[active_user] else "Needs confirmation"
        st.markdown(f"Transcript state: {status_badge(transcript_state, 'teal' if transcript_state == 'Confirmed' else 'amber')}", unsafe_allow_html=True)
        if st.button("Confirm transcript", key=f"confirm_transcript_{active_user}", disabled=not transcript.strip(), width="stretch"):
            st.session_state.transcript_confirmed[active_user] = True
            st.rerun()
    process_disabled = bool((audio or transcript.strip()) and not st.session_state.transcript_confirmed[active_user] and not claim.strip())
    if process_disabled:
        st.caption("Confirm the transcript before processing this intake.")
    if st.button("Process claim", type="primary", disabled=process_disabled, width="stretch"):
        text = claim.strip() or transcript.strip()
        if not text:
            note("Customer message needed", "Enter a customer message or confirm the transcript before processing.", "hold")
        else:
            try:
                st.session_state.drafts[active_user] = text
                with st.spinner("Extracting facts and searching synthetic payments..."):
                    result = process_claim(text, debtor_account=profile["account"])
                    active_result = register_customer_case(history, text, result)
                st.session_state.active_case_ids[active_user] = active_result.case_id
                st.session_state.active_case_id = active_result.case_id
                st.session_state.drafts[active_user] = text if result.clarification_question else ""
                st.session_state[f"reset_{claim_key}"] = True
                st.session_state[f"reset_transcript_{active_user}"] = True
                save_saved_state()
                st.session_state.transcript_confirmed[active_user] = False
                st.rerun()
            except Exception:
                note("Claim not processed", "Check the intake text and try again.", "hold")
    # Re-evaluate an old clarification using the text currently visible in the intake box.
    if current and current.clarification_question:
        current_draft = claim.strip() or st.session_state.drafts.get(active_user, "")
        if current_draft:
            refreshed = process_claim(current_draft, DATABASE_PATH, debtor_account=profile["account"])
            refreshed.case_id = current.case_id
            preserve_case_dates(refreshed, current)
            current_index = next((index for index, item in enumerate(history) if item.case_id == current.case_id), None)
            if current_index is not None:
                history[current_index] = refreshed
                current = refreshed
                st.session_state.chat_threads.pop(current.case_id, None)
                save_saved_state()

    st.markdown("### Conversation")
    if claim.strip() or current:
        if current:
            thread = st.session_state.chat_threads.setdefault(current.case_id, [])
            if not thread:
                if st.session_state.drafts[active_user]:
                    thread.append({"role": "customer", "text": st.session_state.drafts[active_user]})
            initial_response = customer_response(current)
            if initial_response and not any(item.get("role") == "agent" for item in thread):
                thread.append({"role": "agent", "text": initial_response})
                save_saved_state()
            if current.clarification_question:
                detailed_question = clarification_response(current)
                thread.append({"role": "agent", "text": detailed_question}) if not any(item["text"] == detailed_question for item in thread) else None
            for message in thread:
                if not message.get("text"):
                    continue
                bubble_class = "customer" if message["role"] == "customer" else "agent"
                label = "Customer" if message["role"] == "customer" else "Agent"
                st.markdown(f'<div class="wa-message {bubble_class}"><span>{label}</span>{safe_text(message["text"])}</div>', unsafe_allow_html=True)

            if current.clarification_question:
                clarification_key = f"clarification_{active_user}_{current.case_id}"
                clarification_submit_key = f"submit_clarification_{active_user}_{current.case_id}"
                clarification_reset_key = f"reset_clarification_{active_user}_{current.case_id}"
                if st.session_state.pop(clarification_reset_key, False):
                    st.session_state[clarification_key] = ""
                clarification = st.text_input("Reply with clarification", key=clarification_key, label_visibility="collapsed", placeholder=clarification_placeholder(current), on_change=mark_reply_submitted, args=(clarification_key, clarification_submit_key))
                if st.button("Send clarification", key=f"send_clarification_{active_user}_{current.case_id}", type="primary", width="stretch") or clarification_submit_key in st.session_state:
                    clarification = st.session_state.pop(clarification_submit_key, clarification)
                    if clarification.strip():
                        clarification_text = clarification.strip()
                        normalized_clarification = clarification_text.lower().strip().replace("option ", "")
                        candidates = current.ranked_candidates.candidates
                        ordinal_options = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
                        if normalized_clarification.isdigit() and 1 <= int(normalized_clarification) <= len(candidates):
                            selected_index = int(normalized_clarification) - 1
                        else:
                            selected_index = ordinal_options.get(normalized_clarification)
                        if normalized_clarification in {"yes", "y", "confirm", "confirmed", "yes i confirm", "i confirm", "yes confirm", "correct"} and candidates:
                            selected_index = 0
                        if normalized_clarification in {"both", "all", "both payments"} and len(candidates) >= 2:
                            thread.append({"role": "customer", "text": clarification_text})
                            thread.append({"role": "agent", "text": "I found two matching payments, but one request can cover only one payment. Please reply first or second, or provide a different date, amount, or beneficiary."})
                            st.session_state.pop(clarification_key, None)
                            st.session_state.pop(clarification_submit_key, None)
                            st.session_state[clarification_reset_key] = True
                            save_saved_state()
                            st.rerun()
                        if normalized_clarification in {"no", "neither", "none", "none of these", "none of them", "not these", "not either"}:
                            thread.append({"role": "customer", "text": clarification_text})
                            current.case_status = CaseStatus.ESCALATED
                            current.clarification_question = None
                            thread.append({"role": "agent", "text": "I could not match this payment after the details provided. I am escalating the case for manual payment research. No request will be raised until an agent verifies the transaction."})
                            st.session_state.pop(clarification_key, None)
                            save_saved_state()
                            st.rerun()
                        selected_payment_id = candidates[selected_index].payment.payment_id if selected_index is not None and selected_index < len(candidates) else None
                        if clarification_text.isdigit() and 1 <= int(clarification_text) <= 31:
                            clarification_text = f"on the {int(clarification_text)}th"
                        combined = f"{st.session_state.drafts[active_user]} Clarification: {clarification_text}"
                        with st.spinner("Searching synthetic payments and updating this case..."):
                            updated = process_claim(combined, debtor_account=profile["account"], payment_id=selected_payment_id)
                        updated.case_id = current.case_id
                        preserve_case_dates(updated, current)
                        history[-1] = updated
                        st.session_state.drafts[active_user] = combined
                        thread.append({"role": "customer", "text": clarification.strip()})
                        agent_text = customer_response(updated) if not updated.clarification_question else clarification_response(updated)
                        if agent_text:
                            thread.append({"role": "agent", "text": agent_text})
                        st.session_state.pop(clarification_key, None)
                        st.session_state.pop(clarification_submit_key, None)
                        st.session_state[clarification_reset_key] = True
                        save_saved_state()
                        st.rerun()
                st.caption("Your clarification stays in this conversation; it will not create a new case.")
            elif current.selected_payment and current.remedy and current.remedy.available and not (current.deadline and current.deadline < date.today()):
                submission_key = f"submitted_{active_user}_{current.case_id}"
                if st.session_state.get(submission_key, False):
                    st.markdown(f'<div class="chat-closed"><strong>Conversation closed</strong><br><span class="muted">The customer confirmed the payment and the simulated {safe_text(request_type_for(current))} was raised. No further customer response is required.</span></div>', unsafe_allow_html=True)
                else:
                    customer_confirmed_key = f"customer_confirmed_{active_user}_{current.case_id}"
                    if st.session_state.get(customer_confirmed_key, False):
                        st.markdown(f'<div class="chat-confirm"><strong>Customer confirmation received</strong><br><span class="muted">Processing the simulated {safe_text(request_type_for(current))}...</span></div>', unsafe_allow_html=True)
                        current.agent_approved = True
                        current.request_status = RequestStatus.AGENT_APPROVED
                        current.case_status = CaseStatus.SUBMITTED_SIMULATED
                        current.reference_id = request_id_for(current)
                        current.request_status = RequestStatus.SIMULATED_SUBMITTED
                        current.approved_at = datetime.now()
                        current.last_updated_at = current.approved_at
                        thread.append({"role": "agent", "text": f"[processing] Simulated {request_type_for(current)}..."})
                        thread.append({"role": "agent", "text": submission_response(current)})
                        st.session_state.sent_replies[current.case_id] = submission_response(current)
                        st.session_state[submission_key] = True
                        save_saved_state()
                        st.rerun()
                    else:
                        reply_key = f"reply_{active_user}_{current.case_id}"
                        reply_submit_key = f"submit_reply_{active_user}_{current.case_id}"
                        reply_reset_key = f"reset_reply_{active_user}_{current.case_id}"
                        if st.session_state.pop(reply_reset_key, False):
                            st.session_state[reply_key] = ""
                        reply_text = st.text_input("Reply to customer", key=reply_key, label_visibility="collapsed", placeholder="Reply: Yes, I confirm", on_change=mark_reply_submitted, args=(reply_key, reply_submit_key))
                        send_col, note_col = st.columns([1, 1], gap="small")
                        with send_col:
                            if st.button("Send customer reply", key=f"send_reply_{active_user}_{current.case_id}", type="primary", width="stretch") or reply_submit_key in st.session_state:
                                reply_text = st.session_state.pop(reply_submit_key, reply_text)
                                if reply_text.strip():
                                    normalized = reply_text.lower().replace("'", "")
                                    if "confirm" in normalized or normalized.strip() in {"yes", "yes i confirm", "y"}:
                                        thread.append({"role": "customer", "text": reply_text.strip()})
                                        thread.append({"role": "agent", "text": f"Thank you. Your confirmation was received. The simulated {request_type_for(current)} will be submitted automatically."})
                                        st.session_state[customer_confirmed_key] = True
                                        st.session_state.pop(reply_key, None)
                                        st.session_state.pop(reply_submit_key, None)
                                        st.session_state[reply_reset_key] = True
                                        save_saved_state()
                                        st.rerun()
                                    else:
                                        note("Confirmation needed", "Ask the customer to reply with a clear confirmation, such as: Yes, I confirm.", "hold")
                        with note_col:
                            if st.button("Save draft", key=f"save_reply_{active_user}_{current.case_id}", width="stretch"):
                                note("Draft saved", "Customer reply draft saved in this demo session.", "info")

                    if st.session_state.get(customer_confirmed_key, False):
                        pass
                    else:
                        st.markdown('<div class="chat-note"><span>Internal note</span></div>', unsafe_allow_html=True)
                        internal_note = st.text_area("Internal note", key=f"note_{active_user}_{current.case_id}", height=65, label_visibility="collapsed", placeholder="Add an internal note for the operations team...")
                        if internal_note:
                            st.caption("Internal note is visible to agents only.")
            elif current.category is Category.AUTHORISED_BUT_SCAMMED and current.selected_payment:
                st.markdown('<div class="chat-confirm"><strong>Manual review required</strong><br><span class="muted">The payment was matched. Authorised-scam claims are escalated with no recovery promise; customer confirmation is not required because no request will be submitted automatically.</span></div>', unsafe_allow_html=True)
            elif current.selected_payment and current.deadline and current.deadline < date.today():
                st.markdown('<div class="chat-confirm"><strong>Manual review required</strong><br><span class="muted">The payment-exception deadline has passed. No late request will be raised automatically.</span></div>', unsafe_allow_html=True)
            elif current.selected_payment and current.remedy and not current.remedy.available:
                st.markdown(f'<div class="chat-confirm"><strong>No inter-bank request</strong><br><span class="muted">{safe_text(no_remedy_reason(current))} No customer confirmation is required.</span></div>', unsafe_allow_html=True)
            else:
                st.caption("Waiting for a confirmed payment before a request can be raised.")
        else:
            st.markdown(f'<div class="wa-message customer"><span>Customer</span>{safe_text(claim.strip())}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-card">Start with the customer story. The original message will appear beside the structured case review.</div>', unsafe_allow_html=True)
    st.markdown("### Case History")
    if history:
        for item in reversed(history[-5:]):
            item_status, _ = result_status(item)
            label = CATEGORY_LABELS.get(item.claim_category, "INTAKE") if item.claim_category else "INTAKE"
            request_status_label = item.request_status.value.replace("_", " ").title()
            if st.button(item.case_id, key=f"open_case_{active_user}_{item.case_id}", width="stretch"):
                st.session_state.active_case_ids[active_user] = item.case_id
                st.session_state.active_case_id = item.case_id
                st.rerun()
            no_remedy = (
                item.case_status is CaseStatus.NO_REMEDY
                or item.request_status is RequestStatus.NOT_AVAILABLE
                or (item.remedy is not None and not item.remedy.available)
            )
            outcome_label = "Outcome" if no_remedy else "Approved"
            outcome_value = "No Inter-bank Request" if no_remedy else format_case_date(item.approved_at)
            outcome_detail = "Policy Decision" if no_remedy else f"Reference {item.reference_id or 'Not submitted'}"
            st.markdown(
                f'<div class="timeline-item">'
                f'<div><strong>{safe_text(label)}</strong><small>{safe_text(item.case_id)}</small></div>'
                f'<div><span>Latest status</span><strong>{safe_text(item_status.replace("_", " ").title())}</strong><small>{safe_text(request_status_label)}</small></div>'
                f'<div><span>Raised</span><strong>{safe_text(format_case_date(item.raised_at))}</strong><small>Last updated {safe_text(format_case_date(item.last_updated_at))}</small></div>'
                f'<div><span>{outcome_label}</span><strong>{safe_text(outcome_value)}</strong><small>{safe_text(outcome_detail)}</small></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No previous cases for this demo user.")

with right:
    st.markdown('<div class="section-kicker">02 / Decision workspace</div>', unsafe_allow_html=True)
    st.markdown("### Structured Case Review")
    if current:
        render_result(current, history, active_user)
    else:
        st.markdown('<div class="empty-card"><h3>No active case</h3><p class="muted">Process a customer message to populate extracted facts, payment candidates, classification, remedy, deadline, and generated outputs.</p></div>', unsafe_allow_html=True)

