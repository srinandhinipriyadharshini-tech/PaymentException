from __future__ import annotations

from ai.demo_adapter import DemoAIAdapter
from core.models import Category, ExtractedFacts, Payment
from app_platform.ai_contract import AILayer, AIResult, Citation


class ClassificationAI(AILayer):
    def __init__(self) -> None:
        self.adapter = DemoAIAdapter()

    def classify(self, facts: ExtractedFacts, payment: Payment) -> AIResult[Category]:
        category, confidence, reasons = self.adapter.classify_claim(facts.customer_reason or "", payment)
        return AIResult(
            value=category,
            confidence=confidence,
            citations=[Citation(source="payment_claim", ref=payment.payment_id, quote=", ".join(reasons))],
            reasoning="Classified the stated reason together with the matched payment rail.",
        )
