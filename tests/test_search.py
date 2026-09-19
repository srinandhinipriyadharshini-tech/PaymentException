from datetime import date
from decimal import Decimal
from pathlib import Path
from core.models import ExtractedFacts
from core.payment_search import search_payments
from data.create_database import create_database

DB = Path(__file__).resolve().parents[1] / "data" / "payment_exceptions.duckdb"


def setup_module(): create_database(DB)


def test_exact_search_match():
    facts = ExtractedFacts(amount_min=Decimal("1250"), amount_max=Decimal("1250"), date_min=date(2026, 1, 2), date_max=date(2026, 1, 2))
    assert {item.payment_id for item in search_payments(facts, DB)} == {"PMT-SYN-000001", "PMT-SYN-000002"}


def test_approximate_search_match():
    facts = ExtractedFacts(amount_min=Decimal("1249"), amount_max=Decimal("1251"), date_min=date(2026, 1, 2), date_max=date(2026, 1, 2))
    assert search_payments(facts, DB)[0].amount == Decimal("1250.00")


def test_trading_name_search():
    facts = ExtractedFacts(beneficiary_description="Northwind")
    results = search_payments(facts, DB)
    assert results and all("Northwind" in item.creditor_trading_name for item in results)
