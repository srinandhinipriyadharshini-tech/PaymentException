from __future__ import annotations

from ai.demo_adapter import DemoAIAdapter
from core.models import ExtractedFacts
from app_platform.ai_contract import AILayer, AIResult


class IntakeAI(AILayer):
    def __init__(self) -> None:
        self.adapter = DemoAIAdapter()

    def extract(self, claim_text: str) -> AIResult[ExtractedFacts]:
        facts = self.adapter.extract_claim(claim_text)
        if not any((facts.amount_min, facts.date_min, facts.day_of_month, facts.beneficiary_description)):
            return AIResult(
                confidence=0.0,
                abstained=True,
                abstain_reason="The claim contains no searchable amount, date, or beneficiary.",
                reasoning="A payment cannot be located without at least one searchable fact.",
            )
        return AIResult(
            value=facts,
            confidence=0.85,
            citations=[],
            reasoning="Extracted deterministic payment-search facts from the customer claim.",
        )
