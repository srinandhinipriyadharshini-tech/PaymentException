# AI Voice, Distress Signals, and Analyst Priority Guide

## Purpose

This guide describes how to extend the Clearline Payment Exceptions demo with:

1. Speech-to-text transcription for recorded customer messages.
2. A structured customer distress signal analysis.
3. Analyst priority assignment in the Payment Exception Analyst workspace.
4. Human review and deterministic policy safeguards.

The current repository is offline-first. Its voice flow uses deterministic demo scenarios and its `platform/llm_client.py` is an intentionally unconfigured seam. This guide explains how to connect an approved hosted AI provider without putting a secret in source control or allowing an AI model to make the final payment decision.

## Important Safety Boundary

The model should identify a **customer distress signal**, not diagnose a person or infer a medical condition.

Do not use the model to decide whether a customer is truthful, fraudulent, vulnerable, or entitled to recovery. The signal is only one input for queue ordering and support handling. Deterministic payment rules, deadlines, rail rules, guardrails, and a human analyst remain authoritative.

Recommended display language:

- `Distress signal: High`
- `Distress score: 86/100`
- `Analyst priority: P1`
- `Reason: Customer reports urgent financial impact and repeated failed recovery attempts.`

Avoid labels such as `emotion detected`, `mental health risk`, or `customer is unstable`.

## Current Repository Flow

The current voice flow is in `app.py`:

```text
st.audio_input()
    -> deterministic demo scenario
    -> transcript preview
    -> transcript confirmation
    -> core.workflow.process_claim()
    -> customer case history
```

The target flow is:

```text
st.audio_input()
    -> speech-to-text provider
    -> transcript preview and customer confirmation
    -> distress signal analysis
    -> deterministic priority calculation
    -> core.workflow.process_claim()
    -> case history and analyst queue
```

Relevant files:

| File | Responsibility |
| --- | --- |
| `app.py` | Customer voice capture, transcript confirmation, and customer display |
| `admin_dashboard.py` | Payment Exception Analyst queue and case review |
| `core/models.py` | Pydantic case and payment data models |
| `core/workflow.py` | Deterministic payment matching and policy workflow |
| `ai/` | AI layer boundaries |
| `platform/llm_client.py` | Placeholder seam for a hosted LLM |
| `platform/config.yaml` | Runtime model and threshold configuration |
| `tests/` | Regression and behavior tests |

## 1. Configure the API Key Securely

Never paste an API key into Python, YAML, Markdown, Streamlit code, or a git commit.

For a temporary PowerShell session:

```powershell
$env:AI_API_KEY = "paste-the-approved-key-here"
```

For a persistent Windows user environment, set it outside the repository using your organization-approved secret manager or environment configuration. Restart the terminal after changing persistent variables.

Verify that the variable exists without printing the secret:

```powershell
if ($env:AI_API_KEY) { "AI_API_KEY is configured" } else { "AI_API_KEY is missing" }
```

Add local secret files to `.gitignore` if the project later introduces one. Do not print request headers, tokens, raw audio, or customer transcripts in logs.

## 2. Add Provider Dependencies

Use the official SDK for the selected provider when one is approved by the lab. Install it inside the project environment, for example:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install <approved-provider-sdk>
```

Record the dependency in `requirements.txt` so another lab machine can reproduce the setup. Do not add a provider-specific package until the lab confirms which provider and model are approved.

## 3. Create a Voice Service Boundary

Create `ai/voice.py`. Keep provider-specific code in this file so the Streamlit pages and deterministic workflow do not depend directly on a vendor SDK.

A provider-neutral contract should look like this:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class DistressResult:
    level: str
    score: int
    priority: str
    reason: str


def transcribe_audio(audio_bytes: bytes, filename: str, content_type: str) -> TranscriptResult:
    """Send audio to the approved speech-to-text provider."""
    # Provider-specific SDK call goes here.
    # Read the API key from os.environ, never from source code.
    raise NotImplementedError


def analyze_distress(transcript: str) -> DistressResult:
    """Return a bounded support signal, not a diagnosis."""
    # Provider-specific structured analysis call goes here.
    raise NotImplementedError
```

Keep the service return values small and typed. Do not pass an unvalidated provider response directly into the case model.

## 4. Speech-to-Text Request

The speech request should include:

- The recorded audio bytes.
- The correct MIME type from Streamlit's uploaded audio object.
- A language hint if the customer language is known.
- A request for plain transcript text or a small structured response.

Validate the response before displaying it:

```python
transcript = response.text.strip()
if not transcript:
    raise ValueError("The speech provider returned an empty transcript.")

if len(transcript) > 20_000:
    transcript = transcript[:20_000]
```

Recommended user flow:

1. Customer records a message.
2. The application sends the audio to the provider.
3. The transcript appears in a preview panel.
4. The customer or operator confirms the transcript.
5. Only the confirmed transcript enters `process_claim()`.

The confirmation step must remain. Speech recognition can mishear amounts, dates, names, and negations such as `I did not authorize this`.

## 5. Distress Signal Prompt

Use structured output and keep the prompt narrow:

```text
Analyze this payment-exception transcript for customer support urgency.

Return JSON only:
{
  "distress_level": "low|medium|high",
  "distress_score": 0,
  "urgency_reason": "brief factual explanation",
  "recommended_priority": "P1|P2|P3"
}

Rules:
- Assess only language indicating urgency or support distress.
- Do not diagnose a medical or mental-health condition.
- Do not decide whether the claim is truthful or fraudulent.
- Do not decide whether payment recovery is permitted.
- Do not invent facts that are absent from the transcript.
- Score from 0 to 100.
- Use P1 only for clear urgent impact, high distress, or immediate support risk.
- Keep the explanation under 240 characters.

Transcript:
{transcript}
```

Validate the response strictly:

```python
ALLOWED_LEVELS = {"low", "medium", "high"}
ALLOWED_PRIORITIES = {"P1", "P2", "P3"}


def validate_distress(payload: dict) -> DistressResult:
    level = payload.get("distress_level")
    priority = payload.get("recommended_priority")
    score = int(payload.get("distress_score", 0))
    reason = str(payload.get("urgency_reason", "")).strip()

    if level not in ALLOWED_LEVELS:
        raise ValueError("Invalid distress level")
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError("Invalid analyst priority")
    if not 0 <= score <= 100:
        raise ValueError("Distress score must be between 0 and 100")
    if len(reason) > 240:
        reason = reason[:240]

    return DistressResult(level, score, priority, reason)
```

If the provider fails, times out, returns invalid JSON, or exceeds a budget, the case must continue with:

```text
distress_level = unknown
distress_score = null
analyst_priority = the deterministic default
```

The application should show `AI distress analysis unavailable` rather than inventing a result.

## 6. Add Case Fields

Add these fields to `CaseResult` in `core/models.py`:

```python
distress_level: str | None = None
distress_score: int | None = Field(default=None, ge=0, le=100)
analyst_priority: str = "P3"
urgency_reason: str | None = None
```

Because the model currently uses `extra="forbid"`, these fields must be added before saving or loading enriched cases. Existing saved cases remain compatible because all new fields have defaults.

If you need to preserve the source of the signal, add:

```python
distress_source: str = "not_available"
```

Possible values are `voice_llm`, `text_llm`, `operator`, and `not_available`.

## 7. Calculate Priority Deterministically

Do not blindly trust the model's recommended priority. Apply a local policy after the model response:

```python
def calculate_priority(case_status: str, distress_score: int | None, deadline_days: int | None) -> str:
    score = distress_score or 0

    # Payment policy and immediate escalation remain authoritative.
    if case_status in {"ESCALATED", "NO_REMEDY"}:
        return "P1"
    if deadline_days is not None and deadline_days <= 2:
        return "P1"
    if score >= 80:
        return "P1"
    if score >= 50:
        return "P2"
    return "P3"
```

Suggested meanings:

| Priority | Meaning | Analyst handling |
| --- | --- | --- |
| `P1` | Immediate human attention | Review first; preserve evidence and check deadline |
| `P2` | Normal analyst attention | Review during the active queue cycle |
| `P3` | Standard processing | Process in normal order |

Sort the analyst queue by priority first and age second:

```python
priority_order = {"P1": 0, "P2": 1, "P3": 2}
visible = sorted(
    cases,
    key=lambda item: (priority_order.get(item.get("Priority", "P3"), 3), -item.get("Age", 0)),
)
```

## 8. Integrate with `app.py`

Replace the deterministic voice scenario selection in the voice section of `app.py` with the following logical sequence:

```python
if audio:
    audio_bytes = audio.getvalue()
    audio_type = getattr(audio, "type", "audio/wav")

    with st.spinner("Transcribing customer message..."):
        transcript_result = transcribe_audio(
            audio_bytes,
            filename="customer-voice.webm",
            content_type=audio_type,
        )

    st.session_state.voice_transcripts[active_user] = transcript_result.text
    st.session_state.drafts[active_user] = transcript_result.text
    st.rerun()
```

Then, after transcript confirmation:

```python
if st.session_state.transcript_confirmed[active_user]:
    with st.spinner("Analyzing support urgency..."):
        distress = analyze_distress(transcript)

    priority = calculate_priority(
        case_status="RECEIVED",
        distress_score=distress.score,
        deadline_days=None,
    )
```

Pass the confirmed transcript into the existing workflow. Do not change matching, category classification, remedy, rail rules, or deadline behavior.

## 9. Display the Signal on 8501

After transcript analysis, show a neutral customer-safe message:

```text
Your message has been transcribed and marked for analyst review.
```

Do not expose a distress score to the customer unless the product owner explicitly wants that. The score is primarily an internal support-routing signal.

## 10. Display the Signal on 8502

Add these fields to the analyst case rows:

```text
Priority: P1
Distress signal: High · 86/100
Reason: Customer reports urgent financial impact and repeated failed recovery attempts.
```

Use clear colors:

- P1: coral/red accent
- P2: amber accent
- P3: teal/neutral accent
- Unknown: gray accent

The analyst must still be able to open the case and inspect the original confirmed transcript.

## 11. Testing Plan

Add unit tests before enabling the hosted provider in the live demo.

### Validation tests

- Empty transcript is rejected.
- Transcript length is bounded.
- Invalid distress level is rejected.
- Scores below 0 or above 100 are rejected.
- Unknown provider output produces `not_available`, not a guessed score.
- API key is never included in logs or trace files.

### Priority tests

- Escalated case is always P1.
- Deadline within two days is P1.
- Score 80 is P1.
- Score 50 is P2.
- Score 49 is P3.
- Missing score follows deterministic default behavior.

### Workflow tests

- Confirmed transcript reaches `process_claim()`.
- Unconfirmed transcript cannot create a case.
- Existing deterministic payment matching remains unchanged.
- Existing human approval remains required before simulated submission.
- Existing RTP/FEDNOW and expired-deadline rules remain authoritative.

Run:

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" -m py_compile app.py admin_dashboard.py
& ".\.venv\Scripts\python.exe" verify.py
```

## 12. Demo Fallback

The application must still work without an API key. Keep the deterministic demo mode:

```text
AI_API_KEY missing
    -> show offline demo mode
    -> use the existing fixed transcript scenarios
    -> leave distress signal as unavailable
    -> calculate priority from deterministic case status and deadline only
```

This makes the demo reproducible in the AI Lab and prevents a provider outage from blocking the payment-exception workflow.

## 13. Suggested Implementation Order

1. Confirm the approved provider, model, retention policy, and audio formats.
2. Add the secret through the lab's environment or secret manager.
3. Add the provider SDK to the virtual environment and `requirements.txt`.
4. Create `ai/voice.py` with transcription and structured distress contracts.
5. Add strict response validation and offline fallback.
6. Add the four optional fields to `CaseResult`.
7. Connect confirmed transcripts in `app.py`.
8. Add deterministic priority calculation.
9. Add priority and distress signal display to `admin_dashboard.py`.
10. Add unit tests and run the full validation commands.
11. Test with synthetic recordings containing amounts, dates, beneficiaries, and explicit negation.
12. Demonstrate that a high distress signal changes queue order only, never payment-policy outcomes.

## Definition of Done

The feature is ready for the hackathon demo when:

- A recorded voice message becomes a visible, confirmable transcript.
- The confirmed transcript is used by the existing payment workflow.
- A structured distress signal is stored with the case.
- The analyst queue shows P1/P2/P3 priority and a short reason.
- Priority sorting is deterministic and tested.
- No API key, raw audio, or unnecessary transcript is written to logs.
- The app still runs in offline demo mode without a key.
- Human approval and existing payment policy guards remain in control.
