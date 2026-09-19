from datetime import date
from decimal import Decimal
from core.deadlines import calculate_deadline, is_expired
from core.models import Category, Payment
from core.rail_rules import calculate_remedy


def payment(rail="ACH"):
    return Payment(payment_id="PMT-SYN-000001", rail=rail, amount=Decimal("10"), currency="GBP", value_date=date(2026, 1, 2), settlement_timestamp="2026-01-02T09:00:00", debtor_account="ACCT-SYN-000001", creditor_account="ACCT-SYN-000251", creditor_registered_name="Northwind Supplies Ltd", creditor_trading_name="Northwind", status="SETTLED", funds_moved=True)


def test_all_four_categories(): assert {item.value for item in Category} == {"ERRONEOUS", "UNAUTHORISED", "AUTHORISED_BUT_SCAMMED", "NO_REMEDY"}

def test_deterministic_remedy_behavior():
    assert calculate_remedy(Category.ERRONEOUS, payment()).available
    assert not calculate_remedy(Category.NO_REMEDY, payment("RTP")).available

def test_expired_deadline():
    deadline = calculate_deadline(Category.ERRONEOUS, payment(), today=date(2026, 3, 1))
    assert deadline == date(2026, 2, 1)
    assert is_expired(deadline, date(2026, 3, 1))

def test_redaction():
    from core.redaction import redact
    assert "ACCT-SYN" not in redact("PMT-SYN-000001 ACCT-SYN-000001")
