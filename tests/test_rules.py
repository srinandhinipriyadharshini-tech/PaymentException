from datetime import date
from decimal import Decimal

from core.deadlines import calculate_deadline, is_expired
from core.models import Category, Payment
from core.rail_rules import calculate_remedy


def payment(rail="ACH", *, status="SETTLED", funds_moved=True):
    return Payment(
        payment_id="PMT-SYN-000001",
        rail=rail,
        amount=Decimal("10"),
        currency="GBP",
        value_date=date(2026, 1, 2),
        settlement_timestamp="2026-01-02T09:00:00",
        debtor_account="ACCT-SYN-000001",
        creditor_account="ACCT-SYN-000251",
        creditor_registered_name="Northwind Supplies Ltd",
        creditor_trading_name="Northwind",
        status=status,
        funds_moved=funds_moved,
    )


def test_all_four_rails_follow_rulebook():
    assert calculate_remedy(Category.UNAUTHORISED, payment("ACH")).message_type == "AC_RETURN"
    assert calculate_remedy(Category.ERRONEOUS, payment("WIRE")).message_type == "wire_recall_request"
    assert calculate_remedy(Category.UNAUTHORISED, payment("RTP", status="PENDING", funds_moved=False)).message_type == "payment_cancel_request"
    assert calculate_remedy(Category.UNAUTHORISED, payment("FEDNOW", status="PENDING", funds_moved=False)).message_type == "payment_cancel_request"


def test_ach_requires_signed_statement_before_return_request():
    remedy = calculate_remedy(Category.UNAUTHORISED, payment("ACH"), signed_statement_received=False)
    assert remedy.available is False
    assert remedy.message_type == "none"
    assert remedy.reason_code == "none"


def test_ach_unauthorised_deadline_is_calendar_days_and_recovery_is_not_guaranteed():
    remedy = calculate_remedy(Category.UNAUTHORISED, payment("ACH"), signed_statement_received=True)
    assert remedy.message_type == "AC_RETURN"
    assert remedy.reason_code == "SYN_R10"
    assert remedy.deadline_days == 60
    assert remedy.recovery_guaranteed is False


def test_ach_erroneous_has_banking_day_deadline():
    remedy = calculate_remedy(Category.ERRONEOUS, payment("ACH"))
    assert remedy.message_type == "AC_RETURN"
    assert remedy.reason_code == "SYN_R02"
    assert remedy.deadline_days == 5
    deadline = calculate_deadline(Category.ERRONEOUS, payment("ACH"))
    assert deadline == date(2026, 1, 9)


def test_wire_and_rtp_fednow_rules_are_specific_to_rails():
    wire = calculate_remedy(Category.ERRONEOUS, payment("WIRE"))
    assert wire.message_type == "wire_recall_request"
    assert wire.reason_code == "SYN_W01"

    rtp = calculate_remedy(Category.UNAUTHORISED, payment("RTP", status="PENDING", funds_moved=False), feature_flags={"ENABLE_PENDING_CANCEL": False})
    assert rtp.message_type == "rtp_return_request"
    assert rtp.reason_code == "SYN_rtp01"

    fednow = calculate_remedy(Category.UNAUTHORISED, payment("FEDNOW", status="PENDING", funds_moved=False), feature_flags={"ENABLE_PENDING_CANCEL": False})
    assert fednow.message_type == "fednow_return_request"
    assert fednow.reason_code == "SYN_fn01"


def test_rtp_and_fednow_do_not_allow_request_after_settlement_when_flag_is_false():
    rtp = calculate_remedy(Category.UNAUTHORISED, payment("RTP", status="SETTLED", funds_moved=True))
    assert rtp.available is False
    assert rtp.message_type == "none"

    fednow = calculate_remedy(Category.UNAUTHORISED, payment("FEDNOW", status="SETTLED", funds_moved=True))
    assert fednow.available is False
    assert fednow.message_type == "none"


def test_pending_payment_extension_is_cancel_request_for_all_four_rails():
    for rail in ("ACH", "WIRE", "RTP", "FEDNOW"):
        remedy = calculate_remedy(Category.UNAUTHORISED, payment(rail, status="PENDING", funds_moved=False))
        assert remedy.available is True
        assert remedy.message_type == "payment_cancel_request"
        assert remedy.reason_code == "SYN_CANCEL01"


def test_authorised_but_scammed_is_manual_review_only():
    remedy = calculate_remedy(Category.AUTHORISED_BUT_SCAMMED, payment("WIRE"))
    assert remedy.available is False
    assert remedy.requires_human_review is True
    assert remedy.message_type == "none"


def test_expired_window_is_translated_to_deadline_expired_logic():
    deadline = calculate_deadline(Category.ERRONEOUS, payment("WIRE"))
    assert deadline == date(2026, 1, 3)
    assert is_expired(deadline, date(2026, 1, 4)) is True


def test_rulebook_recovery_guarantee_is_always_false():
    for rail in ("ACH", "WIRE", "RTP", "FEDNOW"):
        remedy = calculate_remedy(Category.UNAUTHORISED, payment(rail, status="PENDING", funds_moved=False))
        assert remedy.recovery_guaranteed is False
