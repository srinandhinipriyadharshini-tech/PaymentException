from __future__ import annotations
from core.models import Category, Payment, Remedy

SUPPORTED_RAILS = {"ACH", "WIRE", "RTP", "FEDNOW"}


def calculate_remedy(category: Category, payment: Payment) -> Remedy:
    if category is Category.NO_REMEDY or payment.rail in {"RTP", "FEDNOW"}:
        return Remedy(category=Category.NO_REMEDY, action="No simulated remedy available", rationale="Synthetic instant-payment demo rules do not provide a remedy.", available=False)
    if category is Category.ERRONEOUS:
        return Remedy(category=category, action="Request return of funds", rationale="Synthetic demo rule for an erroneous payment.", available=True)
    if category is Category.UNAUTHORISED:
        return Remedy(category=category, action="Open an unauthorised-payment investigation", rationale="Synthetic demo rule for an unauthorised payment.", available=True, requires_human_review=True)
    return Remedy(category=category, action="Open an authorised-scam investigation", rationale="Synthetic demo rule for an authorised but scammed payment.", available=True, requires_human_review=True)
