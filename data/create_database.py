from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).with_name("payment_exceptions.duckdb")
SEED = 20260919
RAILS = ("ACH", "WIRE", "RTP", "FEDNOW")


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
    connection.close()
    return path


if __name__ == "__main__": print(f"Created {create_database()}")
