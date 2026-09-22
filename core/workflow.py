from __future__ import annotations
from datetime import date
from decimal import Decimal
from uuid import uuid4
from ai.demo_adapter import DemoAIAdapter
from core.deadlines import calculate_deadline
from core.decision_rules import ABSTENTION_THRESHOLD, AMBIGUITY_BAND
from core.models import CaseResult, CaseStatus, Category, RankedCandidates, RequestStatus
from core.payment_search import get_payment, search_payments
from core.rail_rules import calculate_remedy
from core.redaction import redact


def process_claim(claim_text: str, db_path=None, adapter=None, agent_confirmed: bool = False, debtor_account: str | None = None, payment_id: str | None = None) -> CaseResult:
    adapter = adapter or DemoAIAdapter(); facts = adapter.extract_claim(claim_text)
    if debtor_account:
        facts = facts.model_copy(update={"customer_account": debtor_account})
    missing_facts = []
    if facts.amount_min is None and facts.amount_max is None:
        missing_facts.append("the payment amount")
    if not facts.beneficiary_description:
        missing_facts.append("the beneficiary")
    if not ((facts.date_min and facts.date_max) or facts.day_of_month):
        missing_facts.append("the payment date")
    if missing_facts and not payment_id:
        joined = ", ".join(missing_facts[:-1]) + (f", and {missing_facts[-1]}" if len(missing_facts) > 1 else missing_facts[0])
        return CaseResult(case_id=f"CASE-SYN-{uuid4().int % 1000000:06d}", case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=RankedCandidates(), confidence=0.0, clarification_question=f"Please provide {joined} so I can confirm the payment before classifying the claim.")
    selected_by_id = get_payment(payment_id, db_path) if payment_id and db_path else get_payment(payment_id) if payment_id else None
    candidates = [selected_by_id] if selected_by_id else search_payments(facts, db_path=db_path) if db_path else search_payments(facts)
    if debtor_account:
        candidates = [item for item in candidates if item.debtor_account == debtor_account]
    ranking_facts = facts
    if not candidates and facts.amount_min is not None and facts.amount_max is not None and facts.day_of_month is not None:
        stated_amount = (facts.amount_min + facts.amount_max) / 2
        ranking_facts = facts.model_copy(update={
            "amount_min": stated_amount * Decimal("0.90"),
            "amount_max": stated_amount * Decimal("1.10"),
        })
        candidates = search_payments(ranking_facts, db_path=db_path) if db_path else search_payments(ranking_facts)
        if debtor_account:
            candidates = [item for item in candidates if item.debtor_account == debtor_account]
    if not candidates and facts.day_of_month is not None:
        ranking_facts = facts.model_copy(update={"amount_min": None, "amount_max": None})
        candidates = search_payments(ranking_facts, db_path=db_path) if db_path else search_payments(ranking_facts)
        if debtor_account:
            candidates = [item for item in candidates if item.debtor_account == debtor_account]
    if payment_id and not selected_by_id:
        candidates = [item for item in candidates if item.payment_id == payment_id]
    ranked = RankedCandidates(candidates=adapter.rank_candidates(ranking_facts, candidates))
    case_id = f"CASE-SYN-{uuid4().int % 1000000:06d}"
    if not ranked.candidates:
        complete_search_facts = bool(
            facts.amount_min is not None
            and facts.amount_max is not None
            and facts.date_min is not None
            and facts.date_max is not None
            and facts.beneficiary_description
        )
        if complete_search_facts:
            amount_label = f"{facts.amount_min:,.2f}" if facts.amount_min == facts.amount_max else f"{facts.amount_min:,.2f} to {facts.amount_max:,.2f}"
            question = (
                f"There is no transaction available for amount {amount_label} on {facts.date_min} "
                f"to {facts.beneficiary_description} for this customer account. "
                "Please provide the correct amount, date, or beneficiary."
            )
        elif facts.day_of_month and facts.amount_min is not None:
            stated_amount = (facts.amount_min + facts.amount_max) / 2 if facts.amount_max is not None else facts.amount_min
            question = f"I captured approximately {stated_amount:.2f} on day {facts.day_of_month}, but could not locate a payment. Please provide the correct date, beneficiary, or amount."
        elif facts.week_of_month and facts.month_of_year and facts.amount_min is not None:
            stated_amount = (facts.amount_min + facts.amount_max) / 2 if facts.amount_max is not None else facts.amount_min
            question = f"I could not locate a payment of approximately {stated_amount:.2f} in week {facts.week_of_month} of month {facts.month_of_year}. Please confirm the amount, exact date, or beneficiary."
        elif facts.day_of_month:
            question = f"I captured day {facts.day_of_month}. Please provide the correct date, amount, or beneficiary so I can locate the payment."
        else:
            question = "Please provide an amount, date, or beneficiary so we can locate the payment."
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=0.0, clarification_question=question)
    if ranked.candidates[0].confidence < ABSTENTION_THRESHOLD and not selected_by_id:
        ranked.abstained = True; ranked.abstention_reason = "Claim is too vague to identify a payment."
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=ranked.candidates[0].confidence, clarification_question="Could you provide the payment amount and date or beneficiary?")
    specific_claim = bool(facts.amount_min and facts.amount_max and facts.date_min and facts.date_max and facts.beneficiary_description)
    if len(ranked.candidates) > 1 and ranked.candidates[0].confidence - ranked.candidates[1].confidence < AMBIGUITY_BAND and not specific_claim:
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=ranked.candidates[0].confidence, clarification_question="Which of the similarly matched payments do you mean?")
    amount_is_non_exact = facts.amount_min != facts.amount_max
    if (facts.amount_min is not None or facts.amount_max is not None) and amount_is_non_exact and not selected_by_id:
        candidate = ranked.candidates[0].payment
        return CaseResult(
            case_id=case_id,
            case_status=CaseStatus.CLARIFICATION_REQUIRED,
            extracted_facts=facts,
            ranked_candidates=ranked,
            confidence=ranked.candidates[0].confidence,
            clarification_question=f"I found a {candidate.currency} {candidate.amount:,.2f} payment on {candidate.value_date} to {candidate.creditor_trading_name}. You mentioned an approximate amount. Please confirm this payment or choose another option before I classify the claim.",
        )
    selected = ranked.candidates[0].payment; category, confidence, _ = adapter.classify_claim(claim_text, selected)
    remedy = calculate_remedy(category, selected); deadline = calculate_deadline(category, selected)
    deadline_expired = deadline is not None and deadline < date.today()
    if deadline_expired and remedy.available:
        remedy = remedy.model_copy(update={"available": False, "requires_human_review": True, "rationale": "Configured recovery window has expired; escalate and close without submitting a request."})
    customer, bank = adapter.draft_outputs(claim_text, selected, category)
    no_remedy = not remedy.available
    if not no_remedy:
        bank = f"message_type={remedy.message_type}; reason_code={remedy.reason_code}; deadline_days={remedy.deadline_days}; recovery_guaranteed={str(remedy.recovery_guaranteed).upper()}; category={category.value}"
    requires_manual_escalation = deadline_expired or category is Category.AUTHORISED_BUT_SCAMMED
    case_status = CaseStatus.ESCALATED if requires_manual_escalation else CaseStatus.NO_REMEDY if no_remedy else CaseStatus.READY_FOR_REVIEW
    return CaseResult(case_id=case_id, case_status=case_status, claim_category=category, category=category, request_status=RequestStatus.NOT_AVAILABLE if not remedy.available else RequestStatus.DRAFT_READY, rail=selected.rail, remedy_available=remedy.available, agent_approved=agent_confirmed, extracted_facts=facts, ranked_candidates=ranked, selected_payment=selected, remedy=remedy, deadline=deadline, confidence=confidence, customer_message=redact(customer), interbank_request=redact(bank), agent_confirmed=agent_confirmed)
