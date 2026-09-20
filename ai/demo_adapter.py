from __future__ import annotations
import re
from datetime import date
from decimal import Decimal
from ai.adapter import AIAdapter
from core.models import CandidateMatch, Category, ExtractedFacts, Payment
from core.decision_rules import approximate_amount_range


NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def parse_word_amount(words: str) -> Decimal:
    total, current = 0, 0
    for token in words.replace("-", " ").split():
        if token == "and":
            continue
        if token in NUMBER_WORDS:
            current += NUMBER_WORDS[token]
        elif token == "hundred":
            current = max(current, 1) * 100
        elif token in {"thousand", "million"}:
            total += max(current, 1) * (1000 if token == "thousand" else 1000000)
            current = 0
        elif token == "grand":
            total += max(current, 1) * 1000
            current = 0
    return Decimal(total + current)


class DemoAIAdapter(AIAdapter):
    def extract_claim(self, claim_text: str) -> ExtractedFacts:
        text, lowered = claim_text.strip(), claim_text.lower()
        amounts = [Decimal(value.replace(",", "")) for value in re.findall(r"(?:[$£]|gbp\s*)(\d+(?:,\d{3})?(?:\.\d{1,2})?)", text, re.I)]
        amounts.extend(Decimal(value.replace(",", "")) for value in re.findall(r"(?:about|around|approximately|approx)\s+(?:[$£]|gbp\s*)?(\d+(?:,\d{3})?(?:\.\d{1,2})?)\b", lowered, re.I))
        amounts.extend(Decimal(value.replace(",", "")) for value in re.findall(r"(?:payment|charge|transfer|sent)\s+(?:(?:about|around|approximately|approx)\s+)?(?:of\s+)?(?:[$£]|gbp\s*)?(\d+(?:,\d{3})?(?:\.\d{1,2})?)\b", lowered, re.I))
        amounts.extend(Decimal(value.replace(",", "")) * (1000 if suffix.lower() == "k" else 1) for value, suffix in re.findall(r"\b(\d+(?:,\d{3})?(?:\.\d{1,2})?)\s*(k|grand)\b", text, re.I))
        word_amounts = re.findall(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|grand)(?:\s+(?:and\s+)?(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|grand)){0,10}\b", lowered)
        amounts.extend(parse_word_amount(value) for value in word_amounts if any(unit in value for unit in ("hundred", "thousand", "million", "grand")))
        dates = [date.fromisoformat(value.replace("/", "-")) for value in re.findall(r"\b(2026[-/]\d{1,2}[-/]\d{1,2})\b", text)]
        day_matches = []
        for pattern in (
            r"\b(?:the\s+)?([12]\d|3[01]|[1-9])(?:st|nd|rd|th)\b",
            r"\b([12]\d|3[01]|[1-9])\s+(?:date|day)\b",
            r"\b(?:date|day)\s+([12]\d|3[01]|[1-9])\b",
        ):
            day_matches.extend((match.start(), int(match.group(1))) for match in re.finditer(pattern, lowered))
        if not day_matches:
            day_match = re.fullmatch(r"(?:the\s+)?([12]\d|3[01]|[1-9])", lowered)
            if day_match:
                day_matches.append((day_match.start(), int(day_match.group(1))))
        months = {name: number for number, name in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"), 1)}
        week_words = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4, "fifth": 5, "5th": 5}
        week_matches = list(re.finditer(r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s+week\b", lowered))
        week_of_month = week_words[week_matches[-1].group(1)] if week_matches else None
        if week_matches:
            week_start = (week_of_month - 1) * 7 + 1
            week_end = min(week_start + 6, 31)
            day_matches = [(match.start(), value) for match in day_matches if not (match[0] >= week_matches[-1].start() - 4 and match[0] <= week_matches[-1].end() + 4)]
            if month_matches := list(re.finditer(r"\b(" + "|".join(months) + r")\b", lowered)):
                month_number = months[month_matches[-1].group(1)]
                dates.extend((date(2026, month_number, week_start), date(2026, month_number, week_end)))
        month_matches = list(re.finditer(r"\b(" + "|".join(months) + r")\b", lowered))
        month_day_matches = list(re.finditer(r"\b(" + "|".join(months) + r")\s+([12]\d|3[01]|[1-9])(?:st|nd|rd|th)?\b", lowered))
        for match in month_day_matches:
            try:
                dates.append(date(2026, months[match.group(1)], int(match.group(2))))
            except ValueError:
                continue
        rail = next((item for item in ("ACH", "WIRE", "RTP", "FEDNOW") if item.lower() in lowered), None)
        beneficiary_aliases = (("northwind", "Northwind"), ("blue oak", "Blue Oak"), ("cedar", "Cedar Works"), ("lumen", "Lumen Health"))
        beneficiary = next((canonical for alias, canonical in beneficiary_aliases if alias in lowered), None)
        match = re.search(r"says\s+([A-Za-z][A-Za-z ]{2,35}?)(?:\s+on|\s+for|\s+was|\s+of|[,.]|$)", text, re.I)
        match = match or re.search(r"(?:to|from|at)\s+([A-Za-z][A-Za-z ]{2,35}?)(?:\s+on|\s+for|\s+was|\s+of|[,.]|$)", text, re.I)
        match = match or re.search(r"(?:for|with)\s+([A-Za-z][A-Za-z ]{2,35}?)(?:\s+on|\s+for|\s+was|\s+of|[,.]|$)", text, re.I)
        if match and beneficiary is None: beneficiary = match.group(1).strip()
        reason = "unauthorised" if "unauthor" in lowered or "did not make" in lowered or "never authorized" in lowered or "never authorised" in lowered else "authorised but scammed" if "scam" in lowered or "fraud" in lowered else "erroneous" if "mistake" in lowered or "wrong" in lowered else "no remedy" if "instant" in lowered else ""
        approximate = any(word in lowered for word in ("about", "around", "approximately", "approx"))
        amount_min = min(amounts) if amounts else None
        amount_max = max(amounts) if amounts else None
        if approximate and amount_min is not None:
            amount_min, amount_max = approximate_amount_range(amount_min)
        return ExtractedFacts(amount_min=amount_min, amount_max=amount_max, date_min=min(dates) if dates else None, date_max=max(dates) if dates else None, day_of_month=day_matches[-1][1] if day_matches else None, month_of_year=months[month_matches[-1].group(1)] if month_matches else None, week_of_month=week_of_month, beneficiary_description=beneficiary, customer_reason=reason, rail=rail)

    def rank_candidates(self, facts: ExtractedFacts, candidates: list[Payment]) -> list[CandidateMatch]:
        ranked = []
        for payment in candidates:
            score, reasons = 0.2, []
            score = 0.0
            if facts.amount_min is not None and facts.amount_max is not None and facts.amount_min <= payment.amount <= facts.amount_max: score += 0.4; reasons.append("amount")
            date_match = facts.date_min and facts.date_max and facts.date_min <= payment.value_date <= facts.date_max
            date_match = date_match or (facts.day_of_month and facts.day_of_month == payment.value_date.day)
            date_match = date_match or (facts.month_of_year and facts.month_of_year == payment.value_date.month)
            if date_match: score += 0.25; reasons.append("date")
            if facts.beneficiary_description and (facts.beneficiary_description.lower() in payment.creditor_trading_name.lower() or facts.beneficiary_description.lower() in payment.creditor_registered_name.lower()): score += 0.25; reasons.append("beneficiary name")
            if facts.customer_account and facts.customer_account == payment.debtor_account: score += 0.1; reasons.append("customer account")
            ranked.append(CandidateMatch(payment=payment, confidence=min(score, 0.99), match_reasons=reasons))
        return sorted(ranked, key=lambda item: (-item.confidence, item.payment.payment_id))

    def classify_claim(self, claim_text: str, payment: Payment) -> tuple[Category, float, list[str]]:
        text = claim_text.lower()
        if "unauthor" in text or "did not make" in text or "never authorized" in text or "never authorised" in text: return Category.UNAUTHORISED, 0.94, ["customer says payment was not authorised"]
        if "scam" in text or "fraud" in text: return Category.AUTHORISED_BUT_SCAMMED, 0.92, ["customer describes a scam"]
        if "instant" in text or payment.rail in {"RTP", "FEDNOW"}: return Category.NO_REMEDY, 0.96, ["instant-payment synthetic rule"]
        return Category.ERRONEOUS, 0.84, ["default synthetic erroneous-payment classification"]

    def draft_outputs(self, claim_text: str, payment: Payment, category: Category) -> tuple[str, str]:
        return (f"We recorded your {category.value.lower()} claim for the payment. Any return or recall request is not a guarantee of recovery; the receiving institution may decline it and funds may no longer be available.", f"Synthetic request: review {payment.payment_id} for category {category.value}. This request does not guarantee recovery.")
