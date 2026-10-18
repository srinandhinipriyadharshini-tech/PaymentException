from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai.voice import (
    VoiceServiceError,
    analyze_support_urgency,
    transcribe_audio,
)


def test_support_urgency_uses_non_diagnostic_bounded_levels():
    assert analyze_support_urgency("I can't pay rent because my money is missing.").level == "high"
    assert analyze_support_urgency("I am worried about this payment.").level == "medium"
    assert analyze_support_urgency("I made a payment to Northwind.").level == "low"


def test_support_urgency_rejects_empty_transcript():
    with pytest.raises(ValueError, match="confirmed transcript"):
        analyze_support_urgency("  ")


def test_transcription_rejects_empty_audio():
    with pytest.raises(VoiceServiceError, match="recording is empty"):
        transcribe_audio(b"", "audio/wav")


def test_transcription_rejects_non_audio_content_type():
    with pytest.raises(VoiceServiceError, match="not recognized as audio"):
        transcribe_audio(b"audio", "application/octet-stream")


def test_transcription_rejects_invalid_model_size(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "unknown")
    with pytest.raises(VoiceServiceError, match="WHISPER_MODEL_SIZE"):
        transcribe_audio(b"audio", "audio/wav")


def test_transcription_uses_local_model_and_joins_segments(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")

    class LocalModel:
        def transcribe(self, audio, *, beam_size, vad_filter):
            assert audio.read() == b"recorded-audio"
            assert beam_size == 5
            assert vad_filter is True
            return iter(
                [
                    SimpleNamespace(text=" I did not authorize"),
                    SimpleNamespace(text=" the payment."),
                ]
            ), SimpleNamespace(language="en")

    with patch("ai.voice._load_local_model", return_value=LocalModel()) as load_model:
        assert transcribe_audio(b"recorded-audio", "audio/webm") == "I did not authorize the payment."

    load_model.assert_called_once_with("base")


def test_transcription_reports_empty_local_result(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")

    class LocalModel:
        def transcribe(self, *_args, **_kwargs):
            return iter([]), SimpleNamespace(language="en")

    with patch("ai.voice._load_local_model", return_value=LocalModel()):
        with pytest.raises(VoiceServiceError, match="empty transcript"):
            transcribe_audio(b"recorded-audio", "audio/wav")
