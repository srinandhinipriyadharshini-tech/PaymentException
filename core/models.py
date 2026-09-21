from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class Category(str, Enum):
    ERRONEOUS = "ERRONEOUS"
    UNAUTHORISED = "UNAUTHORISED"
    AUTHORISED_BUT_SCAMMED = "AUTHORISED_BUT_SCAMMED"
    NO_REMEDY = "NO_REMEDY"


class CaseStatus(str, Enum):
    RECEIVED = "RECEIVED"
    TRANSCRIPT_REVIEW_REQUIRED = "TRANSCRIPT_REVIEW_REQUIRED"
    FACTS_EXTRACTED = "FACTS_EXTRACTED"
    SEARCHING = "SEARCHING"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    PAYMENT_MATCHED = "PAYMENT_MATCHED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    SUBMITTED_SIMULATED = "SUBMITTED_SIMULATED"
    NO_REMEDY = "NO_REMEDY"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class RequestStatus(str, Enum):
    NOT_CREATED = "NOT_CREATED"
    DRAFT_READY = "DRAFT_READY"
    AGENT_APPROVED = "AGENT_APPROVED"
    SIMULATED_SUBMITTED = "SIMULATED_SUBMITTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class Payment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_id: str
    rail: str
    amount: Decimal = Field(ge=0)
    currency: str
    value_date: date
    settlement_timestamp: datetime
    debtor_account: str
    creditor_account: str
    creditor_registered_name: str
    creditor_trading_name: str
    status: str
    funds_moved: bool


class ExtractedFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_min: Optional[Decimal] = Field(default=None, ge=0)
    amount_max: Optional[Decimal] = Field(default=None, ge=0)
    date_min: Optional[date] = None
    date_max: Optional[date] = None
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    month_of_year: Optional[int] = Field(default=None, ge=1, le=12)
    week_of_month: Optional[int] = Field(default=None, ge=1, le=5)
    beneficiary_description: Optional[str] = None
    customer_reason: Optional[str] = None
    rail: Optional[str] = None
    customer_account: Optional[str] = None


class CandidateMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment: Payment
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    match_reasons: list[str] = Field(default_factory=list)


class RankedCandidates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[CandidateMatch] = Field(default_factory=list)
    abstained: bool = False
    abstention_reason: Optional[str] = None


class Remedy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Category
    action: str
    rationale: str
    available: bool
    requires_human_review: bool = False
    message_type: str = "none"
    reason_code: str = "none"
    deadline_days: int | None = None
    recovery_guaranteed: bool = False


class CaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    case_status: CaseStatus
    claim_category: Optional[Category] = None
    category: Optional[Category] = None
    request_status: RequestStatus = RequestStatus.NOT_CREATED
    reference_id: Optional[str] = None
    rail: Optional[str] = None
    remedy_available: bool = False
    agent_approval_required: bool = True
    agent_approved: bool = False
    extracted_facts: ExtractedFacts
    ranked_candidates: RankedCandidates
    selected_payment: Optional[Payment] = None
    category: Optional[Category] = None
    remedy: Optional[Remedy] = None
    deadline: Optional[date] = None
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    clarification_question: Optional[str] = None
    customer_message: str = ""
    interbank_request: str = ""
    redacted: bool = True
    agent_confirmed: bool = False
    raised_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    last_updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def submission_allowed(self) -> bool:
        return bool(
            self.agent_approved
            and self.selected_payment
            and self.remedy
            and self.remedy.available
            and (self.deadline is None or self.deadline >= date.today())
            and not self.clarification_question
        )

