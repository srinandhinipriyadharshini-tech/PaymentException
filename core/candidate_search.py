from __future__ import annotations

from pathlib import Path

from core.models import ExtractedFacts, Payment
from core.payment_search import search_payments


def find_candidates(facts: ExtractedFacts, db_path: Path | None = None, limit: int = 20) -> list[Payment]:
    return search_payments(facts, db_path=db_path, limit=limit) if db_path else search_payments(facts, limit=limit)
