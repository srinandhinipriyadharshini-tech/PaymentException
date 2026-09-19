from __future__ import annotations
from decimal import Decimal
from uuid import uuid4
from ai.demo_adapter import DemoAIAdapter
from core.deadlines import calculate_deadline
from core.decision_rules import ABSTENTION_THRESHOLD, AMBIGUITY_BAND
from core.models import CaseResult, CaseStatus, RankedCandidates, RequestStatus
from core.payment_search import get_payment, search_payments
from core.rail_rules import calculate_remedy
from core.redaction import redact


def process_claim(claim_text: str, db_path=None, adapter=None, agent_confirmed: bool = False, debtor_account: str | None = None, payment_id: str | None = None) -> CaseResult:
    adapter = adapter or DemoAIAdapter(); facts = adapter.extract_claim(claim_text)
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
        if facts.day_of_month and facts.amount_min is not None:
            stated_amount = (facts.amount_min + facts.amount_max) / 2 if facts.amount_max is not None else facts.amount_min
            question = f"I captured approximately {stated_amount:.2f} on day {facts.day_of_month}, but could not locate a payment. Please provide the correct date, beneficiary, or amount."
        elif facts.day_of_month:
            question = f"I captured day {facts.day_of_month}. Please provide the correct date, amount, or beneficiary so I can locate the payment."
        else:
            question = "Please provide an amount, date, or beneficiary so we can locate the payment."
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=0.0, clarification_question=question)
    if ranked.candidates[0].confidence < ABSTENTION_THRESHOLD:
        ranked.abstained = True; ranked.abstention_reason = "Claim is too vague to identify a payment."
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=ranked.candidates[0].confidence, clarification_question="Could you provide the payment amount and date or beneficiary?")
    specific_claim = bool(facts.amount_min and facts.amount_max and facts.date_min and facts.date_max and facts.beneficiary_description)
    if len(ranked.candidates) > 1 and ranked.candidates[0].confidence - ranked.candidates[1].confidence < AMBIGUITY_BAND and not specific_claim:
        return CaseResult(case_id=case_id, case_status=CaseStatus.CLARIFICATION_REQUIRED, extracted_facts=facts, ranked_candidates=ranked, confidence=ranked.candidates[0].confidence, clarification_question="Which of the similarly matched payments do you mean?")
    selected = ranked.candidates[0].payment; category, confidence, _ = adapter.classify_claim(claim_text, selected)
    remedy = calculate_remedy(category, selected); deadline = calculate_deadline(category, selected)
    customer, bank = adapter.draft_outputs(claim_text, selected, category)
    no_remedy = not remedy.available
    return CaseResult(case_id=case_id, case_status=CaseStatus.NO_REMEDY if no_remedy else CaseStatus.READY_FOR_REVIEW, claim_category=category, category=category, request_status=RequestStatus.NOT_AVAILABLE if no_remedy else RequestStatus.DRAFT_READY, rail=selected.rail, remedy_available=remedy.available, agent_approved=agent_confirmed, extracted_facts=facts, ranked_candidates=ranked, selected_payment=selected, remedy=remedy, deadline=deadline, confidence=confidence, customer_message=redact(customer), interbank_request=redact(bank), agent_confirmed=agent_confirmed)
