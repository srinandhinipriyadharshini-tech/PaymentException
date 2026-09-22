from __future__ import annotations

from pathlib import Path

REQUIRED = (
    "ai/intake.py",
    "ai/matching.py",
    "ai/classification.py",
    "ai/drafting.py",
    "app_platform/ai_contract.py",
    "app_platform/guardrails.py",
    "app_platform/tracer.py",
    "api.py",
    "run.py",
    "Makefile",
)


def main() -> int:
    root = Path(__file__).resolve().parent
    missing = [path for path in REQUIRED if not (root / path).exists()]
    if missing:
        print("Missing required files:")
        print("\n".join(missing))
        return 1
    print(f"verify passed: {len(REQUIRED)} required files present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
