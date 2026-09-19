from __future__ import annotations

from abc import ABC
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class Citation(BaseModel):
    source: str
    ref: str
    quote: str | None = None


class AIResult(BaseModel, Generic[T]):
    value: T | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    abstained: bool = False
    abstain_reason: str | None = None
    reasoning: str = ""


class AILayer(ABC):
    """Common contract marker for the repository's AI-layer implementations."""
