# AI Voice, Distress Signals, and Analyst Priority Guide

## Purpose

This guide describes how to extend the Clearline Payment Exceptions demo with:

1. Speech-to-text transcription for recorded customer messages.
2. A structured customer distress signal analysis.
3. Analyst priority assignment in the Payment Exception Analyst workspace.
4. Human review and deterministic policy safeguards.

The customer voice flow uses local `faster-whisper` transcription on the app machine, plus a clearly labelled offline demo transcript. The model is downloaded to the local cache on first use. Transcription starts automatically when recording is complete; the customer can edit the transcript and submit it with **Process claim**, or choose **Record again**. Submitting the claim confirms the transcript. A local wording-based support-urgency heuristic is shown to the customer and stored with the case; it is not an acoustic stress detector, a diagnosis, or a payment-policy input. This guide retains the future integration guidance for approved structured distress analysis and analyst prioritisation.

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
    -> automatic local Whisper transcription or selected offline demo
    -> editable transcript preview
    -> wording-based support-urgency cue
    -> Process claim (submits/confirms transcript) or Record again
    -> core.workflow.process_claim()
    -> customer case history
```

Local transcription runs on the app machine using `faster-whisper` and the `base` model by default. The model weights are downloaded once to the local model cache on first use; recorded audio is not sent to a transcription provider. Set `WHISPER_MODEL_SIZE` to `tiny`, `base`, `small`, `medium`, or `large-v3` to choose a local model size. The offline demo remains available explicitly. The current urgency cue examines transcript wording only; do not describe it as an analysis of vocal tone or physiological stress.

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
| `app.py` | Customer voice capture, automatic transcription, and customer display |
| `admin_dashboard.py` | Payment Exception Analyst queue and case review |
| `core/models.py` | Pydantic case and payment data models |
| `core/workflow.py` | Deterministic payment matching and policy workflow |
| `ai/` | AI layer boundaries |
| `ai/voice.py` | Local Whisper transcription and local wording-based support-urgency cue |
| `platform/llm_client.py` | Placeholder seam for a future hosted LLM |
| `platform/config.yaml` | Runtime model and threshold configuration |
| `tests/` | Regression and behavior tests |

## 1. Install the Local Whisper Runtime

The current implementation does not need an API key. Install the declared runtime in the project virtual environment:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

The `base` model downloads to the local Hugging Face cache the first time a recording is transcribed. This initial model download requires internet access; transcription itself runs locally. Use `WHISPER_MODEL_SIZE=tiny|base|small|medium|large-v3` to select a different installed/downloadable model size before starting Streamlit. Close existing Streamlit processes and restart after changing dependencies or environment settings.

Do not print raw audio or customer transcripts in logs. The model download is public model data; recorded customer audio is not uploaded to a transcription provider.

## 2. Voice Service Boundary

`ai/voice.py` owns local transcription and the bounded wording-based urgency cue. Keep the Streamlit page and deterministic payment workflow independent of the transcription runtime.

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


def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    """Transcribe audio locally with faster-whisper."""
    raise NotImplementedError


def analyze_distress(transcript: str) -> DistressResult:
    """Return a bounded support signal, not a diagnosis."""
    # Provider-specific structured analysis call goes here.
    raise NotImplementedError
```

Keep service return values small and typed. Never use this signal to determine whether a payment is eligible for recovery.

## 3. Speech-to-Text and Confirmation

The local transcriber receives:

- Recorded audio bytes.
- The recording's media type from Streamlit.
- A local Whisper model selected by `WHISPER_MODEL_SIZE`.

The implementation rejects empty recordings/transcripts and limits transcript text to 20,000 characters.

Recommended user flow:

1. Customer records a message.
2. The application transcribes the audio locally with Whisper.
3. The transcript appears in an editable preview panel.
4. The customer clicks **Process claim** to submit the transcript, or **Record again** to replace it.
5. Only the submitted transcript enters `process_claim()`.

The customer can review or edit the transcript before submission because speech recognition can mishear amounts, dates, names, and negations such as `I did not authorize this`.

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

## 8. Current `app.py` Integration

The customer page now uses this sequence:

1. Customer records audio; local Whisper transcription starts automatically when the recording is complete.
2. The app displays an editable transcript preview and a wording-based support cue.
3. The customer clicks **Process claim** to submit the transcript, or **Record again** to replace the recording.
4. Only the submitted transcript is passed into `process_claim()`.
5. The cue is stored with the case but does not change matching, category classification, remedy, rail rules, or deadline behavior.

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

The analyst must still be able to open the case and inspect the original submitted transcript.

## 11. Testing Plan

Unit tests cover the local service boundary and urgency classification.

### Validation tests

- Empty transcript is rejected.
- Transcript length is bounded.
- Invalid distress level is rejected.
- Scores below 0 or above 100 are rejected.
- Empty and unsupported audio input is rejected.
- Empty transcription output is not accepted as a successful transcript.
- The local model receives the audio without any hosted transcription request.

### Priority tests

- Escalated case is always P1.
- Deadline within two days is P1.
- Score 80 is P1.
- Score 50 is P2.
- Score 49 is P3.
- Missing score follows deterministic default behavior.

### Workflow tests

- Submitted transcript reaches `process_claim()`.
- The customer can edit or replace a transcript before submitting it.
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

The application remains usable if the local model cannot be downloaded or loaded. Keep the explicitly selected deterministic demo mode:

```text
Local Whisper unavailable
    -> show the transcription error
    -> allow user to choose an offline demo transcript
    -> do not claim that the demo transcript came from the audio
```

This makes the demo reproducible and prevents model-download issues from blocking the payment-exception workflow.

## 13. Suggested Implementation Order

1. Install the `faster-whisper` dependency from `requirements.txt`.
2. Select a local model size that fits the machine and download it to the local model cache.
3. Keep `ai/voice.py` as the local transcription and support-urgency boundary.
4. Consider acoustic/support analysis only with an approved, privacy-reviewed design; current analysis uses transcript wording only.
5. Add priority display to `admin_dashboard.py` if analyst prioritization is required.
6. Add unit tests and run the validation commands.
7. Test with synthetic recordings containing amounts, dates, beneficiaries, and explicit negation.
8. Demonstrate that urgency cues can affect support routing only, never payment-policy outcomes.

## Definition of Done

The feature is ready for the hackathon demo when:

- A completed recording is automatically transcribed into a visible, editable transcript.
- The submitted transcript is used by the existing payment workflow.
- A bounded wording-based support urgency cue is stored with a confirmed voice case.
- The cue is clearly presented as non-diagnostic and does not change payment-policy outcomes.
- The analyst queue priority extension remains future work unless separately implemented.
- No raw audio is sent to an external transcription service or written to logs.
- The app still runs in offline demo mode if the local model is unavailable.
- Human approval and existing payment policy guards remain in control.
