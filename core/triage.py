from __future__ import annotations

from core.models import CaseResult


def order_cases(cases: list[CaseResult]) -> list[CaseResult]:
    """Put actionable cases before clarification and no-remedy cases."""
    return sorted(cases, key=lambda case: (case.remedy_available is False, case.clarification_question is not None, -case.confidence))
