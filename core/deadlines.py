from __future__ import annotations
from datetime import date, timedelta
from core.models import Category, Payment


def calculate_deadline(category: Category, payment: Payment, today: date | None = None) -> date | None:
    if category is Category.NO_REMEDY: return None
    return payment.value_date + timedelta(days=30 if category is Category.ERRONEOUS else 60)


def is_expired(deadline: date | None, today: date | None = None) -> bool:
    return deadline is not None and deadline < (today or date.today())
