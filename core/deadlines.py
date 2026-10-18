from __future__ import annotations

from datetime import date, timedelta

from core.models import Category, Payment
from core.rail_rules import calculate_remedy

FED_HOLIDAYS = {
    "2026-01-01",
    "2026-01-19",
    "2026-02-16",
    "2026-05-25",
    "2026-06-19",
    "2026-07-04",
    "2026-09-07",
    "2026-11-11",
    "2026-11-26",
    "2026-12-25",
}


def _add_banking_days(start: date, days: int, holidays: set[str] | None = None) -> date:
    holidays = holidays or FED_HOLIDAYS
    cursor = start
    remaining = days
    while remaining > 0:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5 and cursor.isoformat() not in holidays:
            remaining -= 1
    return cursor


def calculate_deadline(category: Category, payment: Payment, today: date | None = None, holidays: set[str] | None = None) -> date | None:
    remedy = calculate_remedy(category, payment)
    if remedy.deadline_days is None:
        return None
    if payment.rail == "ACH" and category is Category.ERRONEOUS:
        return _add_banking_days(payment.value_date, remedy.deadline_days, holidays)
    return payment.value_date + timedelta(days=remedy.deadline_days)


def is_expired(deadline: date | None, today: date | None = None) -> bool:
    today = today or date.today()
    return deadline is not None and today > deadline
