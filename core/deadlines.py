from __future__ import annotations
from datetime import date, timedelta
from core.models import Category, Payment
from core.rail_rules import calculate_remedy


def calculate_deadline(category: Category, payment: Payment, today: date | None = None) -> date | None:
    remedy = calculate_remedy(category, payment)
    if remedy.deadline_days is None: return None
    return payment.value_date + timedelta(days=remedy.deadline_days)


def is_expired(deadline: date | None, today: date | None = None) -> bool:
    return deadline is not None and deadline < (today or date.today())
