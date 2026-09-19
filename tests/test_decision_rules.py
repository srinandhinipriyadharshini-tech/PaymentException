from decimal import Decimal

from core.decision_rules import approximate_amount_range, is_ambiguous


def test_approximate_amount_rule():
    assert approximate_amount_range(Decimal("1000")) == (Decimal("750.00"), Decimal("1250.00"))


def test_ambiguity_band_rule():
    assert is_ambiguous(0.80, 0.75)
    assert not is_ambiguous(0.80, 0.69)
