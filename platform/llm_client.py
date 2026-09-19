from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str
    tokens: int = 0


class LLMClient:
    """Offline-safe client seam for a future bank-provided model endpoint."""

    def __init__(self, model: str = "deterministic-demo") -> None:
        self.model = model

    def complete(self, prompt: str) -> ModelResponse:
        raise RuntimeError("No hosted LLM is configured; use the deterministic AI layer.")
