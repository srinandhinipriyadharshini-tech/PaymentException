from __future__ import annotations

import argparse
from pathlib import Path

from core.workflow import process_claim
from data.create_database import create_database
from app_platform.guardrails import validate_result
from app_platform.tracer import Trace

DB = Path(__file__).resolve().parent / "data" / "payment_exceptions.duckdb"


def main() -> int:
    parser = argparse.ArgumentParser(description="Payment exception demo runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    case_parser = subparsers.add_parser("case")
    case_parser.add_argument("claim")
    subparsers.add_parser("baseline")
    args = parser.parse_args()
    create_database(DB)
    trace = Trace()
    if args.command == "baseline":
        print("Baseline: deterministic demo adapter disabled")
        return 0
    result = process_claim(args.claim, DB)
    violations = validate_result(result)
    trace.record("claim", args.claim)
    trace.record("result", result.model_dump(mode="json"))
    trace.record("guardrails", violations or "PASS")
    path = trace.write()
    print(result.model_dump_json(indent=2))
    print(f"Trace: {path}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
