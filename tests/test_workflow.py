from pathlib import Path
from data.create_database import create_database
from core.models import Category
from core.workflow import process_claim
from ai.demo_adapter import DemoAIAdapter

DB = Path(__file__).resolve().parents[1] / "data" / "payment_exceptions.duckdb"


def setup_module(): create_database(DB)


def test_day_only_clarification_formats_are_extracted():
    adapter = DemoAIAdapter()
    assert adapter.extract_claim("26").day_of_month == 26
    assert adapter.extract_claim("26th").day_of_month == 26
    assert adapter.extract_claim("on the 26th").day_of_month == 26


def test_later_date_clarification_replaces_earlier_day():
    facts = DemoAIAdapter().extract_claim(
        "someone took about $9000 from my account on the 20th. Clarification: on the 26th May"
    )
    assert facts.day_of_month == 26
    assert facts.month_of_year == 5


def test_written_amount_is_extracted():
    facts = DemoAIAdapter().extract_claim("about eight thousand to the plumber")
    assert facts.amount_min == 8000
    assert facts.amount_max == 8000


def test_unmatched_amount_and_day_asks_for_correct_criteria():
    result = process_claim("someone took about $9000 from my account on the 20th, i never authorized it.", DB)
    assert "approximately 9000.00" in result.clarification_question
    assert "correct date" in result.clarification_question
    assert "beneficiary" in result.clarification_question


def test_customer_account_resolves_duplicate_northwind_payment():
    result = process_claim(
        "someone took about $1000 from my account on the 2nd, i never authorized it. it says Northwind",
        DB,
        debtor_account="ACCT-SYN-000001",
    )
    assert result.selected_payment is not None
    assert result.selected_payment.payment_id == "PMT-SYN-000001"


def test_natural_month_date_matches_erroneous_payment():
    result = process_claim("I made a mistake with the ACH payment of £1800 on September 9 to Northwind. Please request its return.", DB)
    assert result.selected_payment is not None
    assert result.selected_payment.payment_id == "PMT-SYN-000006"
    assert result.category is Category.ERRONEOUS


def test_exact_cedar_amount_and_day_matches_single_payment():
    result = process_claim("sent $152788.25 for Cedar on the 24th i didnt authorize it", DB)
    assert result.selected_payment is not None
    assert result.selected_payment.payment_id == "PMT-SYN-003777"
    assert result.category is Category.UNAUTHORISED


def test_plain_english_variations_extract_search_facts():
    facts = DemoAIAdapter().extract_claim("roughly thirty eight grand, it was for Cedar around September 9")
    assert facts.amount_min == 28500
    assert facts.amount_max == 47500
    assert facts.month_of_year == 9
    assert facts.day_of_month == 9
    assert facts.beneficiary_description == "Cedar Works"


def test_duplicate_matches_are_shown_for_clarification():
    result = process_claim("someone took about $1000 from my account on the 2nd, i never authorized it. it says Northwind", DB)
    assert result.selected_payment is None
    assert len(result.ranked_candidates.candidates) == 2
    assert result.clarification_question == "Which of the similarly matched payments do you mean?"


def test_explicit_payment_choice_resolves_duplicate():
    result = process_claim(
        "someone took about $1000 from my account on the 2nd, i never authorized it. it says Northwind",
        DB,
        payment_id="PMT-SYN-000002",
    )
    assert result.selected_payment and result.selected_payment.payment_id == "PMT-SYN-000002"


def test_ambiguous_candidate_clarification():
    result = process_claim("I do not recognise the ACH payment of £1250.", DB)
    assert result.clarification_question and result.selected_payment is None


def test_end_to_end_clear_claim():
    result = process_claim("I did not make the ACH payment of £1250 on 2026-01-02 to Northwind.", DB)
    assert result.selected_payment and result.category is Category.UNAUTHORISED
    assert result.remedy and result.deadline and result.customer_message


def test_submission_disabled_when_unsafe():
    result = process_claim("I do not recognise the ACH payment of £1250.", DB)
    assert not result.submission_allowed


def test_unmatched_claim_returns_clarification():
    result = process_claim("someone took about $412 from my account on the 4th, i never authorized it. it says northgate.", DB)
    assert result.selected_payment is None
    assert result.clarification_question


def test_approximate_amount_and_day_find_available_record():
    result = process_claim("someone took about $73000 from my account on the 20th, i never authorized it. it says Northwind", DB)
    assert result.selected_payment is not None
    assert result.selected_payment.payment_id == "PMT-SYN-004501"
    assert result.clarification_question is None


def test_all_category_paths():
    for phrase, category in [("wrong payment", Category.ERRONEOUS), ("scam payment", Category.AUTHORISED_BUT_SCAMMED), ("instant payment", Category.NO_REMEDY)]:
        result = process_claim(f"The ACH payment of £1250 on 2026-01-02 to Northwind was a {phrase}.", DB)
        assert result.category is category or (category is Category.NO_REMEDY and result.category is Category.NO_REMEDY)
