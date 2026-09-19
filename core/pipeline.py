from __future__ import annotations

from pathlib import Path

from core.models import CaseResult
from core.workflow import process_claim


def run_claim(claim_text: str, db_path: Path | None = None) -> CaseResult:
    return process_claim(claim_text, db_path=db_path)
