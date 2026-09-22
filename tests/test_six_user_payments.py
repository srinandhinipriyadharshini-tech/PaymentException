from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import duckdb

from data.create_database import create_database
from core.workflow import process_claim

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "payment_exceptions.duckdb"
EXPECTATIONS = ROOT / "data" / "six_user_payment_expectations.csv"
EXPECTED_IDS = {f"PMT-SYN-{index:06d}" for index in range(1001, 1013)}


def setup_module() -> None:
    create_database(DB)


def load_expectations() -> list[dict[str, str]]:
    with EXPECTATIONS.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_uploaded_rows_cover_all_six_accounts() -> None:
    rows = load_expectations()
    assert len(rows) == 12
    assert {row["debtor_account"] for row in rows} == {f"ACCT-SYN-{index:06d}" for index in range(1, 7)}
    assert {row["payment_id"] for row in rows} == EXPECTED_IDS


def test_uploaded_rows_are_seeded_with_expected_values() -> None:
    connection = duckdb.connect(str(DB), read_only=True)
    actual = {
        row[0]: row[1:]
        for row in connection.execute(
            "SELECT payment_id, debtor_account, rail, amount, status, funds_moved "
            "FROM payments WHERE payment_id BETWEEN 'PMT-SYN-001001' AND 'PMT-SYN-001012'"
        ).fetchall()
    }
    connection.close()

    for expected in load_expectations():
        debtor_account, rail, amount, status, funds_moved = actual[expected["payment_id"]]
        assert debtor_account == expected["debtor_account"]
        assert rail == expected["rail"]
        assert amount == Decimal(expected["amount"])
        assert status == expected["status"]
        assert funds_moved is (expected["funds_moved"].lower() == "true")


def test_uploaded_rows_preserve_rail_coverage_and_status_mix() -> None:
    rows = load_expectations()
    assert {row["rail"] for row in rows} == {"ACH", "WIRE", "RTP", "FEDNOW"}
    assert {row["status"] for row in rows} == {"SETTLED", "PENDING", "REJECTED", "FAILED", "CANCELLED", "RETURNED"}
    assert sum(row["funds_moved"].lower() == "true" for row in rows) == 6


def test_expectations_document_policy_behavior() -> None:
    rows = load_expectations()
    final_rail_rows = [row for row in rows if row["rail"] in {"RTP", "FEDNOW"} and row["funds_moved"].lower() == "true"]
    assert {row["payment_id"] for row in final_rail_rows} == {
        "PMT-SYN-001004",
        "PMT-SYN-001008",
        "PMT-SYN-001010",
        "PMT-SYN-001012",
    }
    assert all("no recovery request" in row["expected_behavior"].lower() for row in final_rail_rows)


def test_pending_rtp_and_wire_cases_can_start_recovery_requests() -> None:
    rtp = process_claim(
        "I made a mistake with the pending RTP payment of GBP 799 on 2026-09-21 to John.",
        DB,
        debtor_account="ACCT-SYN-000002",
    )
    wire = process_claim(
        "I did not authorise the pending WIRE payment of GBP 999999 on 2026-09-21 to Litware.",
        DB,
        debtor_account="ACCT-SYN-000005",
    )
    assert rtp.selected_payment and rtp.selected_payment.payment_id == "PMT-SYN-001002"
    assert rtp.remedy and rtp.remedy.available and rtp.remedy.message_type == "rtp_return_request"
    assert wire.selected_payment and wire.selected_payment.payment_id == "PMT-SYN-001011"
    assert wire.remedy and wire.remedy.available and wire.remedy.message_type == "wire_recall_request"


def test_terminal_payment_statuses_do_not_start_recovery_requests() -> None:
    result = process_claim(
        "I made a mistake with the cancelled WIRE payment of GBP 85000 on 2026-09-22 to Tailspin.",
        DB,
        debtor_account="ACCT-SYN-000001",
    )
    assert result.selected_payment and result.selected_payment.payment_id == "PMT-SYN-001007"
    assert result.remedy and not result.remedy.available
