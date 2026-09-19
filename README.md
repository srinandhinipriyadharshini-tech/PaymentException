# payment-exceptions

A standalone, offline synthetic payment-exception demo for QA practice. It uses Python 3.14, Streamlit, DuckDB, Pydantic, pytest, and deterministic standard-library parsing. It never connects to a bank or paid AI service. All policies are synthetic demo rules.

## Windows PowerShell

```powershell
py -3.14 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" data\create_database.py
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
```

Expected test output ends with the current test count. Streamlit prints a local URL such as `http://localhost:8501`.

## UC-02 layer entry points

The repository now exposes the UC-02-style boundaries in `ai/`: `IntakeAI`, `MatchingAI`, `ClassificationAI`, and `DraftingAI`. Their results use the structured envelope in `platform/ai_contract.py`; the implementation remains deterministic and offline.

```powershell
& ".\.venv\Scripts\python.exe" run.py case "I did not make the ACH payment of £1250 on 2026-01-02 to Northwind."
& ".\.venv\Scripts\python.exe" -m eval.score
```

The `Makefile` provides `test`, `verify`, `score`, and `demo` targets for environments that provide `make`. `run.py` also writes a self-contained HTML trace under `traces/` and reports guardrail violations.

The regenerated demo data includes July, August, and September scenarios across ACH, WIRE, RTP, and FEDNOW, including expired settled payments and a pending in-progress FEDNOW payment.

## Troubleshooting

If `py -3.14` is unavailable, install Python 3.14 or use the full Python executable path. If DuckDB reports a locked database, stop Streamlit and rerun the generator. If imports fail, run commands from this project root. Regenerating the database is safe and deterministic.
