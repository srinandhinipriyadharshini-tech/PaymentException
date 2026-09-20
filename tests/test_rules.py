from datetime import date
from decimal import Decimal
from core.deadlines import calculate_deadline, is_expired
from core.models import Category, Payment
from core.rail_rules import calculate_remedy


def payment(rail="ACH", moved=True):
    return Payment(payment_id="PMT-SYN-000001", rail=rail, amount=Decimal("10"), currency="GBP", value_date=date(2026, 1, 2), settlement_timestamp="2026-01-02T09:00:00", debtor_account="ACCT-SYN-000001", creditor_account="ACCT-SYN-000251", creditor_registered_name="Northwind Supplies Ltd", creditor_trading_name="Northwind", status="SETTLED", funds_moved=moved)


def test_all_four_categories(): assert {item.value for item in Category} == {"ERRONEOUS", "UNAUTHORISED", "AUTHORISED_BUT_SCAMMED", "NO_REMEDY"}

def test_deterministic_remedy_behavior():
    assert calculate_remedy(Category.ERRONEOUS, payment()).available
    assert not calculate_remedy(Category.NO_REMEDY, payment("RTP")).available
    ach = calculate_remedy(Category.ERRONEOUS, payment())
    assert (ach.message_type, ach.reason_code, ach.deadline_days, ach.recovery_guaranteed) == ("AC_RETURN", "SYN_R02", 5, False)
    wire = calculate_remedy(Category.ERRONEOUS, payment("WIRE"))
    assert (wire.message_type, wire.reason_code, wire.deadline_days) == ("wire_recall_request", "SYN_W01", 1)
    assert calculate_remedy(Category.UNAUTHORISED, payment("WIRE")).available
    assert calculate_remedy(Category.ERRONEOUS, payment("RTP")).message_type == "rtp_return_request"
    assert calculate_remedy(Category.UNAUTHORISED, payment("FEDNOW", moved=False)).available


def test_authorised_scam_preserves_category_without_recovery_promise():
    remedy = calculate_remedy(Category.AUTHORISED_BUT_SCAMMED, payment("ACH"))
    assert remedy.category is Category.AUTHORISED_BUT_SCAMMED
    assert not remedy.available
    assert remedy.requires_human_review

def test_expired_deadline():
    deadline = calculate_deadline(Category.ERRONEOUS, payment(), today=date(2026, 3, 1))
    assert deadline == date(2026, 1, 7)
    assert is_expired(deadline, date(2026, 3, 1))

def test_redaction():
    from core.redaction import redact
    assert "ACCT-SYN" not in redact("PMT-SYN-000001 ACCT-SYN-000001")
