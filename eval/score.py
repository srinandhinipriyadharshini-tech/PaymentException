from __future__ import annotations

import argparse
from pathlib import Path

from core.models import CaseStatus
from core.workflow import process_claim
from data.create_database import create_database

DB = Path(__file__).resolve().parents[1] / "data" / "payment_exceptions.duckdb"
DEFAULT_CLAIMS = [
    "I did not make the ACH payment of £1250 on 2026-01-02 to Northwind.",
    "I do not recognise the ACH payment of £1250.",
    "someone took about $73000 from my account on the 20th, i never authorized it. it says Northwind",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Score the available synthetic claims")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    create_database(DB)
    for run in range(max(args.repeat, 1)):
        results = [process_claim(claim, DB) for claim in DEFAULT_CLAIMS]
        matched = sum(result.selected_payment is not None for result in results)
        abstained = sum(result.case_status is CaseStatus.CLARIFICATION_REQUIRED for result in results)
        print(f"run={run + 1} cases={len(results)} matched={matched} clarification_rate={abstained / len(results):.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
