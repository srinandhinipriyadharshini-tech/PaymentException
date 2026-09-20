# UC-02 Core Payment Exceptions & Automated Dispute Portal
## 7-slide presentation script and content outline

### Positioning statement

**UC-02 turns an ambiguous payment-dispute conversation into a controlled, auditable decision path.** Probabilistic AI accelerates understanding and search. Deterministic banking rules retain final authority.

This demo is an offline synthetic prototype. It demonstrates the operating model without contacting real banks, payment networks, or notification providers.

---

## Slide 1: The Core Payments Problem

### Visual layout and graphic suggestions

Use a high-contrast split screen:

- Left: four rail tiles: ACH, WIRE, RTP, FEDNOW.
- Under each tile, show a different visual policy marker: return review, investigation, finality, pending/finality.
- Right: a chat bubble containing: **“About 8k to the plumber last Tuesday.”**
- Between the two sides, show a broken search path: free text -> spreadsheets -> account history -> rail policy -> deadline.
- Add a small metric strip: **4 rails | 60-day control window | 6,000 synthetic payments | human approval required**.

### Key bullets for the slide

- Payment exceptions are not one workflow; they are rail-specific decisions.
- ACH and WIRE may support a recovery request, subject to category and deadline.
- RTP and FEDNOW are final instant rails in this synthetic rulebook.
- Customers describe events naturally; payment systems store structured records.
- “About 8k to the plumber” is meaningful to a human, but not directly searchable in a payment ledger.
- Manual investigation spends time finding the payment before anyone can decide the remedy.

### Speaker notes

“Every dispute starts as a story, not a database query. A customer does not say, ‘select payment ID PMT-SYN-004998 where rail equals WIRE.’ They say, ‘about eight thousand to the plumber last Tuesday.’ Meanwhile, the institution has four rails, different recovery rules, strict time windows, and different finality behavior. The operational problem is the translation layer: how do we move from an uncertain human narrative to a defensible, policy-controlled action without losing the customer’s context?”

“UC-02 is designed around that translation problem. It does not pretend that every payment has the same remedy. It first identifies the payment, then applies the rulebook for that payment.”

---

## Slide 2: The Architecture Strategy
### Deterministic Compliance Core vs. Probabilistic AI Analysis

### Visual layout and graphic suggestions

Use a two-lane architecture diagram:

**Lane 1: Probabilistic analysis**

- IntakeAI
- MatchingAI
- ClassificationAI
- DraftingAI
- Confidence, citations, reasoning, abstention

**Lane 2: deterministic control plane**

- Payment ledger and rail rules
- Deadline calculation
- Ambiguity and confidence gates
- PII redaction
- Human approval
- Trace and audit ledger

Place a bold lock icon between the lanes: **AI recommends; policy decides.**

### Key bullets for the slide

- AI extracts facts, ranks candidates, classifies intent, and drafts communication.
- The deterministic core owns payment selection, rail finality, deadlines, remedies, and submission gates.
- Step 5–6: rail rules and deadline controls are write-locked business policy.
- Step 8: PII masking is applied before generated customer and inter-bank outputs leave the workflow.
- No prompt can grant a remedy to an RTP/FEDNOW payment or bypass an expired deadline.
- Ambiguity produces clarification or escalation; it never becomes a silent selection.
- Every decision can be traced through facts, evidence, rules, and operator action.

### Speaker notes

“This is the most important architectural choice in the system. We use AI where language is uncertain and rules where compliance must be exact. IntakeAI can interpret ‘plumber’ as a beneficiary clue. MatchingAI can rank likely records. ClassificationAI can identify an erroneous, unauthorised, authorised-scam, or no-remedy claim. But none of those layers can rewrite the rulebook.”

“In the intended UC-02 control sequence, Step 5 and Step 6 apply rail and deadline policy. Step 8 masks synthetic account and payment identifiers from generated outputs. The result is an AI-assisted workflow with deterministic enforcement, not an AI system pretending to be a bank policy engine.”

---

## Slide 3: IntakeAI & MatchingAI in Action

### Visual layout and graphic suggestions

Use a three-stage horizontal flow:

1. **Customer narrative**
   - “I sent around eight thousand to the plumber last Tuesday.”
2. **Structured facts**
   - Amount: approximately 8,000
   - Beneficiary clue: plumber
   - Relative date: last Tuesday
   - Reason: not invented if absent
3. **Candidate evidence**
   - John Doe Plumbing LLC
   - USD 7,950
   - Match confidence and match reasons

Add a small dark terminal-style inset titled **AI cognitive routing / reasoning trace**.

### Key bullets for the slide

- IntakeAI extracts only searchable facts and preserves uncertainty.
- Approximate values become ranges rather than false exactness.
- MatchingAI ranks candidates using amount, date, beneficiary, rail, and account context.
- Fuzzy customer language is mapped to official registered or trading names.
- Candidate evidence is visible: amount, date, beneficiary, and confidence.
- Low confidence or close candidates trigger abstention and clarification.
- The system can show an inner-monologue-style trace as an operator explanation, not as a compliance authority.

### Speaker notes

“Here the AI is doing the work it is good at: turning natural language into search signals. ‘Around eight thousand’ becomes an amount range. ‘The plumber’ becomes a beneficiary clue. The system then ranks official records such as John Doe Plumbing LLC and explains why the candidate surfaced.”

“The crucial behavior is what happens when the evidence is weak. If two Northwind payments are equally plausible, the system does not guess. It asks the customer to choose. That abstention behavior is a feature: it protects the customer and the institution from a confidently wrong payment match.”

---

## Slide 4: The 60-Day SLA Rule & No-Remedy Finality

### Visual layout and graphic suggestions

Use a large horizontal timeline:

- Day 0: payment settled
- Day 30: erroneous-payment synthetic deadline
- Day 60: unauthorised/scam-payment synthetic deadline
- Day 61+: automatic request blocked

Above the timeline, show two diverging paths:

- **Inside window** -> Simulated Request Raised -> request ID -> no guaranteed recovery
- **Past window** -> Manual Review / no late automatic request

Add a separate red rail-finality card:

- RTP / FEDNOW -> No-Remedy

### Key bullets for the slide

- Deadline is calculated from the payment value date and claim category.
- Erroneous claims use a synthetic 30-day deadline.
- Unauthorised and authorised-but-scammed claims use a synthetic 60-day deadline.
- An in-window ACH/WIRE case can create a simulated Interbank Request ID.
- The request is never presented as guaranteed recovery.
- Expired deadlines block automatic late requests and route the case to manual review.
- RTP and FEDNOW are no-remedy under the synthetic instant-rail finality rule.

### Speaker notes

“This is where the product stops being a chatbot and becomes an operations control. The clock is calculated from the payment date, not from when the customer happens to open the portal. Category matters: erroneous claims use one synthetic window, while unauthorised and authorised-scam claims use another.”

“For an in-window ACH or WIRE claim, the operator can approve a simulated request and the system displays a request ID with an explicit no-guaranteed-recovery disclaimer. Once the deadline has passed, the product does not hide the outcome or raise a late request automatically. It routes the case to manual review. For final instant rails, the no-remedy result is rail-driven.”

---

## Slide 5: The Time-Travel Regulatory Sandbox
### Wow Factor 1

### Visual layout and graphic suggestions

Make the SLA slider the hero element:

- Green zone: 10–45 days, **Automatic path**
- Amber zone: 46–60 days, **Analyst attention**
- Red zone: over 60 days, **No-remedy active**

Show the same selected case card changing live as the slider moves. Include:

- Countdown label
- Case state badge
- Request eligibility
- Color shift and red pulse at expiry

### Key bullets for the slide

- The operator can simulate transaction age from 10 to 70 days.
- Every card, metric, status, and recommendation responds to the same policy clock.
- Green means the request path is available.
- Amber means the case is approaching the deadline and needs attention.
- Red means the deadline is exceeded or the rail is final.
- This is a test harness for policy behavior, not a cosmetic animation.
- It lets teams validate compliance outcomes before changing production rules.

### Speaker notes

“This is our time-travel sandbox. I can move the same case through its lifecycle without editing data or restarting the application. At day 18, the case is inside the safe window. Near day 60, the interface turns amber and focuses the operator’s attention. Past day 60, the automatic request path is blocked and the state turns red.”

“The point is not the color. The point is that the UI is exposing the consequence of a deterministic policy decision in real time. Product, operations, compliance, and QA can all use this control to test what the customer and operator will see at every point in the case lifecycle.”

---

## Slide 6: Agentic Smart Audit Summary
### Wow Factor 2

### Visual layout and graphic suggestions

Use a prominent audit card with three connected agent nodes:

- Match agent: evidence and candidate confidence
- Policy agent: rail and deadline checks
- Risk agent: behavioral context and review signals

The center of the card should show:

- Risk score badge
- Behavioral flag
- System recommendation
- **Human approval required** seal

Put a visible boundary around the card: **Pre-audit context, not autonomous submission.**

### Key bullets for the slide

- The audit layer pre-computes decision context before the operator opens the case.
- Match, policy, and risk checks are shown as separate evidence paths.
- Risk scores prioritize review; they do not make a final fraud determination.
- Behavioral flags provide context such as prior dispute history or device change.
- The recommendation is explicit: approve, hold, clarify, or preserve evidence.
- Human approval remains mandatory before a simulated recovery request.
- The audit result is designed to be explainable and traceable.

### Speaker notes

“This is the agentic layer, but notice what it does not do. It does not submit a payment request by itself. It prepares the operator. The match agent explains the candidate. The policy agent checks the deadline and rail. The risk agent adds behavioral context. Together they produce a compact pre-audit verdict.”

“A low risk score is not a declaration that fraud did not happen. It is a prioritization signal. The operator still sees the evidence, the recommendation, and the recovery disclaimer, then makes the approval decision. This is how we get the speed of agentic workflows without confusing recommendation with authorization.”

---

## Slide 7: Business Impact & Definition of Done

### Visual layout and graphic suggestions

Use a four-quadrant impact scorecard:

1. **Speed**: searchable facts and ranked candidates
2. **Control**: deterministic rail/deadline gates
3. **Quality**: abstention and clarification instead of wrong matches
4. **Trust**: explainable audit, redaction, and no-guaranteed-recovery language

Add a small analytics panel showing:

- AI initial classification vs human overrides
- Auto-resolved vs escalated vs no-remedy trend
- Matched-case rate
- Clarification/abstention rate

End with a bold line: **Faster decisions. Fewer unsafe submissions. Better customer explanations.**

### Key bullets for the slide

- Reduce manual search effort by extracting facts and ranking candidates automatically.
- Prevent unsafe submissions with deterministic policy gates.
- Reduce false matches through confidence thresholds, ambiguity bands, and abstention.
- Improve operator consistency with cognitive routing and Smart Audit context.
- Track matched cases, clarification/abstention rate, classification overrides, and triage volatility.
- Definition of done: every supported scenario has an expected state, remedy, explanation, and audit path.
- Production next step: connect approved speech, notification, identity, and payment-provider services behind the same control plane.

### Speaker notes

“The business outcome is not simply a faster chatbot. It is a more controlled exception operation. The system reduces the search burden, makes the policy decision visible, and blocks unsafe automation when evidence or eligibility is insufficient.”

“Our measurable definition of done is scenario-based. For every category and rail, we can state the expected payment match, deadline, remedy, status, customer message, and audit event. We measure matched-case rate and clarification rate, then track where humans override the initial classification and where triage volatility changes.”

“The final message is simple: UC-02 gives operations more speed without giving up control. AI handles ambiguity. Deterministic rules handle compliance. Humans retain accountability.”

---

# Optional 90-second closing

“UC-02 is a controlled bridge between customer language and payment operations. A customer can describe a dispute in one sentence. The system extracts only what it can support, ranks the right payment, applies the rail and deadline rulebook, redacts sensitive output, and prepares the operator with an auditable recommendation. When the evidence is weak, it asks. When the remedy is unavailable, it says so. When a request is eligible, a human approves it and the product makes no false promise about recovery. That is the operating model we are demonstrating: probabilistic understanding inside a deterministic compliance boundary.”

# Technical claims to keep precise

- The current demo is deterministic and offline; AI layers are represented by local adapters.
- `RTP` and `FEDNOW` are treated as final instant rails by the synthetic rulebook.
- Current notification and inter-bank actions are simulated; no external email or bank is contacted.
- The current evaluator reports matched cases and clarification/abstention rate; it does not claim production accuracy.
- The scenario fixture for validation is `data/uc02_test_scenarios.csv`.
