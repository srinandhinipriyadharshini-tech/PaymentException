# Payment Exception Rules (Consumer Accounts Only)

Authoritative, deterministic rules for the synthetic payment-exception application.
Copilot: implement these rules exactly. Do not invent behavior, thresholds, codes, or wording that is not defined here. When a rule here conflicts with generated code, the rule wins.

Scope: **consumer accounts only**. Business accounts are out of scope. All reason codes (`SYN_*`) and the 1-day windows for WIRE/RTP/FEDNOW are **synthetic demo constants**, not production values.

---

## 0. Engineering principles

1. **Pure and deterministic.** Rule functions take all inputs as arguments, including `now`. Never read the system clock, random values, or the network inside a rule function.
2. **Fixed evaluation order.** Gates run in the order in section 3. The first gate that stops processing decides the outcome.
3. **Two tracks.** Track A is customer protection (Reg E clock). Track B is inter-bank recovery (the request). They are independent. A Track B outcome never changes a Track A result.
4. **No guarantees.** `recovery_guaranteed` is always `FALSE`. A request is only a request.
5. **Every decision is auditable.** Each decision records `rule_id`, inputs used, outcome code, and masked identifiers.
6. **Mask all PII in every output, log, and message** (section 9).

---

## 1. Configuration constants

```yaml
timezone: America/New_York
deadline_cutoff_local_time: "17:00"      # deadline is inclusive through this time on the deadline date
deadline_inclusive: true

match:
  min_score: 60            # below this -> NO_MATCH
  auto_match_score: 80     # top score needed for automatic selection
  min_gap: 15              # top score minus second score needed for automatic selection
  approximate_amount_ranges:
    "around 1000": [500, 1999]   # approximate amounts are searched as ranges, never exact points

weights:
  amount: 40
  date: 25
  beneficiary: 25
  account: 10

regE:
  notice_window_days: 60              # calendar days from statement date
  investigation_business_days: 10
  extended_investigation_days: 45     # calendar days
  extended_investigation_days_new_account: 90
  new_account_age_days: 30

feature_flags:
  ENABLE_PENDING_CANCEL: true                    # extension E-01 (cancel/stop for PENDING payments)
  RTP_FEDNOW_REQUEST_AFTER_FUNDS_MOVED: false    # false = strict reading of base rulebook
  ENABLE_ACH_DOCUMENT_PRECONDITION: true         # extension E-02 (signed statement for ACH unauthorised debits)
  ENABLE_INTL_WIRE_MANUAL_REVIEW: true           # extension E-03
```

`banking_days` exclude Saturdays, Sundays, and the Federal Reserve holiday list supplied in configuration (`fed_holidays: [YYYY-MM-DD, ...]`). `calendar_days` count every day.

---

## 2. Rail configuration (base rulebook, authoritative)

| Rail | Category | Available | Message type | Reason code | Deadline | Day type | Recovery guaranteed |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| ACH | Unauthorised | TRUE | `AC_RETURN` | `SYN_R10` | 60 | calendar | FALSE |
| ACH | Erroneous | TRUE | `AC_RETURN` | `SYN_R02` | 5 | banking | FALSE |
| WIRE | Unauthorised | TRUE | `wire_recall_request` | `SYN_W01` | 1 | calendar | FALSE |
| WIRE | Erroneous | TRUE | `wire_recall_request` | `SYN_W01` | 1 | calendar | FALSE |
| RTP | Unauthorised, Erroneous | TRUE (see RTP rules) | `rtp_return_request` | `SYN_rtp01` | 1 | calendar | FALSE |
| FEDNOW | Unauthorised, Erroneous | TRUE (see FEDNOW rules) | `fednow_return_request` | `SYN_fn01` | 1 | calendar | FALSE |
| Any | Authorised-but-scammed | FALSE | `none` | `none` | none | n/a | FALSE |
| Any | No remedy | FALSE | `none` | `none` | none | n/a | FALSE |

Extension message type (only when `ENABLE_PENDING_CANCEL`): `payment_cancel_request`, reason `SYN_CANCEL01`, `recovery_guaranteed = FALSE`.

---

## 3. Input model

Required fields on every claim evaluation:

| Field | Values / meaning |
| --- | --- |
| `now` | Injected timestamp (timezone-aware) |
| `transcript_confirmed` | bool |
| `agent_review_confirmed` | bool |
| `claim_category` | `UNAUTHORISED`, `ERRONEOUS`, `AUTHORISED_BUT_SCAMMED` |
| `claim_date` | Date the customer reported the issue |
| `customer_id`, `customer_accounts[]` | Ownership is a hard search constraint |
| `payment.rail` | `ACH`, `WIRE`, `RTP`, `FEDNOW` |
| `payment.status` | `PENDING`, `SETTLED` |
| `payment.direction` | `DEBIT_PULL` (third party pulled funds) or `CREDIT_PUSH` (bank sent funds out) |
| `payment.payment_event_date` | Anchor date (use settlement date when present) |
| `payment.statement_date` | Date the statement showing the payment was sent |
| `payment.is_international` | bool (WIRE) |
| `payment.account_age_days` | int |
| `signed_statement_received` | bool (ACH unauthorised debit) |
| `open_request_exists` | bool (idempotency) |

`funds_moved = (payment.status == SETTLED)`.

---

## 4. Evaluation order (gates)

Run in this exact order. Stop at the first gate that returns a terminal outcome.

| Gate | Condition | Outcome code | Request created | Ask customer to confirm |
| --- | --- | --- | --- | --- |
| G-01 | `transcript_confirmed == false` | `STOP_UNCONFIRMED_TRANSCRIPT` | No | No |
| G-02 | Match step (section 5) returns no candidate or top score < `min_score` | `NO_MATCH` | No | No |
| G-03 | Match step returns ambiguity | `CLARIFY_AMBIGUOUS` | No | Ask to clarify (not to confirm a request) |
| G-04 | `claim_category == AUTHORISED_BUT_SCAMMED` | `ESCALATE_SCAM` | No | No |
| G-05 | `open_request_exists == true` | `BLOCK_DUPLICATE` | No | No |
| G-06 | Rail rules (sections 7 to 10) find no permitted remedy | `NO_REMEDY` | No | No |
| G-07 | Deadline passed (section 6) | `ESCALATE_EXPIRED` | No | No |
| G-08 | Extension precondition missing (E-02) | `AWAIT_DOCUMENT` | No | No |
| G-09 | `agent_review_confirmed == false` | `HOLD_FOR_HUMAN_REVIEW` | No | No |
| G-10 | All gates passed | `REMEDY_AVAILABLE` | Only after customer confirmation | **Yes** |

Rules for G-02 and G-04: when there is no matching payment, do **not** classify the claim, select a remedy, compute a deadline, or create a request. Preserve the `AUTHORISED_BUT_SCAMMED` category on the case when G-04 fires.

Track A (section 6) is evaluated after the gates for any matched payment and is reported independently. It is also reported for `ESCALATE_EXPIRED` and `NO_REMEDY` outcomes on ACH, RTP, and FEDNOW unauthorised claims.

---

## 5. Matching and ranking

Search only the customer's own accounts (`customer_accounts[]`). Never rank payments from other customers.

### Score (total 100)

| Signal | Points | Rule |
| --- | ---: | --- |
| Amount | 40 | Exact = 40. Within 1% = 30. Within 5% = 15. Otherwise 0. For approximate amounts: 40 if within 10% of the stated figure, 25 if elsewhere inside the configured range, else 0. |
| Date | 25 | Same day = 25, minus 5 per day apart, floor 0. If the customer gives a date range: 25 inside the range, otherwise decay by days from the nearest boundary. |
| Beneficiary | 25 | Normalised exact match on registered name **or any known trading name** = 25. Fuzzy token similarity ≥ 0.80 = 15. Otherwise 0. |
| Account | 10 | The payment is on the account the customer named, or the customer has only one account. Otherwise 0. |

Normalisation: lower-case, trim, collapse whitespace, strip punctuation and legal suffixes (`inc`, `llc`, `ltd`, `corp`).

### Selection

1. Sort candidates by score descending.
2. If no candidates or `top < 60` -> `NO_MATCH`.
3. If `top >= 80` and (there is no second candidate or `top - second >= 15`) -> `MATCHED`.
4. Otherwise -> `AMBIGUOUS`. Never silently choose between similarly ranked candidates.
5. Tie-breakers (only to order candidates, never to resolve ambiguity): account match, then rail stated by customer, then most recent date.
6. When several accounts hold similar payments, prefer the account match.

A clarification result must not create or submit a request.

---

## 6. Deadlines (Track B) and Reg E clock (Track A)

### 6.1 Track B deadline

```
anchor = payment.payment_event_date
deadline_date = anchor + deadline_days   (calendar_days or banking_days per rail table)
deadline_at   = deadline_date at 17:00 America/New_York
expired       = now > deadline_at
```

When `expired`:

- Do not submit the return, reversal, or recall request.
- State plainly that the configured window has passed.
- Escalate for manual review and close the automatic flow.
- Do not ask the customer for confirmation.

Deadlines are not evaluated for `PENDING` cancel requests (E-01).

### 6.2 Track A (Reg E), consumer electronic transfers

Applies **only** to `UNAUTHORISED` claims on `ACH`, `RTP`, and `FEDNOW`. It does **not** apply to WIRE (domestic), to customer-entered mistakes (wrong beneficiary, wrong amount, duplicate), or to authorised-but-scammed.

| ID | Rule | Output |
| --- | --- | --- |
| REGE-01 | `claim_date - statement_date <= 60` calendar days | `notice_timely = true`; otherwise `false` and Track A status `MANUAL_REVIEW_LATE_NOTICE` |
| REGE-02 | Investigation due = `claim_date` + 10 banking days | `investigation_due` |
| REGE-03 | If the investigation cannot complete by `investigation_due`, provisional credit is due by the same date and the investigation extends to 45 calendar days from `claim_date` | `provisional_credit_due_by`, `extended_due` |
| REGE-04 | If `account_age_days < 30`, the extended window is 90 calendar days | `extended_due` |
| REGE-05 | Track A result never promises the outcome to the customer | text rule |

Track A runs even when Track B is blocked, expired, or has no remedy.

---

## 7. ACH rules (consumer)

| ID | Condition | Outcome |
| --- | --- | --- |
| ACH-01 | `DEBIT_PULL`, `UNAUTHORISED`, `SETTLED`, deadline open (60 calendar days) | Remedy `AC_RETURN` / `SYN_R10` |
| ACH-02 | `DEBIT_PULL`, `UNAUTHORISED`, `SETTLED`, `signed_statement_received == false`, `ENABLE_ACH_DOCUMENT_PRECONDITION` | `AWAIT_DOCUMENT` (G-08). Explain that a signed statement is needed. No request. |
| ACH-03 | `UNAUTHORISED`, deadline passed | `ESCALATE_EXPIRED` |
| ACH-04 | `ERRONEOUS` (wrong amount, wrong account, duplicate), `SETTLED`, deadline open (5 banking days) | Remedy `AC_RETURN` / `SYN_R02` |
| ACH-05 | `ERRONEOUS`, deadline passed | `ESCALATE_EXPIRED` |
| ACH-06 | `CREDIT_PUSH`, `UNAUTHORISED`, deadline passed (60-day return window does not apply to bank-originated credits) | `ESCALATE_EXPIRED` and flag `FRAUD_REVIEW` |
| ACH-07 | `PENDING` (not yet settled), `ENABLE_PENDING_CANCEL` | Extension E-01 remedy `payment_cancel_request` / `SYN_CANCEL01` |

Wording note: for `CREDIT_PUSH` erroneous claims, describe the request as a reversal request in customer text. The message type stays `AC_RETURN`.

---

## 8. WIRE rules (consumer)

| ID | Condition | Outcome |
| --- | --- | --- |
| WIRE-01 | Domestic, `SETTLED`, `UNAUTHORISED` or `ERRONEOUS`, deadline open (1 day) | Remedy `wire_recall_request` / `SYN_W01` |
| WIRE-02 | Domestic, deadline passed | `ESCALATE_EXPIRED` |
| WIRE-03 | `PENDING` (not released), `ENABLE_PENDING_CANCEL` | Extension E-01 cancel |
| WIRE-04 | `AUTHORISED_BUT_SCAMMED`, deadline still open | `ESCALATE_SCAM` with priority `URGENT` |
| WIRE-05 | `is_international == true`, `ENABLE_INTL_WIRE_MANUAL_REVIEW` | `ESCALATE_MANUAL_REVIEW` (E-03). No automatic request. |
| WIRE-06 | Any domestic wire | Track A = `NOT_APPLICABLE` |

Customer text must say a recall depends on the receiving bank and funds may not be recovered.

---

## 9. RTP rules (consumer)

| ID | Condition | Outcome |
| --- | --- | --- |
| RTP-01 | `PENDING` (funds not moved), `UNAUTHORISED` or `ERRONEOUS`, deadline open | Remedy `rtp_return_request` / `SYN_rtp01` |
| RTP-02 | `SETTLED` (funds moved), `RTP_FEDNOW_REQUEST_AFTER_FUNDS_MOVED == true`, deadline open | Remedy `rtp_return_request` / `SYN_rtp01`, with the no-recovery-promise text |
| RTP-03 | `SETTLED` (funds moved), `RTP_FEDNOW_REQUEST_AFTER_FUNDS_MOVED == false` | `NO_REMEDY`. Explain directly that the payment has already been delivered and cannot be pulled back through this process. |
| RTP-04 | Deadline passed | `ESCALATE_EXPIRED` |
| RTP-05 | Any RTP outcome with funds moved | Never promise recovery. Include the receiving-bank-may-decline text. |

## 10. FEDNOW rules (consumer)

Identical to the RTP rules with `fednow_return_request` / `SYN_fn01`:

| ID | Condition | Outcome |
| --- | --- | --- |
| FN-01 | `PENDING`, `UNAUTHORISED` or `ERRONEOUS`, deadline open | Remedy `fednow_return_request` / `SYN_fn01` |
| FN-02 | `SETTLED`, flag true, deadline open | Remedy `fednow_return_request` / `SYN_fn01`, no-promise text |
| FN-03 | `SETTLED`, flag false | `NO_REMEDY`, direct explanation |
| FN-04 | Deadline passed | `ESCALATE_EXPIRED` |
| FN-05 | Funds moved | Never promise recovery |

---

## 11. Customer conversation rules

- Ask the customer to confirm **only** when the outcome is `REMEDY_AVAILABLE` (matched payment, available remedy, open deadline, all preconditions met).
- For `NO_MATCH`, `NO_REMEDY`, `ESCALATE_EXPIRED`, `ESCALATE_SCAM`, `AWAIT_DOCUMENT`, and `BLOCK_DUPLICATE`, explain the outcome directly. Do not ask for confirmation.
- For `CLARIFY_AMBIGUOUS`, ask which payment the customer means. Show only masked identifiers.
- An agent recommendation does not bypass the policy gate.
- Customer confirmation may produce a **simulated** request only when rail, deadline, account, and human-review rules all permit it.
- Never use hedging language ("we will keep trying") when no remedy exists.

### Explanation templates (use verbatim, fill the placeholders)

| Outcome | Template |
| --- | --- |
| `NO_MATCH` | "I could not find a payment on your accounts that matches those details. Please check the amount, date, or recipient and try again." |
| `CLARIFY_AMBIGUOUS` | "I found more than one payment that could match. Which of these did you mean: {masked_candidate_list}?" |
| `ESCALATE_SCAM` | "Because you approved this payment, this is being sent to a specialist for manual review. I cannot promise that the money can be recovered." |
| `ESCALATE_EXPIRED` | "The {deadline_days}-{day_type} day window for this {rail} request ended on {deadline_date}. I cannot submit a request, so this has been escalated for manual review." |
| `NO_REMEDY` | "No recovery request is available for this {rail} payment because {reason}. No request has been created." |
| `AWAIT_DOCUMENT` | "To request a return of this debit we need your signed statement that you did not authorise it. No request has been submitted yet." |
| `REMEDY_AVAILABLE` | "I can prepare a {message_type} for this payment. This is a request only and does not guarantee recovery. Do you want me to proceed?" |
| `BLOCK_DUPLICATE` | "A request for this payment is already open, so I have not created another." |

---

## 12. Admin and review rules

- Admin can view active and non-active cases with their status.
- Admin approval is allowed only for escalated or manual-review cases.
- Admin must not approve cases already approved by the agent.
- Admin approval triggers the simulated customer email.
- No-remedy cases may be closed as no remedy.
- Agent-approved cases remain visible and need no further admin approval.

---

## 13. Data ownership

- 6,000 transactions: 1,000 for each of `ACCT-SYN-000001` through `ACCT-SYN-000006`.
- Rails covered: ACH, WIRE, RTP, FEDNOW. Statuses: `PENDING`, `SETTLED`.
- Customer account ownership is both a matching signal (10 points) and a hard search constraint.

---

## 14. PII masking (applies to every output)

| Data | Mask format | Example |
| --- | --- | --- |
| Account ID | Keep the last 4 characters | `ACCT-SYN-****0003` |
| Email | First character, then `***`, domain kept | `j***@example.com` |
| Phone | Keep the last 4 digits | `***-***-1234` |
| Names and other PII | Include only when needed for the customer to identify the payment | |

Never write unmasked account IDs, emails, or phone numbers to logs, messages, or audit records.

---

## 15. Decision output schema

```json
{
  "outcome_code": "REMEDY_AVAILABLE",
  "rule_id": "ACH-01",
  "category": "UNAUTHORISED",
  "rail": "ACH",
  "matched_payment_id": "TXN-000123",
  "match_score": 92,
  "candidates": [{"payment_id": "TXN-000123", "score": 92}],
  "message_type": "AC_RETURN",
  "reason_code": "SYN_R10",
  "deadline_at": "2026-12-17T17:00:00-05:00",
  "deadline_expired": false,
  "recovery_guaranteed": false,
  "ask_customer_confirmation": true,
  "request_created": false,
  "track_a": {
    "applicable": true,
    "notice_timely": true,
    "investigation_due": "2026-11-02",
    "provisional_credit_due_by": "2026-11-02",
    "extended_due": "2026-12-02"
  },
  "explanation": "I can prepare a AC_RETURN for this payment. This is a request only and does not guarantee recovery. Do you want me to proceed?",
  "audit": {"evaluated_at": "2026-10-19T10:00:00-04:00", "customer_account": "ACCT-SYN-****0003"}
}
```

Invariants (assert in code):

- `recovery_guaranteed` is always `false`.
- If `outcome_code != REMEDY_AVAILABLE`, then `ask_customer_confirmation == false`, except `CLARIFY_AMBIGUOUS`.
- If `outcome_code` is `NO_MATCH`, `CLARIFY_AMBIGUOUS`, `ESCALATE_SCAM`, `NO_REMEDY`, `ESCALATE_EXPIRED`, `AWAIT_DOCUMENT`, `BLOCK_DUPLICATE`, or `HOLD_FOR_HUMAN_REVIEW`, then `request_created == false` and `message_type == "none"`.
- `NO_MATCH` carries no category, remedy, deadline, or request fields.
- No unmasked account ID, email, or phone appears anywhere in the output.

---

## 16. Required unit tests (one per case)

Assume `now` is injected and Fed holidays are configured.

| # | Scenario | Expected outcome |
| --- | --- | --- |
| 1 | ACH debit, unauthorised, settled 10 days ago, signed statement received | `REMEDY_AVAILABLE`, `AC_RETURN`, `SYN_R10`, Track A applicable |
| 2 | Same as 1 but 61 days ago | `ESCALATE_EXPIRED` |
| 3 | Same as 1 without signed statement | `AWAIT_DOCUMENT` |
| 4 | ACH erroneous, settled 3 banking days ago | `REMEDY_AVAILABLE`, `SYN_R02` |
| 5 | ACH erroneous, settled 6 banking days ago | `ESCALATE_EXPIRED` |
| 6 | Wire, domestic, erroneous, settled today | `REMEDY_AVAILABLE`, `wire_recall_request`, Track A not applicable |
| 7 | Wire, domestic, settled 2 days ago | `ESCALATE_EXPIRED` |
| 8 | Wire, authorised-but-scammed, within 1 day | `ESCALATE_SCAM`, priority `URGENT`, no request |
| 9 | RTP, pending, unauthorised | `REMEDY_AVAILABLE`, `rtp_return_request` |
| 10 | RTP, settled, flag false | `NO_REMEDY`, direct explanation, no promise |
| 11 | FedNow, settled, flag true, within 1 day | `REMEDY_AVAILABLE` with no-promise text |
| 12 | Any rail, authorised-but-scammed | `ESCALATE_SCAM`, `message_type == "none"` |
| 13 | Two payments scoring 88 and 79 | `CLARIFY_AMBIGUOUS`, no request |
| 14 | Best candidate scores 55 | `NO_MATCH`, no category or deadline fields |
| 15 | "Around 1000" with a 1,450 payment | Candidate included via range 500 to 1999 |
| 16 | Beneficiary described by trading name | Beneficiary score 25 |
| 17 | Open request already exists for the payment | `BLOCK_DUPLICATE` |
| 18 | Agent approved but `agent_review_confirmed == false` | `HOLD_FOR_HUMAN_REVIEW` |
| 19 | Reg E notice 70 days after statement | Track A `MANUAL_REVIEW_LATE_NOTICE`, Track B unaffected |
| 20 | New account (age under 30 days), unauthorised RTP | `extended_due` is 90 days from `claim_date` |
| 21 | Transcript not confirmed | `STOP_UNCONFIRMED_TRANSCRIPT`, nothing else evaluated |
| 22 | Output contains an unmasked account ID | Test fails |

---

## 17. Extensions (not in the base rulebook)

These are additions that mirror real-world consumer-payment practice. Each is controlled by a feature flag so the base behavior can be restored.

| ID | Extension | Flag |
| --- | --- | --- |
| E-01 | `PENDING` payments are cancelled or stopped instead of returned or recalled | `ENABLE_PENDING_CANCEL` |
| E-02 | ACH unauthorised debits require a signed statement before a return request | `ENABLE_ACH_DOCUMENT_PRECONDITION` |
| E-03 | International consumer wires go to manual review | `ENABLE_INTL_WIRE_MANUAL_REVIEW` |
| E-04 | Track A (Reg E clock) reported alongside Track B | always on |
| E-05 | Banking-day vs calendar-day deadlines | always on |

Before presenting to the client, verify window lengths and Reg E timeframes against current Nacha, Fedwire, RTP, FedNow, and Regulation E sources, and label the `SYN_*` codes as placeholders.