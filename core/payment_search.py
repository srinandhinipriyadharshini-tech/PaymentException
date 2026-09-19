from __future__ import annotations

from pathlib import Path
import duckdb
from core.models import ExtractedFacts, Payment

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "payment_exceptions.duckdb"


def search_payments(facts: ExtractedFacts, db_path: Path = DB_PATH, limit: int = 20) -> list[Payment]:
    clauses, parameters = [], []
    if facts.amount_min is not None: clauses.append("amount >= ?"); parameters.append(facts.amount_min)
    if facts.amount_max is not None: clauses.append("amount <= ?"); parameters.append(facts.amount_max)
    if facts.date_min is not None: clauses.append("value_date >= ?"); parameters.append(facts.date_min)
    if facts.date_max is not None: clauses.append("value_date <= ?"); parameters.append(facts.date_max)
    if facts.day_of_month is not None: clauses.append("EXTRACT(DAY FROM value_date) = ?"); parameters.append(facts.day_of_month)
    month_of_year = getattr(facts, "month_of_year", None)
    if month_of_year is not None: clauses.append("EXTRACT(MONTH FROM value_date) = ?"); parameters.append(month_of_year)
    if facts.rail: clauses.append("rail = ?"); parameters.append(facts.rail)
    if facts.beneficiary_description:
        clauses.append("(lower(creditor_registered_name) LIKE ? OR lower(creditor_trading_name) LIKE ?)")
        term = f"%{facts.beneficiary_description.lower()}%"; parameters.extend([term, term])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT payment_id, rail, amount, currency, value_date, settlement_timestamp, debtor_account, creditor_account, creditor_registered_name, creditor_trading_name, status, funds_moved FROM payments {where} ORDER BY value_date, payment_id LIMIT ?"
    parameters.append(min(max(limit, 1), 100))
    connection = duckdb.connect(str(db_path), read_only=True)
    result = connection.execute(query, parameters); rows, columns = result.fetchall(), [item[0] for item in result.description]
    connection.close()
    return [Payment.model_validate(dict(zip(columns, row))) for row in rows]


def get_payment(payment_id: str, db_path: Path = DB_PATH) -> Payment | None:
    connection = duckdb.connect(str(db_path), read_only=True)
    result = connection.execute("SELECT payment_id, rail, amount, currency, value_date, settlement_timestamp, debtor_account, creditor_account, creditor_registered_name, creditor_trading_name, status, funds_moved FROM payments WHERE payment_id = ?", [payment_id])
    row = result.fetchone()
    columns = [item[0] for item in result.description]
    connection.close()
    return Payment.model_validate(dict(zip(columns, row))) if row else None


def count_payments(db_path: Path = DB_PATH) -> int:
    connection = duckdb.connect(str(db_path), read_only=True); count = connection.execute("SELECT COUNT(*) FROM payments").fetchone()[0]; connection.close(); return int(count)
