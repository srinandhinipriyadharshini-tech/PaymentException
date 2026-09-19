from __future__ import annotations

from ai.demo_adapter import DemoAIAdapter
from core.models import ExtractedFacts, Payment, RankedCandidates
from platform.ai_contract import AILayer, AIResult, Citation


class MatchingAI(AILayer):
    def __init__(self) -> None:
        self.adapter = DemoAIAdapter()

    def rank(self, facts: ExtractedFacts, candidates: list[Payment]) -> AIResult[RankedCandidates]:
        ranked = RankedCandidates(candidates=self.adapter.rank_candidates(facts, candidates))
        citations = [
            Citation(source="payments", ref=item.payment.payment_id, quote=", ".join(item.match_reasons))
            for item in ranked.candidates[:5]
        ]
        if not ranked.candidates:
            return AIResult(value=ranked, confidence=0.0, citations=citations, abstained=True, abstain_reason="No payment matched the extracted facts.")
        if len(ranked.candidates) > 1 and ranked.candidates[0].confidence - ranked.candidates[1].confidence < 0.1:
            ranked.abstained = True
            ranked.abstention_reason = "The leading payment candidates are too close to choose safely."
            return AIResult(value=ranked, confidence=ranked.candidates[0].confidence, citations=citations, abstained=True, abstain_reason=ranked.abstention_reason)
        return AIResult(value=ranked, confidence=ranked.candidates[0].confidence, citations=citations)
