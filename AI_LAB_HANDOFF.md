# Clearline Payment Exceptions: AI Lab Handoff

## 1. Purpose

This repository is a standalone, offline synthetic implementation of the UC-02 Core Payment Exceptions and Dispute Chatbot Portal.

The demo combines:

- Deterministic payment search and policy rules
- AI-layer boundaries for intake, matching, classification, and drafting
- Human-in-the-loop approval before a simulated inter-bank request
- Customer chat and voice-intake flows
- An operations console for escalation, audit, email notification, and analytics
- A React voice-agent experience for the judge-facing demo

No real bank, payment network, SMTP provider, or paid AI service is contacted by default.

## 2. Repository map

| Area | Purpose |
| --- | --- |
| `app.py` | Customer-facing Streamlit portal on port 8501 |
| `admin_dashboard.py` | Admin and Operations Streamlit console on port 8502 |
| `frontend/` | React + Tailwind + Recharts voice-enabled operations console |
| `ai/` | Intake, matching, classification, and drafting AI boundaries |
| `core/` | Payment models, search, workflow, deadlines, rail rules, redaction |
| `app_platform/` | AI contract, guardrails, and trace utilities |
| `data/create_database.py` | Reproducible 6,000-record DuckDB fixture |
| `tests/` | Automated Python tests |
| `traces/` | Saved synthetic case history and generated HTML traces |

## 3. Prerequisites

### Python

- Windows 10 or 11
- Python 3.14 recommended
- PowerShell
- Git

### Frontend

- Node.js 20 or newer
- npm 10 or newer
- A browser with microphone permission if testing voice capture

### Optional

- `make` for the Makefile shortcuts
- A modern Chromium-based browser for the best Streamlit audio-input experience

## 4. Fresh setup in AI Lab

Run these commands from PowerShell after cloning the repository:

```powershell
git clone <repository-url>
Set-Location Payment_Exceptions

py -3.14 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" data\create_database.py
```

Verify the Python environment:

```powershell
& ".\.venv\Scripts\python.exe" --version
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" verify.py
& ".\.venv\Scripts\python.exe" -m compileall -q ai app_platform core eval run.py
```

Install and build the React console:

```powershell
Set-Location frontend
npm install
npm run build
Set-Location ..
```

If PowerShell reports that `npm.ps1` is blocked by execution policy, use the Windows command shim:

```powershell
& "C:\Program Files\nodejs\npm.cmd" install
& "C:\Program Files\nodejs\npm.cmd" run build
```

If `npm` is not recognized after installing Node.js, close and reopen VS Code so the new PATH is loaded. The standard installation path is usually `C:\Program Files\nodejs`.

## 5. Run the applications

For a live demo, run the included setup-and-launch script from the repository root. It creates `.venv` when needed, installs `requirements.txt`, creates the synthetic DuckDB fixture, starts both Streamlit portals plus the read-only live case API, waits for ports 8501, 8502, and 8503, and opens both portal URLs:

```powershell
Set-Location Payment_Exceptions
& powershell.exe -ExecutionPolicy Bypass -File .\start_demo.ps1
```

After the first successful setup, use the faster repeat-launch command:

```powershell
& powershell.exe -ExecutionPolicy Bypass -File .\start_demo.ps1 -SkipInstall
```

The script preserves any service already using ports 8501, 8502, or 8503. The React operations console can fetch live cases from `http://localhost:8503/api/cases`; Vite proxies `/api` to that service during development and preview. Clarification-only customer cases are intentionally excluded from the analyst/API queue until a payment is matched. Keep the service windows open during the hackathon; closing them stops the local servers.

If Python is missing, install Python 3.14 for Windows, reopen PowerShell, and run the setup command again. If the browser does not open automatically, use `http://localhost:8501` for the customer portal, `http://localhost:8502` for the Payment Exception Analyst console, and `http://localhost:8503/api/cases` to verify the live case feed.

Check service health before the demo:

```powershell
Invoke-WebRequest http://localhost:8501
Invoke-WebRequest http://localhost:8502
Invoke-WebRequest http://localhost:8503/health
Invoke-WebRequest http://localhost:8503/api/cases
```

The launch script starts the two Streamlit workspaces and the case API. Start the optional React console separately from `frontend`:

```powershell
Set-Location Payment_Exceptions\frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open the Vite URL printed in the terminal, normally `http://127.0.0.1:5173`.

Use separate terminals for each server.

### Customer portal

```powershell
Set-Location Payment_Exceptions
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
```

Open: `http://localhost:8501`

The customer portal supports:

- Typed customer claim intake
- Browser audio recording
- Offline deterministic voice demo transcription scenarios
- Customer and chatbot conversation bubbles
- Clarification requests
- Payment matching and category classification
- Simulated request confirmation
- Customer email-notification handoff from the operations console

### Admin and Operations console

```powershell
Set-Location Payment_Exceptions
& ".\.venv\Scripts\python.exe" -m streamlit run admin_dashboard.py --server.port 8502
```

Open: `http://localhost:8502`

The console supports:

- Exception queue and deep-dive audit
- Operations workspace and Audit workspace
- SLA tester from 10 to 70 days
- Escalated, simulated-request, and no-remedy states
- AI cognitive routing trace
- Agentic Smart Audit Verdict
- Simulated customer email preview and trigger
- Classification and triage analytics

### React voice dashboard

```powershell
Set-Location Payment_Exceptions\frontend
npm run dev -- --host 127.0.0.1
```

Open the URL printed by Vite, normally `http://127.0.0.1:5173`.

## 6. Use-case test matrix

The business rule used by the demo is:

- ACH and WIRE can expose a simulated recovery remedy when inside the configured deadline.
- RTP and FEDNOW are final instant-payment rails in the synthetic rulebook and expose no recovery remedy.
- The default deadline is 30 days for erroneous payments and 60 days for unauthorised or authorised-but-scammed claims.
- An expired deadline blocks automatic submission and routes the case to manual review.
- An ambiguous candidate must produce clarification rather than silent selection.
- An agent recommendation never bypasses human approval or rail/deadline policy.

### Category and rail coverage

| ID | Scenario / input | Rail | Category | Expected result | Type |
| --- | --- | --- | --- | --- | --- |
| C01 | `I did not make the ACH payment of GBP 1250 on 2026-01-02 to Northwind.` | ACH | `UNAUTHORISED` | Payment match, investigation remedy, deadline is expired as of 2026-09-20, no automatic late request | Positive + expired |
| C02 | `I made a mistake with the ACH payment of GBP 1800 on September 9 to Northwind.` | ACH | `ERRONEOUS` | Matches `PMT-SYN-000006`, return-of-funds remedy, deadline 2026-10-09 | Positive |
| C03 | `The WIRE payment of GBP 12500 on 2026-08-14 to Blue Oak was authorised by me, but I was scammed.` | WIRE | `AUTHORISED_BUT_SCAMMED` | Matches `PMT-SYN-004998`, scam investigation remedy, deadline 2026-10-13 | Positive |
| C04 | `The RTP payment of GBP 3200 on 2026-09-05 to Cedar was a scam.` | RTP | `AUTHORISED_BUT_SCAMMED` | Category may be scam, but rail rule changes remedy to `NO_REMEDY`; no request | Rail-finality negative |
| C05 | `The FEDNOW payment of GBP 780 on 2026-09-12 to Lumen is wrong.` | FEDNOW | `ERRONEOUS` | Payment is pending, but final instant-rail policy exposes no remedy | Pending + rail-finality |
| C06 | `I do not recognise the ACH payment of GBP 1250.` | ACH | Not selected | Two candidates remain; ask customer which payment they mean | Ambiguity edge case |
| C07 | `Someone took about GBP 73000 from my account on the 20th. It says Northwind.` | ACH | `UNAUTHORISED` | Approximate amount accepted; matches `PMT-SYN-004501`; expired deadline requires manual handling | Approximate + expired |
| C08 | `Someone took about GBP 412 on the 4th. It says Northgate.` | ACH | Not selected | No candidate; ask for correct date, amount, or beneficiary | No-match negative |
| C09 | `The payment is a problem.` | Unknown | Not classified | Intake abstains because there are no searchable facts | Missing-data edge case |
| C10 | `The ACH payment of GBP 1250 on 2026-01-02 to Northwind was a wrong payment.` | ACH | `ERRONEOUS` | Erroneous classification; deadline is expired for the current demo date | Category positive + expired |
| C11 | `The ACH payment of GBP 1250 on 2026-01-02 to Northwind was a scam payment.` | ACH | `AUTHORISED_BUT_SCAMMED` | Authorised-scam classification; deadline is expired for the current demo date | Category positive + expired |
| C12 | `I sent GBP 152788.25 for Cedar on the 24th and did not authorise it.` | ACH | `UNAUTHORISED` | Matches `PMT-SYN-003777`, exact beneficiary/date/amount evidence | Exact-match positive |

### Rail matrix

| Rail | Normal outcome | Expected recovery behavior |
| --- | --- | --- |
| ACH | Recoverable if deadline is open | Simulated request may be drafted and approved |
| WIRE | Recoverable if deadline is open | Simulated request may be drafted and approved |
| RTP | Final instant rail | `NO_REMEDY`, no inter-bank request |
| FEDNOW | Final instant rail | `NO_REMEDY`, no inter-bank request; pending status is still shown |

The machine-readable version of this matrix is [data/uc02_test_scenarios.csv](data/uc02_test_scenarios.csv). It includes `debtor_account` and `creditor_account` for every matched payment, including both account possibilities for the ambiguous C06 case. Use the account values to validate customer ownership and beneficiary matching; do not invent account numbers in new test cases.

### Six-user uploaded payment data

The workbook rows are seeded into `data/payment_exceptions.duckdb` by `data/create_database.py`. The expected behavior matrix is [data/six_user_payment_expectations.csv](data/six_user_payment_expectations.csv), and claim examples are in [data/six_user_test_claims.csv](data/six_user_test_claims.csv).

The current-date positive request scenarios are:

| Payment | Rail/status | Expected result |
| --- | --- | --- |
| `PMT-SYN-001001` | ACH / SETTLED | ACH return request can be drafted before the five-day deadline |
| `PMT-SYN-001003` | WIRE / SETTLED | WIRE recall request can be drafted before the one-day deadline |
| `PMT-SYN-001002` | RTP / PENDING | RTP return request can be drafted because funds have not moved |
| `PMT-SYN-001011` | WIRE / PENDING | WIRE recall request can be drafted because funds have not moved |

Each still requires customer confirmation and Payment Exception Analyst approval. `FAILED`, `CANCELLED`, `REJECTED`, and `RETURNED` payments do not start automatic recovery requests. Clarification-only cases without a selected payment remain in the customer workspace and are excluded from the analyst queue/API.

## 7. Voice demo scenarios

### Streamlit 8501

1. Open `http://localhost:8501`.
2. Record a customer message with the microphone control.
3. Stop the recording and confirm the audio player is visible.
4. Select a demo transcription scenario explicitly.
5. Review the transcription preview.
6. Click `Transcribe & process voice`.
7. Confirm the captured customer transcript and chatbot response appear in the conversation.

The Streamlit version is offline and deterministic. It does not infer arbitrary speech from the audio bytes. A real speech-to-text provider must be connected for production transcription.

### React voice console

The React voice panel includes:

- Idle microphone state
- Listening waveform and timer
- Processing state
- Transcript success state
- Automated candidate-search message
- `onTranscriptionComplete` callback

React scenarios:

| Scenario | Transcript | Expected UI result |
| --- | --- | --- |
| A | `I sent around eight thousand to the plumber last Tuesday.` | Filters to John Doe Plumbing LLC, USD 7,950, safe SLA state |
| B | `I had a wrong charge of five hundred dollars back in June.` | Moves the SLA tester past 60 days and activates no-remedy state |
| C | `No, that's not the right account, none of those are mine!` | Selects the case and moves it to escalated manual review |

## 8. Validation checklist

Before the AI Lab demo:

- [ ] `pytest -q` passes.
- [ ] `verify.py` passes.
- [ ] Python compileall passes.
- [ ] `npm run build` passes.
- [ ] Port 8501 customer portal loads.
- [ ] Port 8502 operations console loads.
- [ ] React Vite page loads if the React demo is being shown.
- [ ] Browser microphone permission is enabled.
- [ ] Scenario A produces a customer transcript and chatbot response.
- [ ] Scenario B displays expired/no-remedy behavior.
- [ ] Scenario C displays manual escalation.
- [ ] An admin can open the audit ledger.
- [ ] The email action is clearly marked simulated and does not claim external delivery.
- [ ] No output exposes synthetic account or payment identifiers where redaction is required.

Useful commands:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" verify.py
& ".\.venv\Scripts\python.exe" -m eval.score
& ".\.venv\Scripts\python.exe" run.py case "The WIRE payment of GBP 12500 on 2026-08-14 to Blue Oak was authorised by me, but I was scammed."
Import-Csv data\uc02_test_scenarios.csv | Format-Table scenario_id, payment_id, debtor_account, creditor_account, expected_category, expected_status
```

## 9. Technical demo story

Use this sequence for a judge or stakeholder demo:

1. Start in the customer portal and submit a natural-language dispute.
2. Show deterministic intake: amount, date, beneficiary, rail, and reason are extracted without inventing facts.
3. Demonstrate candidate matching and explain why ambiguity triggers clarification instead of silent selection.
4. Use the voice control to show audio capture, transcription, and chatbot follow-up.
5. Open the operations console through the portal link.
6. Select the case in the queue and show the AI cognitive routing trace, match confidence, and evidence.
7. Open the Agentic Smart Audit Verdict and explain that it prepares context but does not replace human approval.
8. Move the SLA slider from a safe day to day 47 and then past day 60.
9. Show the state transition: simulated request, escalated review, or no-remedy.
10. Approve an in-window ACH/WIRE request and show the request ID plus the no-guaranteed-recovery disclaimer.
11. Trigger the simulated customer email and explain that production would connect this event to an approved notification provider.
12. Switch to Audit workspace and show the immutable-style decision ledger.

## 10. Use-case guidelines

### Always preserve

- Human approval before external submission
- Explicit no-guaranteed-recovery language
- Deadline and rail policy enforcement
- Customer clarification when matching is ambiguous
- Redaction of synthetic payment and account identifiers in generated messages
- A trace of facts, reasoning, policy checks, and operator action

### Do not claim in the demo

- Do not claim that an email was delivered; it is simulated.
- Do not claim that a bank or receiving institution was contacted.
- Do not claim that the voice demo is production speech recognition.
- Do not claim that an AI fraud score is a final fraud decision.
- Do not call an expired case automatically unrecoverable unless the policy explicitly says so; this demo distinguishes manual review from rail-level no-remedy.

### Recommended production enhancements

- Replace the deterministic voice scenario mapper with a secured speech-to-text service.
- Add customer notification preferences and consent records.
- Add an outbound notification worker with retries, idempotency keys, delivery status, and provider webhooks.
- Persist audit events in an append-only store.
- Add role-based access control for agent, supervisor, auditor, and administrator.
- Add a policy version to every decision so historical outcomes remain reproducible.
- Add contract tests between the AI layers and deterministic core workflow.

## 11. Commit and handoff workflow

Before committing:

```powershell
git status
git diff --check
& ".\.venv\Scripts\python.exe" -m pytest -q
Set-Location frontend
& "C:\Program Files\nodejs\npm.cmd" run build
Set-Location ..
```

Commit and push:

```powershell
git add AI_LAB_HANDOFF.md app.py admin_dashboard.py ai app_platform core data frontend Makefile verify.py README.md
git commit -m "Add UC-02 AI Lab demo handoff and multimodal workflows"
git push origin <branch-name>
```

AI Lab pull workflow:

```powershell
git pull origin <branch-name>
py -3.14 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" data\create_database.py
Set-Location frontend
npm install
npm run build
```

This document is the operational handoff. Keep it updated when a policy rule, fixture, port, provider, or demo scenario changes.

8501 and 8502 are both working again and return 200 OK.

For the hackathon, use the new one-command launcher from the project root:



.\start_demo.ps1
It will:

Start the customer portal on http://localhost:8501
Start the admin console on http://localhost:8502
Open both browser pages
Detect if either port is already running
Keep existing services instead of starting duplicates
Keep the two PowerShell windows open during the demo. Closing them stops the local servers.

The launcher is:

start_demo.ps1

Its PowerShell syntax has been validated successfully.

## 12. Final pre-push and AI Lab recovery checklist

Run the following from the repository root before pushing:

```powershell
& ".\.venv\Scripts\python.exe" -m py_compile app.py admin_dashboard.py
& ".\.venv\Scripts\python.exe" -m compileall -q ai app_platform core eval run.py
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" verify.py
Set-Location frontend
& "C:\Program Files\nodejs\npm.cmd" run build
Set-Location ..
git diff --check
git status --short
```

Before running tests or rebuilding the DuckDB fixture, stop both Streamlit processes if they are running. DuckDB uses a file lock, so a live portal can prevent test setup or database regeneration.

```powershell
netstat -ano | Select-String ':8501|:8502'
Stop-Process -Id <customer-process-id>,<admin-process-id> -Force
& ".\.venv\Scripts\python.exe" data\create_database.py
```

The regenerated fixture must contain:

- 6,000 payments total.
- 1,000 payments for each of `ACCT-SYN-000001` through `ACCT-SYN-000006`.
- ACH, WIRE, RTP, and FEDNOW rails.
- Both `PENDING` and `SETTLED` statuses.

Restart the demo after validation:

```powershell
.\start_demo.ps1
```

Expected URLs:

- Customer portal: `http://localhost:8501/`
- Admin console: `http://localhost:8502/`

If the browser shows old customer results, use the customer sidebar **Clear history**, then submit the claim again. If the admin queue is empty after a new customer case, use **Refresh customer cases** in the admin sidebar. Admin approval is allowed only for escalated cases; agent-approved cases must remain visible without a second approval.

Expected conversation checks:

- Missing amount, beneficiary, or date produces a clarification request.
- Approximate amounts show the matched transaction details and require transaction confirmation before classification.
- `Yes, I confirm`, `confirm`, or `correct` selects the displayed transaction.
- Expired cases escalate and do not submit a request.
- Authorised-scam cases preserve their category, escalate, and do not promise recovery.
- RTP/FEDNOW cases with moved funds do not promise recovery.
- No-match and ambiguous cases do not create requests.

If a portal still serves old behavior after a code change, stop the old process, restart the relevant Streamlit command, and hard-refresh the browser with `Ctrl+F5`. Confirm with:

```powershell
Invoke-WebRequest http://localhost:8501/ -UseBasicParsing
Invoke-WebRequest http://localhost:8502/ -UseBasicParsing
```

Both responses should return status `200`.

### Interpreting legacy test failures

If pytest reports failures in the older workflow tests after pulling this version, check whether the assertion still expects the previous behavior:

- Approximate `1000` used to mean `750..1250`; the current rule is `500..1999`.
- Approximate claims now require transaction confirmation before classification, so `selected_payment` remains empty while clarification is pending.
- Claims missing amount, beneficiary, or date now clarify before searching/classifying.
- Authorised-scam claims preserve their category and escalate without a request.
- The configured rail deadlines are 60 days for ACH unauthorised, 5 days for ACH erroneous, and 1 day for WIRE/RTP/FEDNOW configured requests.

These failures indicate stale expectations in the local test file when the failure text mentions the old values or old automatic-selection behavior. Do not weaken the policy implementation to satisfy those old assertions; update the test expectation to the current rulebook and rerun `pytest -q`.

User Raises Exception
2
|
3
v
4
AI Categorization
5
|
6
v
7
Analyst Review
8
|
9
+----+----+
10
| |
11
Resolved Need More Info
12
| |
13
+----+----+
14
|
15
v
16
User Notification