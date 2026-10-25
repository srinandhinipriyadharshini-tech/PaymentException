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

## Deploy both Streamlit pages to Community Cloud

Deploy the repository as one Streamlit Community Cloud app so the customer portal and analyst console can read and update the same case-history files:

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from this repository and select the branch you want to deploy.
3. Set **Main file path** to `streamlit_app.py` and the **App URL** as desired, then deploy.
4. Use the **Switch workspace** dropdown in the page header to switch between **Customer Portal** and **Analyst Console**.

The deployment uses the dependencies in `requirements.txt` and the checked-in synthetic DuckDB fixture. No secrets or external service credentials are required. This is a public, synthetic-data demo: it has no authentication, and Community Cloud's local filesystem is not durable storage. Do not enter real customer or payment data; case history and analyst decisions may be lost when the app restarts or is redeployed. This single deployment is required for the two pages to share local case history.

## UC-02 layer entry points

The repository now exposes the UC-02-style boundaries in `ai/`: `IntakeAI`, `MatchingAI`, `ClassificationAI`, and `DraftingAI`. Their results use the structured envelope in `app_platform/ai_contract.py`; the implementation remains deterministic and offline.

```powershell
& ".\.venv\Scripts\python.exe" run.py case "I did not make the ACH payment of £1250 on 2026-01-02 to Northwind."
& ".\.venv\Scripts\python.exe" -m eval.score
```

The `Makefile` provides `test`, `verify`, `score`, and `demo` targets for environments that provide `make`. `run.py` also writes a self-contained HTML trace under `traces/` and reports guardrail violations.

## React operations console

The judge-facing Admin & Operations Dashboard lives in `frontend/` as a standalone Vite + React + Tailwind + Recharts app.

```powershell
Set-Location frontend
npm install
npm run dev
```

It includes the deterministic 60-day SLA sandbox, case queue, cognitive routing trace, agentic audit verdict, and classification/triage analytics.

The complete seven-slide presentation script, visual guidance, speaker notes, demo narrative, and UC-02 guidelines are in [UC02_PITCH_DECK_SCRIPT.md](UC02_PITCH_DECK_SCRIPT.md).

The generated PowerPoint deck is [UC02_Core_Payment_Exceptions_Pitch.pptx](UC02_Core_Payment_Exceptions_Pitch.pptx). The editable generator is [tools/create_pitch_deck.py](tools/create_pitch_deck.py).

The regenerated demo data includes July, August, and September scenarios across ACH, WIRE, RTP, and FEDNOW, including expired settled payments and a pending in-progress FEDNOW payment.

Customer voice transcription starts automatically when a recording is complete, using local `faster-whisper` with the `base` model by default. The customer can edit the transcript and click **Process claim**, or choose **Record again**. Install project requirements before launch; the Whisper model downloads to the local cache on first transcription. Recordings are processed on the app machine and are not sent to an external transcription service. Optionally set `WHISPER_MODEL_SIZE` to `tiny`, `base`, `small`, `medium`, or `large-v3` before launching to change the local model size. The offline demo transcript remains available if model setup is unavailable.

The customer conversation also includes **Listen to latest reply**. It uses the browser's built-in speech synthesis, so customers can play or stop the agent's latest text response without installing a text-to-speech service. Playback requires a browser with speech-synthesis support and starts only when the customer presses the button; the reply text is not sent to a separate speech service.

Conversation messages are saved with their case. After a browser refresh, no case is selected and the conversation stays hidden until the customer clicks that case number in **Case History**. Unfinished intake drafts clear on refresh.

For the complete AI Lab demo, run `start_demo.ps1` from the repository root. It starts the customer portal on 8501, the Payment Exception Analyst console on 8502, and the live case API on 8503. Verify with `http://localhost:8501`, `http://localhost:8502`, `http://localhost:8503/health`, and `http://localhost:8503/api/cases`. The optional React console runs separately from `frontend` with `npm.cmd run dev -- --host 127.0.0.1`.

## Troubleshooting

If `py -3.14` is unavailable, install Python 3.14 or use the full Python executable path. If DuckDB reports a locked database, stop Streamlit and rerun the generator. If imports fail, run commands from this project root. Regenerating the database is safe and deterministic.

https://paymentexceptionuser.streamlit.app/

https://paymentexceptionexceptionanalyst.streamlit.app/
