from __future__ import annotations

from ai.demo_adapter import DemoAIAdapter
from core.models import Category, Payment, Remedy
from app_platform.ai_contract import AILayer, AIResult, Citation
from pydantic import BaseModel


class CaseOutputs(BaseModel):
    customer_message: str
    interbank_request: str


class DraftingAI(AILayer):
    def __init__(self) -> None:
        self.adapter = DemoAIAdapter()

    def draft(self, claim_text: str, payment: Payment, category: Category, remedy: Remedy) -> AIResult[CaseOutputs]:
        customer, interbank = self.adapter.draft_outputs(claim_text, payment, category)
        if not remedy.available:
            customer = f"No remedy is available for this {payment.rail} payment under the synthetic rulebook; the payment cannot be recovered through this process."
            interbank = f"No inter-bank request created: {payment.payment_id} on {payment.rail}; remedy unavailable."
        else:
            interbank = f"message_type={remedy.message_type}; reason_code={remedy.reason_code}; deadline_days={remedy.deadline_days}; recovery_guaranteed={str(remedy.recovery_guaranteed).upper()}; category={category.value}"
        return AIResult(
            value=CaseOutputs(customer_message=customer, interbank_request=interbank),
            confidence=0.9,
            citations=[Citation(source="payments", ref=payment.payment_id), Citation(source="rail_rules", ref=payment.rail)],
        )
