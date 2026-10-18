from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import os
import re


MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_TRANSCRIPT_CHARS = 20_000
DEFAULT_MODEL_SIZE = "base"
ALLOWED_MODEL_SIZES = {"tiny", "base", "small", "medium", "large-v3"}

HIGH_URGENCY_PHRASES = (
    "can't pay rent",
    "cannot pay rent",
    "eviction",
    "no food",
    "can't afford medication",
    "cannot afford medication",
    "life savings",
    "all my savings",
    "financial emergency",
    "need the money today",
)
MEDIUM_URGENCY_PHRASES = (
    "worried",
    "stressed",
    "anxious",
    "struggling",
    "desperate",
    "can't sleep",
    "cannot sleep",
    "overdraft",
    "overdue bills",
    "scared",
)


class VoiceServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SupportUrgency:
    level: str
    score: int
    reason: str


@lru_cache(maxsize=1)
def _load_local_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise VoiceServiceError(
            "Local Whisper is not installed. Install the project requirements and restart the app."
        ) from exc
    try:
        return WhisperModel(model_size, device="cpu", compute_type="int8")
    except (OSError, RuntimeError, ValueError) as exc:
        raise VoiceServiceError(
            f"Could not load the local Whisper '{model_size}' model. Check the model download/cache and try again."
        ) from exc


def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    if not audio_bytes:
        raise VoiceServiceError("The recording is empty. Record a message and try again.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise VoiceServiceError("The recording exceeds the 25 MB local transcription limit.")

    mime_type = content_type.split(";", 1)[0].strip().lower()
    if not mime_type.startswith("audio/"):
        raise VoiceServiceError("The recording format is not recognized as audio.")

    model_size = os.environ.get("WHISPER_MODEL_SIZE", DEFAULT_MODEL_SIZE).strip().lower()
    if model_size not in ALLOWED_MODEL_SIZES:
        allowed = ", ".join(sorted(ALLOWED_MODEL_SIZES))
        raise VoiceServiceError(f"WHISPER_MODEL_SIZE must be one of: {allowed}.")
    model = _load_local_model(model_size)
    import av

    try:
        segments, _info = model.transcribe(BytesIO(audio_bytes), beam_size=5, vad_filter=True)
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except (av.error.FFmpegError, OSError, RuntimeError, ValueError) as exc:
        raise VoiceServiceError(
            "Local Whisper could not decode this recording. Try recording it again or use the offline demo transcript."
        ) from exc

    if not transcript:
        raise VoiceServiceError("Whisper returned an empty transcript. Record the message again or enter it manually.")
    return transcript[:MAX_TRANSCRIPT_CHARS]


def analyze_support_urgency(transcript: str) -> SupportUrgency:
    normalized = re.sub(r"\s+", " ", transcript.casefold()).strip()
    if not normalized:
        raise ValueError("A confirmed transcript is required for support-urgency analysis.")

    if any(phrase in normalized for phrase in HIGH_URGENCY_PHRASES):
        return SupportUrgency(
            level="high",
            score=85,
            reason="The transcript includes wording about an immediate financial need.",
        )
    if any(phrase in normalized for phrase in MEDIUM_URGENCY_PHRASES):
        return SupportUrgency(
            level="medium",
            score=55,
            reason="The transcript includes wording that may indicate financial worry or difficulty.",
        )
    return SupportUrgency(
        level="low",
        score=10,
        reason="No clear support-urgency wording was identified in the transcript.",
    )
