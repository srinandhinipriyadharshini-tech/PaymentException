from ai.classification import ClassificationAI
from ai.drafting import DraftingAI
from ai.intake import IntakeAI
from ai.matching import MatchingAI
from core.models import Category, Payment, Remedy
from datetime import date
from decimal import Decimal


def test_intake_abstains_without_searchable_facts():
    result = IntakeAI().extract("The payment is a problem")
    assert result.abstained and result.value is None


def test_intake_extracts_uploaded_litware_claim():
    result = IntakeAI().extract("I did not authorise the pending WIRE payment of GBP 999999 on 2026-09-21 to Litware.")
    assert result.value.amount_min == Decimal("999999")
    assert result.value.amount_max == Decimal("999999")
    assert result.value.date_min == date(2026, 9, 21)
    assert result.value.rail == "WIRE"
    assert result.value.beneficiary_description == "Litware"


def test_matching_abstains_when_candidates_are_empty():
    result = MatchingAI().rank(IntakeAI().extract("26th").value, [])
    assert result.abstained and result.value is not None


def test_drafting_states_no_remedy_plainly():
    payment = Payment(
        payment_id="PMT-SYN-000001", rail="RTP", amount=Decimal("10"), currency="GBP",
        value_date=date(2026, 1, 2), settlement_timestamp="2026-01-02T09:00:00",
        debtor_account="ACCT-SYN-000001", creditor_account="ACCT-SYN-000251",
        creditor_registered_name="Northwind Supplies Ltd", creditor_trading_name="Northwind",
        status="SETTLED", funds_moved=True,
    )
    remedy = Remedy(category=Category.NO_REMEDY, action="None", rationale="Final rail", available=False)
    result = DraftingAI().draft("scam payment", payment, Category.NO_REMEDY, remedy)
    assert result.value and "No remedy is available" in result.value.customer_message