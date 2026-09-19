from __future__ import annotations
import re


def redact(text: str) -> str:
    text = re.sub(r"ACCT-SYN-\d{6}", "[REDACTED-ACCOUNT]", text)
    return re.sub(r"PMT-SYN-\d{6}", "[REDACTED-PAYMENT]", text)


redact_text = redact
