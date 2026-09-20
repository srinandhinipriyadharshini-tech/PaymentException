# Payment Exceptions Rulebook

This document records the deterministic rules supplied for the synthetic payment-exception demo.

## 1. Rail Rules

`recovery_guaranteed` is always `FALSE`. A request is a request only; recovery is never promised.

| Rail | Category | Available | Message type | Reason code | Deadline | Recovery guaranteed |
| --- | --- | --- | --- | --- | ---: | --- |
| ACH | Unauthorised | TRUE | `AC_RETURN` | `SYN_R10` | 60 days | FALSE |
| ACH | Erroneous | TRUE | `AC_RETURN` | `SYN_R02` | 5 days | FALSE |
| WIRE | Unauthorised | TRUE | `wire_recall_request` | `SYN_W01` | 1 day | FALSE |
| WIRE | Erroneous | TRUE | `wire_recall_request` | `SYN_W01` | 1 day | FALSE |
| RTP | Any category except authorised-but-scammed, when configured and funds have not moved | TRUE | `rtp_return_request` | `SYN_rtp01` | 1 day | FALSE |
| FEDNOW | Any category except authorised-but-scammed, when configured and funds have not moved | TRUE | `fednow_return_request` | `SYN_fn01` | 1 day | FALSE |
| Any rail | No remedy | FALSE | `none` | `none` | None | FALSE |

### Rail behavior

- ACH unauthorised claims may use the configured return/investigation request within the 60-day deadline.
- ACH erroneous claims may use the configured return request within the 5-day deadline.
- WIRE claims use the configured recall request within the 1-day deadline.
- RTP and FEDNOW may prepare only the configured return/recovery request when permitted and funds have not moved.
- RTP/FEDNOW cases with moved funds must never promise recovery.
- If no configured remedy exists, no inter-bank request is created.

## 2. Deadline Rules

The deadline is calculated as:

```text
payment event date + configured deadline_days = deadline
```

When the deadline has passed:

- Do not submit the configured return or recall request.
- Explain plainly that the configured window has passed.
- Escalate for manual review and close the automatic flow.
- Do not ask the customer for confirmation of a request that cannot be submitted.

## 3. Claim Categories

### Unauthorised

The customer says they did not initiate, approve, or authorise the payment.

Examples:

- "I did not make this payment."
- "I never authorised this transaction."
- "Someone took money from my account."

### Erroneous

The customer made the payment but entered incorrect details or duplicated the payment.

Examples:

- Wrong amount
- Wrong beneficiary
- Wrong account details
- Duplicate payment

### Authorised but scammed

The customer sent or approved the payment but later reports that they were deceived or scammed.

Required behavior:

- Preserve the `AUTHORISED_BUT_SCAMMED` category.
- Escalate for manual review.
- Do not promise recovery.
- Do not automatically raise an inter-bank request.

### No remedy

No permitted remedy exists after considering the rail, payment status, funds moved, and deadline.

Required behavior:

- Do not create a request.
- Explain the limitation directly.
- Explain expiration when relevant.
- Do not hedge or imply that recovery is continuing when no remedy exists.

## 4. Matching and Ranking Rules

Candidate matching uses these facts:

- Amount range
- Date range or date similarity
- Beneficiary registered/trading name
- Customer account
- Rail when stated

### Ranking weights

| Signal | Weight |
| --- | ---: |
| Amount match | 40 points |
| Date similarity | 25 points |
| Beneficiary name match | 25 points |
| Customer account match | 10 points |
| **Total** | **100 points** |

Additional matching rules:

- Approximate amounts must be searched as ranges, not exact points.
- For `around 1000`, the configured search range is `500` through `1999`.
- Prefer the customer account match when several accounts have similar payments.
- The beneficiary may be described by a trading name rather than its registered legal name.
- Never silently select between two similarly ranked candidates.
- When candidates are ambiguous, ask the customer to clarify.
- A clarification result must not create or submit a request.
- If there is no matching payment, do not classify, create a remedy, calculate a request deadline, or create a request.

## 5. Hard Rails and Guardrails

| Condition | Required behavior |
| --- | --- |
| No matching payment | No classification, remedy, deadline, or request |
| Ambiguous payment | No automatic selection or submission; ask for clarification |
| No remedy | No inter-bank request; explain the rule limitation directly |
| Expired deadline | No submission; explain the configured window passed; escalate/close |
| RTP/FEDNOW with funds moved | Never promise recovery |
| Unconfirmed agent review | Do not submit or bypass human review |
| Unconfirmed transcript | Do not begin claim processing |
| Any output | Mask account IDs, email addresses, phone numbers, and unnecessary PII |

## 6. Customer Conversation Rules

- Ask for customer confirmation only when a matched payment has an available remedy and the deadline is still open.
- For no-remedy, expired, final-rail, or authorised-scam cases, explain the outcome directly and do not ask for confirmation.
- An agent recommendation does not bypass the policy gate.
- Customer confirmation may lead to a simulated request only when all rail, deadline, account, and human-review rules permit it.
- A simulated request is never a guarantee of recovery.

## 7. Admin Rules

- Admin can view active and non-active cases with their status.
- Admin approval is allowed only for escalated/manual-review cases.
- Admin must not approve cases already approved by the agent.
- Admin approval triggers the simulated customer email.
- No-remedy cases may be closed as no remedy.
- Agent-approved cases remain visible but do not require another admin approval.

## 8. Data Ownership

- The test database contains 6,000 transactions.
- There are 1,000 transactions for each of the six customer accounts:
  - `ACCT-SYN-000001`
  - `ACCT-SYN-000002`
  - `ACCT-SYN-000003`
  - `ACCT-SYN-000004`
  - `ACCT-SYN-000005`
  - `ACCT-SYN-000006`
- The dataset covers ACH, WIRE, RTP, and FEDNOW.
- The dataset includes both `PENDING` and `SETTLED` statuses.
- Customer account ownership is a matching signal and a search constraint.
