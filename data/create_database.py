from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).with_name("payment_exceptions.duckdb")
SEED = 20260919
RAILS = ("ACH", "WIRE", "RTP", "FEDNOW")

USER_TEST_PAYMENTS = [
    ("PMT-SYN-001001", "ACH", Decimal("1250.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 9, 0), "ACCT-SYN-000001", "ACCT-SYN-000251", "Northwind Supplies Ltd", "Northwind", "SETTLED", True),
    ("PMT-SYN-001002", "RTP", Decimal("799.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 9, 0), "ACCT-SYN-000002", "ACCT-SYN-000252", "John Smith", "John", "PENDING", False),
    ("PMT-SYN-001003", "WIRE", Decimal("250000.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 9, 30), "ACCT-SYN-000003", "ACCT-SYN-000253", "Fabrikam Treasury Services", "Fabrikam", "SETTLED", True),
    ("PMT-SYN-001004", "FEDNOW", Decimal("1900.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 9, 35), "ACCT-SYN-000004", "ACCT-SYN-000254", "Contoso Retail Ltd", "Contoso", "SETTLED", True),
    ("PMT-SYN-001005", "ACH", Decimal("150.00"), "GBP", datetime(2026, 9, 21).date(), None, "ACCT-SYN-000005", "ACCT-SYN-000255", "Adventure Works Ltd", "Adventure", "REJECTED", False),
    ("PMT-SYN-001006", "RTP", Decimal("500.00"), "GBP", datetime(2026, 9, 21).date(), None, "ACCT-SYN-000006", "ACCT-SYN-000256", "", "Unknown", "FAILED", False),
    ("PMT-SYN-001007", "WIRE", Decimal("85000.00"), "GBP", datetime(2026, 9, 22).date(), None, "ACCT-SYN-000001", "ACCT-SYN-000257", "Tailspin Financial Services", "Tailspin", "CANCELLED", False),
    ("PMT-SYN-001008", "FEDNOW", Decimal("3200.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 10, 20), "ACCT-SYN-000002", "ACCT-SYN-000258", "Wingtip Technologies Ltd", "Wingtip", "SETTLED", True),
    ("PMT-SYN-001009", "ACH", Decimal("75.00"), "GBP", datetime(2026, 9, 21).date(), None, "ACCT-SYN-000003", "ACCT-SYN-000259", "Blue Yonder Airlines", "BlueYonder", "RETURNED", False),
    ("PMT-SYN-001010", "RTP", Decimal("1200.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 11, 10), "ACCT-SYN-000004", "ACCT-SYN-000260", "Johnathan Smith Holdings Ltd", "John", "SETTLED", True),
    ("PMT-SYN-001011", "WIRE", Decimal("999999.00"), "GBP", datetime(2026, 9, 21).date(), None, "ACCT-SYN-000005", "ACCT-SYN-000261", "Litware Global Treasury", "Litware", "PENDING", False),
    ("PMT-SYN-001012", "FEDNOW", Decimal("25.00"), "GBP", datetime(2026, 9, 21).date(), datetime(2026, 9, 21, 14, 5), "ACCT-SYN-000006", "ACCT-SYN-000262", "Woodgrove Bank Ltd", "Woodgrove", "SETTLED", True),
]


def build_rows() -> list[tuple]:
    base = datetime(2026, 7, 1, 9, 0)
    names = [("Northwind Supplies Ltd", "Northwind"), ("Blue Oak Services Ltd", "Blue Oak"), ("Cedar Works Inc", "Cedar Works"), ("Lumen Health Partners", "Lumen Health")]
    rows = []
    for index in range(1, 6001):
        registered, trading = names[(index - 1) % len(names)]
        amount = Decimal(f"{100 + index * 37 + (index % 100) / 100:.2f}")
        value_date = base.date() + timedelta(days=(index * 17) % 92)
        timestamp = datetime.combine(value_date, datetime.min.time()).replace(hour=9) + timedelta(minutes=(index * 13) % 600)
        status = "PENDING" if index % 17 == 0 else "SETTLED"
        rows.append((f"PMT-SYN-{index:06d}", RAILS[(index - 1) % 4], amount, "GBP", value_date, timestamp, f"ACCT-SYN-{((index - 1) % 6) + 1:06d}", f"ACCT-SYN-{index + 250:06d}", registered, trading, status, status == "SETTLED"))
    special = {1: ("ACH", Decimal("1250.00"), "Northwind Supplies Ltd", "Northwind"), 2: ("ACH", Decimal("1250.00"), "Northwind Supplies Ltd", "Northwind"), 3: ("WIRE", Decimal("900.00"), "Blue Oak Services Ltd", "Blue Oak"), 4: ("RTP", Decimal("410.50"), "Cedar Works Inc", "Cedar Works"), 5: ("FEDNOW", Decimal("75.25"), "Lumen Health Partners", "Lumen Health"), 6: ("ACH", Decimal("1800.00"), "Northwind Supplies Ltd", "Northwind"), 7: ("WIRE", Decimal("2200.00"), "Blue Oak Services Ltd", "Blue Oak"), 8: ("ACH", Decimal("1450.00"), "Northwind Supplies Ltd", "Northwind"), 9: ("WIRE", Decimal("2750.00"), "Blue Oak Services Ltd", "Blue Oak"), 10: ("RTP", Decimal("680.00"), "Cedar Works Inc", "Cedar Works")}
    for index, (rail, amount, registered, trading) in special.items():
        row = list(rows[index - 1]); row[1], row[2], row[4], row[5], row[8], row[9], row[10], row[11] = rail, amount, datetime(2026, 1, 2).date(), datetime(2026, 1, 2, 9, 0), registered, trading, "SETTLED", True; rows[index - 1] = tuple(row)
    recent_customer_scenarios = {
        4: datetime(2026, 7, 18, 9, 0),
        5: datetime(2026, 8, 21, 9, 0),
        6: datetime(2026, 9, 9, 9, 0),
    }
    for index, timestamp in recent_customer_scenarios.items():
        row = list(rows[index - 1]); row[4], row[5] = timestamp.date(), timestamp; rows[index - 1] = tuple(row)
    scenarios = {
        4997: ("ACH", Decimal("9000.00"), datetime(2026, 7, 25, 9, 0), "Northwind Supplies Ltd", "Northwind", "SETTLED", True),
        4998: ("WIRE", Decimal("12500.00"), datetime(2026, 8, 14, 9, 0), "Blue Oak Services Ltd", "Blue Oak", "SETTLED", True),
        4999: ("RTP", Decimal("3200.00"), datetime(2026, 9, 5, 9, 0), "Cedar Works Inc", "Cedar Works", "SETTLED", True),
        5000: ("FEDNOW", Decimal("780.00"), datetime(2026, 9, 12, 9, 0), "Lumen Health Partners", "Lumen Health", "PENDING", False),
        4501: ("ACH", Decimal("73000.00"), datetime(2026, 7, 20, 9, 0), "Northwind Supplies Ltd", "Northwind", "SETTLED", True),
        3777: ("ACH", Decimal("152788.25"), datetime(2026, 9, 24, 9, 0), "Cedar Works Inc", "Cedar Works", "SETTLED", True),
    }
    for index, (rail, amount, timestamp, registered, trading, status, funds_moved) in scenarios.items():
        row = list(rows[index - 1]); row[1], row[2], row[4], row[5], row[8], row[9], row[10], row[11] = rail, amount, timestamp.date(), timestamp, registered, trading, status, funds_moved; rows[index - 1] = tuple(row)
    return rows


def create_database(path: Path = DB_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(path))
    connection.execute("DROP TABLE IF EXISTS payments")
    connection.execute("CREATE TABLE payments (payment_id VARCHAR PRIMARY KEY, rail VARCHAR, amount DECIMAL(18, 2), currency VARCHAR, value_date DATE, settlement_timestamp TIMESTAMP, debtor_account VARCHAR, creditor_account VARCHAR, creditor_registered_name VARCHAR, creditor_trading_name VARCHAR, status VARCHAR, funds_moved BOOLEAN)")
    connection.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", build_rows())
    connection.execute("CREATE INDEX payments_date_idx ON payments(value_date)")
    connection.execute("CREATE INDEX payments_rail_idx ON payments(rail)")
    connection.executemany("INSERT OR REPLACE INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", USER_TEST_PAYMENTS)
    connection.close()
    return path


if __name__ == "__main__": print(f"Created {create_database()}")
