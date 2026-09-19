from __future__ import annotations
from abc import ABC, abstractmethod
from core.models import CandidateMatch, Category, ExtractedFacts, Payment


class AIAdapter(ABC):
    @abstractmethod
    def extract_claim(self, claim_text: str) -> ExtractedFacts: ...
    @abstractmethod
    def rank_candidates(self, facts: ExtractedFacts, candidates: list[Payment]) -> list[CandidateMatch]: ...
    @abstractmethod
    def classify_claim(self, claim_text: str, payment: Payment) -> tuple[Category, float, list[str]]: ...
    @abstractmethod
    def draft_outputs(self, claim_text: str, payment: Payment, category: Category) -> tuple[str, str]: ...
