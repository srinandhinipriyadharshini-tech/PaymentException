from __future__ import annotations

from core.models import Category, Payment, Remedy

SUPPORTED_RAILS = {"ACH", "WIRE", "RTP", "FEDNOW"}

FEATURE_FLAGS = {
    "ENABLE_PENDING_CANCEL": True,
    "RTP_FEDNOW_REQUEST_AFTER_FUNDS_MOVED": False,
    "ENABLE_ACH_DOCUMENT_PRECONDITION": True,
    "ENABLE_INTL_WIRE_MANUAL_REVIEW": True,
}


def _remedy_no_remedy(category: Category, reason: str, *, requires_human_review: bool = False, message_type: str = "none") -> Remedy:
    return Remedy(
        category=category,
        action="No permitted remedy exists",
        rationale=reason,
        available=False,
        requires_human_review=requires_human_review,
        message_type=message_type,
        reason_code="none",
        deadline_days=None,
        recovery_guaranteed=False,
    )


def calculate_remedy(
    category: Category,
    payment: Payment,
    *,
    signed_statement_received: bool = True,
    is_international: bool = False,
    opening_request_exists: bool = False,
    feature_flags: dict[str, bool] | None = None,
) -> Remedy:
    flags = FEATURE_FLAGS | (feature_flags or {})
    rail = str(payment.rail).upper()
    status = str(payment.status).upper()

    if category is Category.AUTHORISED_BUT_SCAMMED:
        return Remedy(
            category=category,
            action="Escalate for manual review",
            rationale="Because the customer approved this payment, this is being sent to a specialist for manual review. I cannot promise that the money can be recovered.",
            available=False,
            requires_human_review=True,
            message_type="none",
            reason_code="none",
            deadline_days=None,
            recovery_guaranteed=False,
        )

    if category is Category.NO_REMEDY:
        return _remedy_no_remedy(category, "No recovery request is available for this rail under the configured rulebook.")

    if status == "PENDING" and flags.get("ENABLE_PENDING_CANCEL", False):
        if rail in {"ACH", "WIRE", "RTP", "FEDNOW"}:
            return Remedy(
                category=category,
                action="Cancel or stop pending payment",
                rationale="This payment has not moved yet. The request is a cancellation or stop, not a return, and recovery is not guaranteed.",
                available=True,
                requires_human_review=False,
                message_type="payment_cancel_request",
                reason_code="SYN_CANCEL01",
                deadline_days=None,
                recovery_guaranteed=False,
            )

    if rail == "ACH":
        if category is Category.UNAUTHORISED and status == "SETTLED":
            if not signed_statement_received and flags.get("ENABLE_ACH_DOCUMENT_PRECONDITION", False):
                return Remedy(
                    category=category,
                    action="Await signed statement",
                    rationale="To request a return of this debit we need your signed statement that you did not authorise it. No request has been submitted yet.",
                    available=False,
                    requires_human_review=False,
                    message_type="none",
                    reason_code="none",
                    deadline_days=None,
                    recovery_guaranteed=False,
                )
            return Remedy(
                category=category,
                action="Request return of funds",
                rationale="Recovery is not guaranteed by the sending or receiving institution.",
                available=True,
                requires_human_review=False,
                message_type="AC_RETURN",
                reason_code="SYN_R10",
                deadline_days=60,
                recovery_guaranteed=False,
            )
        if category is Category.ERRONEOUS and status == "SETTLED":
            return Remedy(
                category=category,
                action="Request return of funds",
                rationale="Recovery is not guaranteed by the sending or receiving institution.",
                available=True,
                requires_human_review=False,
                message_type="AC_RETURN",
                reason_code="SYN_R02",
                deadline_days=5,
                recovery_guaranteed=False,
            )

    if rail == "WIRE":
        if is_international and flags.get("ENABLE_INTL_WIRE_MANUAL_REVIEW", False):
            return Remedy(
                category=category,
                action="Escalate international wire for manual review",
                rationale="This is an international wire; review is manual and no automatic request is created.",
                available=False,
                requires_human_review=True,
                message_type="none",
                reason_code="none",
                deadline_days=None,
                recovery_guaranteed=False,
            )
        if status == "SETTLED" and category in {Category.UNAUTHORISED, Category.ERRONEOUS}:
            return Remedy(
                category=category,
                action="Request wire recall",
                rationale="A recall depends on the receiving bank and funds may not be recovered.",
                available=True,
                requires_human_review=False,
                message_type="wire_recall_request",
                reason_code="SYN_W01",
                deadline_days=1,
                recovery_guaranteed=False,
            )

    if rail in {"RTP", "FEDNOW"}:
        if status == "PENDING":
            message_type = "rtp_return_request" if rail == "RTP" else "fednow_return_request"
            reason_code = "SYN_rtp01" if rail == "RTP" else "SYN_fn01"
            return Remedy(
                category=category,
                action="Request return of funds",
                rationale="Recovery is not guaranteed by the sending or receiving institution.",
                available=True,
                requires_human_review=False,
                message_type=message_type,
                reason_code=reason_code,
                deadline_days=1,
                recovery_guaranteed=False,
            )
        if status == "SETTLED":
            if payment.funds_moved:
                if flags.get("RTP_FEDNOW_REQUEST_AFTER_FUNDS_MOVED", False):
                    message_type = "rtp_return_request" if rail == "RTP" else "fednow_return_request"
                    reason_code = "SYN_rtp01" if rail == "RTP" else "SYN_fn01"
                    return Remedy(
                        category=category,
                        action="Request return of funds",
                        rationale="Payment funds have already moved. The receiving bank may decline the request and funds may not be recovered.",
                        available=True,
                        requires_human_review=False,
                        message_type=message_type,
                        reason_code=reason_code,
                        deadline_days=1,
                        recovery_guaranteed=False,
                    )
                return _remedy_no_remedy(
                    category,
                    "The payment has already been delivered and cannot be pulled back through this process.",
                )

    if status not in {"SETTLED", "PENDING"}:
        return _remedy_no_remedy(category, f"The payment status is {status.lower()}, so there are no funds in an eligible recovery state.")

    return _remedy_no_remedy(category, "No rail/category rule permits a recovery request.")
