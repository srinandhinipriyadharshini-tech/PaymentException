from __future__ import annotations

from decimal import Decimal


APPROXIMATE_AMOUNT_TOLERANCE = Decimal("0.25")
ABSTENTION_THRESHOLD = 0.45
AMBIGUITY_BAND = 0.10
MAX_CANDIDATES_IN_CUSTOMER_MESSAGE = 5


def approximate_amount_range(amount: Decimal) -> tuple[Decimal, Decimal]:
    tolerance = amount * APPROXIMATE_AMOUNT_TOLERANCE
    return amount - tolerance, amount + tolerance


def is_ambiguous(top_confidence: float, second_confidence: float) -> bool:
    return top_confidence - second_confidence < AMBIGUITY_BAND
