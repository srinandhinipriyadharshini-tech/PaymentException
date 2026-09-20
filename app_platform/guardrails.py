from __future__ import annotations

from core.models import CaseResult, CaseStatus


def validate_result(result: CaseResult) -> list[str]:
    violations: list[str] = []
    if result.selected_payment and result.remedy:
        if result.selected_payment.rail in {"RTP", "FEDNOW"} and result.remedy.available:
            violations.append("instant rail cannot expose an available remedy")
        if not result.remedy.available and result.case_status not in {CaseStatus.NO_REMEDY, CaseStatus.CLARIFICATION_REQUIRED}:
            violations.append("unavailable remedy has an invalid case status")
    if result.clarification_question and result.selected_payment:
        violations.append("clarification result must not select a payment")
    for output in (result.customer_message, result.interbank_request):
        if "ACCT-SYN-" in output or "PMT-SYN-" in output:
            violations.append("output contains synthetic payment PII or identifiers")
    return violations