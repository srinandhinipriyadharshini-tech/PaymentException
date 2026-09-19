from pathlib import Path
import duckdb
from data.create_database import create_database

DB = Path(__file__).resolve().parents[1] / "data" / "payment_exceptions.duckdb"


def setup_module(): create_database(DB)


def test_exactly_6000_records():
    connection = duckdb.connect(str(DB), read_only=True)
    assert connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 6000
    connection.close()


def test_unique_payment_ids():
    connection = duckdb.connect(str(DB), read_only=True)
    assert connection.execute("SELECT COUNT(DISTINCT payment_id) FROM payments").fetchone()[0] == 6000
    connection.close()


def test_all_four_rails():
    connection = duckdb.connect(str(DB), read_only=True)
    assert {row[0] for row in connection.execute("SELECT DISTINCT rail FROM payments").fetchall()} == {"ACH", "WIRE", "RTP", "FEDNOW"}
    connection.close()


def test_demo_month_and_status_scenarios():
    connection = duckdb.connect(str(DB), read_only=True)
    rows = connection.execute("SELECT payment_id, rail, value_date, status, funds_moved FROM payments WHERE payment_id IN ('PMT-SYN-004997', 'PMT-SYN-004998', 'PMT-SYN-004999', 'PMT-SYN-005000') ORDER BY payment_id").fetchall()
    connection.close()
    assert [(row[1], str(row[2]), row[3], row[4]) for row in rows] == [
        ("ACH", "2026-07-25", "SETTLED", True),
        ("WIRE", "2026-08-14", "SETTLED", True),
        ("RTP", "2026-09-05", "SETTLED", True),
        ("FEDNOW", "2026-09-12", "PENDING", False),
    ]


def test_new_users_have_recent_transactions():
    connection = duckdb.connect(str(DB), read_only=True)
    rows = connection.execute("SELECT debtor_account, value_date FROM payments WHERE payment_id IN ('PMT-SYN-000004', 'PMT-SYN-000005', 'PMT-SYN-000006') ORDER BY payment_id").fetchall()
    connection.close()
    assert [(account, str(value_date)) for account, value_date in rows] == [
        ("ACCT-SYN-000004", "2026-07-18"),
        ("ACCT-SYN-000005", "2026-08-21"),
        ("ACCT-SYN-000006", "2026-09-09"),
    ]


def test_each_demo_user_has_1000_transactions():
    connection = duckdb.connect(str(DB), read_only=True)
    rows = connection.execute("SELECT debtor_account, COUNT(*) FROM payments GROUP BY debtor_account ORDER BY debtor_account").fetchall()
    connection.close()
    assert rows == [(f"ACCT-SYN-{index:06d}", 1000) for index in range(1, 7)]
