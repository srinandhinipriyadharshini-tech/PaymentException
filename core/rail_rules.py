from __future__ import annotations
from core.models import Category, Payment, Remedy

SUPPORTED_RAILS = {"ACH", "WIRE", "RTP", "FEDNOW"}

RULES = {
    ("ACH", Category.UNAUTHORISED): (True, "AC_RETURN", "SYN_R10", 60),
    ("ACH", Category.ERRONEOUS): (True, "AC_RETURN", "SYN_R02", 5),
    ("ACH", Category.AUTHORISED_BUT_SCAMMED): (True, "AC_RETURN", "SYN_R10", 60),
    ("WIRE", Category.UNAUTHORISED): (True, "wire_recall_request", "SYN_W01", 1),
    ("WIRE", Category.ERRONEOUS): (True, "wire_recall_request", "SYN_W01", 1),
    ("WIRE", Category.AUTHORISED_BUT_SCAMMED): (True, "wire_recall_request", "SYN_W01", 1),
    ("RTP", Category.UNAUTHORISED): (True, "rtp_return_request", "SYN_rtp01", 1),
    ("RTP", Category.ERRONEOUS): (True, "rtp_return_request", "SYN_rtp01", 1),
    ("FEDNOW", Category.UNAUTHORISED): (True, "fednow_return_request", "SYN_fn01", 1),
    ("FEDNOW", Category.ERRONEOUS): (True, "fednow_return_request", "SYN_fn01", 1),
}


def calculate_remedy(category: Category, payment: Payment) -> Remedy:
    rule = RULES.get((payment.rail, category))
    if category is Category.AUTHORISED_BUT_SCAMMED:
        return Remedy(category=category, action="Escalate for manual review", rationale="Authorised-scam claims require manual handling and do not promise recovery.", available=False, requires_human_review=True)
    if payment.status not in {"SETTLED", "PENDING"}:
        return Remedy(category=category, action="No permitted remedy exists", rationale=f"The payment status is {payment.status.lower()}, so there are no funds in an eligible recovery state.", available=False)
    if category is Category.NO_REMEDY or rule is None:
        return Remedy(category=category, action="No permitted remedy exists", rationale="No rail/category rule permits a recovery request.", available=False)
    available, message_type, reason_code, deadline_days = rule
    if payment.rail in {"RTP", "FEDNOW"} and payment.funds_moved:
        available = False
    action = "Request return of funds" if category is Category.ERRONEOUS else "Open an unauthorised-payment investigation" if category is Category.UNAUTHORISED else "Open an authorised-scam investigation"
    return Remedy(category=category, action=action, rationale="Recovery is not guaranteed by the sending or receiving institution.", available=available, requires_human_review=True, message_type=message_type, reason_code=reason_code, deadline_days=deadline_days, recovery_guaranteed=False)
