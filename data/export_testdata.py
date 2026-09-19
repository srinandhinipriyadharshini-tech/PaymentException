from __future__ import annotations

import csv
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "payment_exceptions.duckdb"
OUTPUT = ROOT / "data" / "payment_exceptions_6000.csv"


def export() -> Path:
    connection = duckdb.connect(str(DATABASE), read_only=True)
    result = connection.execute("SELECT * FROM payments ORDER BY payment_id")
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([item[0] for item in result.description])
        writer.writerows(result.fetchall())
    connection.close()
    return OUTPUT


if __name__ == "__main__":
    print(f"Exported {export()}")