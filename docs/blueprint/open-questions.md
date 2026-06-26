# PART 19 — Open Questions & Founder Decisions Log

**Product:** Rekentafel  
**Last updated:** 2026-06-26  
**Purpose:** Consolidate unresolved items from the master product blueprint with options, tradeoffs, recommended defaults, and decision deadlines.

**Status key:** `OPEN` · `RECOMMENDED` (default until founder confirms) · `DECIDED` (fill when locked)

---

## Decision summary table

| # | Question | Recommended default | Decision by | Status |
|---|----------|---------------------|-------------|--------|
| Q1 | Product name | **Rekentafel** (consumer) + **TabSettle** (codename) | Before pilot marketing | RECOMMENDED |
| Q2 | MVP pricing model | **€0 / 90 days**, then **€59/mo Starter** | Pilot LOI signature | RECOMMENDED |
| Q3 | Payment facilitator role | **Pure SaaS on merchant Mollie (Model A)** | Before counsel memo | RECOMMENDED |
| Q4 | Geo/proximity check | **Waiter unlock only (MVP)**; geo optional V1.1 | Before pilot if hijack incidents | RECOMMENDED |
| Q5 | Refund policy | **Restaurant-mediated; platform audit log** | Pilot ops playbook | RECOMMENDED |
| Q6 | Tip distribution | **Pass-through to restaurant Mollie org; venue config** | Before pilot venue config | RECOMMENDED |
| Q7 | Service charge handling | **Separate line; proportional split; VAT per venue rule** | Pilot venue menu setup | RECOMMENDED |
| Q8 | Mollie account model | **Single restaurant org + OAuth (MVP)**; Connect V2 | Before scale (venue 10+) | RECOMMENDED |

---

## Q1 — Product name final selection

**Master prompt options:** TabSettle, SplitTable, Rekentafel, BillQR

### Options

| Option | Pros | Cons |
|--------|------|------|
| **Rekentafel** | NL-native; describes settlement moment; differentiates from ordering apps | Tourist pronunciation; harder global brand |
| TabSettle | Dev/investor friendly; clear English | Generic; US-centric for NL pilot |
| SplitTable | Obvious SEO for "split bill" | Commodity; trademark collision |
| BillQR | Mechanism-clear | Implies live bill on QR (security narrative conflict) |

### Weak assumption challenged

"English name required for fintech credibility" — **False for NL-first pilot.** Independent Amsterdam/Utrecht venues respond to Dutch hospitality language. Tourist UI can be EN while brand stays NL.

### Recommended default

| Use | Name |
|-----|------|
| Consumer brand, domain story | **Rekentafel** |
| Repo, packages, internal | **TabSettle** / `@rekentafel/*` |

### Risks if deferred

- Pilot QR stickers printed with wrong brand  
- Trademark search delayed → reprint cost  

### Action

- [ ] Benelux trademark screen classes 36/42 for Rekentafel  
- [ ] Register domain `rekentafel.nl` / app subdomain  
- [ ] Founder sign-off on consumer vs codename split  

**Reference:** [positioning.md](../product/positioning.md) § Product name candidates

---

## Q2 — MVP pricing: flat SaaS vs per-transaction bps vs hybrid

**Master prompt:** Undecided among flat SaaS per venue, bps on GMV, hybrid.

### Options

| Model | Pilot fit | Revenue at 1 venue | Regulatory |
|-------|-----------|-------------------|------------|
| **Flat SaaS (€0 → €59/mo)** | Best — no "% of sales" objection | Low until 10 venues | Off-rail invoice; simplest |
| Pure bps (e.g. 25 bps) | Poor — €0.22/table on €86.40 | Misaligned with support cost | Needs Connect `routing[]` |
| **Hybrid (€49/mo + €0.10/checkout)** | V1.1 after metering proven | Aligns with busy venues | Connect review at scale |

### Weak assumption challenged

"Restaurants will accept bps because we process payments" — **Rejected for pilot.** NL independents compare to free Tikkie workaround. Bps before ROI proof kills conversations. Mollie already charges ~€0.32/iDEAL — stacking platform bps early is toxic.

### Recommended default

| Phase | Price |
|-------|-------|
| Pilot (venue 1–3) | **€0 / 90 days** |
| MVP paid (1–10) | **€59/mo Starter** |
| V1.1 (10–50) | **€49/mo + €0.10 per paid guest checkout** (500 included) |

Restaurant pays Mollie transaction fees directly in all phases.

### Risks

| Risk | Mitigation |
|------|------------|
| LTV negative at €59/mo slow venue | Hybrid at V1.1; cap support hours in Starter tier |
| Metering disputes | Idempotent webhook ledger before hybrid billing |

### Action

- [ ] Pilot LOI with €0 / 90 days + success criteria  
- [ ] Log Mollie cost per table session for unit economics  
- [ ] Revisit hybrid at venue **#10**  

**Reference:** [pricing-recommendation.md](../business/pricing-recommendation.md) · [pricing-options.md](../business/pricing-options.md) · [unit-economics.md](../business/unit-economics.md)

---

## Q3 — Payment facilitator vs pure SaaS on merchant Mollie account

**Master prompt:** Who legally acts as payment facilitator vs SaaS layer?

### Options

| Model | Platform receives guest funds? | License surface | MVP fit |
|-------|-------------------------------|-----------------|---------|
| **A — Pure SaaS (restaurant MoR)** | No — direct to restaurant Mollie org | Lowest | **Yes** |
| B — Marketplace with `routing[]` | Platform fee slice in-payment | Connect + AFM review | V2 |
| C — Platform MoR | Yes | Payment institution — **avoid** | No |

### Recommended default

**Model A for MVP:** Platform creates Mollie payments via **restaurant OAuth token**. Funds settle to restaurant balance → IBAN. Platform invoices SaaS fee separately (SEPA).

Contractual posture: software processor / technical agent — **not** merchant of record.

### Weak assumption challenged

"We need platform bps in-payment to monetize" — **False at pilot.** Off-rail SaaS avoids facilitator classification while proving PMF.

### Risks

| Risk | Mitigation |
|------|------------|
| AFM reclassification if funds touch platform account | Never route guest EUR to platform bank in MVP |
| Unauthorized refund liability | Refunds via restaurant token; manager RBAC |

### Action

- [ ] Counsel memo on Model A (questions 4–9 in [counsel-question-list.md](../compliance/counsel-question-list.md))  
- [ ] Restaurant DPA + terms: MoR = restaurant  
- [ ] Re-evaluate Model B before venue 10 if hybrid pricing ships  

**Reference:** [payment-architecture.md](../architecture/payments/payment-architecture.md) §1 · [risk-tiering.md](../compliance/risk-tiering.md)

---

## Q4 — Payment session: geo/proximity check vs waiter unlock only

**Master prompt:** Whether join requires geo/proximity or waiter unlock alone.

### Options

| Gate | Fraud reduction | UX friction | MVP cost |
|------|-----------------|-------------|----------|
| **Waiter unlock + session token + optional PIN** | Moderate | Low | **Shipped MVP** |
| Geo-fence (GPS) | Weak indoors; false negatives | High — permission prompt | Poor |
| WiFi SSID / BLE beacon | Stronger at table | Venue hardware setup | V1.1+ |
| QR rotation per session | Strong | Waiter must show new QR | Ops heavy |

### Weak assumption challenged

"Geo-fence stops bill hijacking" — **Weak alone.** GPS unreliable indoors; guests deny location. Waiter activation is the primary control; PIN adds social proof at table.

### Recommended default

| Phase | Policy |
|-------|--------|
| **MVP** | Waiter unlock + 15 min token TTL + optional 6-digit PIN |
| **V1.1** | Optional venue flag: IP velocity limits + WiFi hint (if venue provides SSID) |
| **Never rely on** | GPS geo-fence as sole gate |

### Risks if wrong

| Scenario | MVP response |
|----------|--------------|
| Remote join via leaked token | Waiter sees unknown nickname; override; shorten TTL |
| Pilot shows >5% foreign IP joins | Enable PIN mandatory + V1.1 heuristics early |

### Action

- [ ] Track `join_source_ip_country` in pilot metrics  
- [ ] Decision gate: if hijack incidents >2/week → mandatory PIN  

**Reference:** [flows-a-o.md](../flows/flows-a-o.md) Flow D · [threat-register.md](../security/threat-register.md)

---

## Q5 — Refund policy: platform-mediated vs restaurant-only vs split refund rules

**Master prompt:** Refund policy undecided.

### Options

| Policy | Pros | Cons |
|--------|------|------|
| **A — Restaurant initiates in Mollie; platform logs** | MoR alignment; simple MVP | Manager context-switch to Mollie dashboard |
| B — In-app partial refund | Better UX | Split refund math complex; needs rules engine extension |
| C — Platform ops initiates | Central control | Facilitator liability creep |

### Recommended default

**Policy A for MVP:**

1. Manager initiates refund in **Mollie dashboard** (full or partial payment refund).  
2. Manager logs refund in admin with `tr_*`, reason code, link to claim snapshot.  
3. Platform ops reconciles weekly; **no automated split-refund engine** until V1.1.  
4. Group bill dispute: waiter adjustment on **unpaid remainder** preferred over refunding settled guests.

### Split refund example (manual MVP)

Table €86,40 paid by 3 guests. Guest B disputes €21,60 charge:

- If table still open: waiter override claims; Guest B pays corrected amount.  
- If table closed: manager refunds Guest B `tr_xxx` in Mollie; remaining guests unchanged; ops documents.

### Risks

| Risk | Mitigation |
|------|------------|
| Partial group chargeback | Claim snapshot at payment time in audit log |
| Refund without bill adjustment | Admin requires reason; ops review queue |

### Action

- [ ] Publish refund SOP in [manual-ops-playbook.md](../integrations/manual-ops-playbook.md)  
- [ ] V1.1 ticket: in-app refund API wrapping Mollie refund endpoint  

**Reference:** [rules-spec.md](../domain/split-engine/rules-spec.md) refunds section · [counsel-question-list.md](../compliance/counsel-question-list.md) Q9

---

## Q6 — Tip distribution: pass-through to staff pool vs restaurant-controlled

**Master prompt:** Tip pass-through vs restaurant-controlled pool.

### Options

| Model | Guest UX | Restaurant ops | MVP |
|-------|----------|----------------|-----|
| **A — Pass-through in Mollie payment to restaurant org** | Simple — one checkout amount | Restaurant allocates tips internally (POS/payroll) | **Default** |
| B — Separate tip line to staff pool account | Transparent "to staff" | Requires split payout / second Mollie route | V2 Connect |
| C — Platform-held tip pool | — | **EMI/facilitator risk** | Never MVP |

### Recommended default

**Model A:** Tip is part of guest Mollie Payment metadata (`tip_cents`) to **restaurant org**. UI copy: "Tip goes to the restaurant; distribution per venue policy." Venue admin toggle: show/hide suggested tip presets (10%/15%/20%).

### Dutch norm note

**Fooi (voluntary tip)** vs **service charge (often mandatory, VAT-bearing)** must be **visually distinct** in UI — see Q7.

### Risks

| Risk | Mitigation |
|------|------------|
| Staff expect direct tip routing | Set pilot expectation in staff training |
| Tip taxed differently from service charge | Counsel Q23; separate line items |

### Action

- [ ] Venue config: tip presets on/off  
- [ ] Counsel confirm tip + service charge in single Mollie Payment (Q7, Q23)  

**Reference:** [payment-architecture.md](../architecture/payments/payment-architecture.md) · [counsel-question-list.md](../compliance/counsel-question-list.md) §5

---

## Q7 — Service charge and mandatory tip line under Dutch hospitality norms

**Master prompt:** Service charge / mandatory tip handling undecided.

### Options

| UI treatment | When to use |
|--------------|-------------|
| **Optional service charge % (venue config)** | Venue adds 10% auto to bill — common NL brasserie |
| Mandatory "service fee" label | Only if venue legally/policy mandates — show as **line item**, not tip |
| Voluntary tip (fooi) | Separate checkout step after claimed subtotal |

### Recommended default

| Element | MVP behavior |
|---------|--------------|
| Service charge | Bill line; % configurable in admin; **split proportionally** with claims ([rules-spec.md](../domain/split-engine/rules-spec.md)) |
| VAT on service charge | Follow venue rule (often 9% on hospitality service charge — **confirm with venue accountant**) |
| Voluntary tip | Separate UI step; **not** mixed into service charge line |
| "Mandatory tip" auto-gratuity | **Off by default**; if enabled, label "Service charge (mandatory)" not "Tip" |

### Weak assumption challenged

"Guests will tip on top of mandatory service charge" — **Venue-dependent.** UI must show both clearly to avoid double-pay backlash.

### Example (Table 12)

| Line | Amount |
|------|--------|
| Food/drink subtotal | €96,00 |
| Service charge 10% | €9,60 |
| Guest voluntary tip | Added at checkout only |

### Risks

| Risk | Mitigation |
|------|------------|
| VAT display non-compliance | Line-level VAT; disclaimer: platform display ≠ fiscal invoice |
| Guest confusion | [payment-trust-patterns.md](../ux/payment-trust-patterns.md) separate rows |

### Action

- [ ] Pilot venue accountant confirms VAT rates on service charge  
- [ ] Counsel Q21–Q23 before marketing copy final  

**Reference:** [worked-examples.md](../domain/split-engine/worked-examples.md) · [counsel-question-list.md](../compliance/counsel-question-list.md)

---

## Q8 — Single Mollie account per restaurant vs platform Connect/split model

**Master prompt:** Single Mollie account vs Connect.

### Options

| Model | Pilot | Scale (10+ venues) | Platform fee collection |
|-------|-------|--------------------|-------------------------|
| **Restaurant-owned org + OAuth** | **Yes** | Works but manual onboarding | Off-rail invoice |
| Mollie Connect for Platforms | Overkill | **Yes** | In-rail `routing[]` |
| Marketplace split | Legal review | V2 enterprise | bps at checkout |

### Recommended default

| Phase | Model |
|-------|-------|
| **MVP pilot** | Each restaurant creates/uses own Mollie org; platform stores encrypted OAuth refresh token |
| **V1.1** | Connect onboarding wizard in admin (still restaurant org owner) |
| **V2** | Optional platform `routing[]` fee when hybrid pricing enabled |

### Weak assumption challenged

"Connect required day one" — **False.** Pilot is 1 venue; manual Mollie setup acceptable. Connect adds KYC UX and facilitator review before PMF.

### Risks

| Risk | Mitigation |
|------|------------|
| Token compromise | Encrypt at rest; rotate; minimal OAuth scopes |
| Restaurant churns Mollie password | Re-auth banner in admin |
| Platform fee evasion at scale | Move to Connect routing when hybrid billing ships |

### Action

- [ ] Document Mollie OAuth scopes: `payments.write`, `payments.read`, `refunds.write`  
- [ ] Admin UI: connection health indicator  
- [ ] Decision gate at venue **#10**: Connect mandatory for new signups  

**Reference:** [mollie-capabilities.md](../architecture/payments/mollie-capabilities.md) · [payment-architecture.md](../architecture/payments/payment-architecture.md)

---

## Additional open items (from blueprint, lower priority)

| Item | Recommended default | Phase |
|------|---------------------|-------|
| Guest account required? | No — nickname only MVP | MVP |
| Session token TTL | 15 min; refresh on waiter action | MVP |
| Max joins per session | 12 default | MVP |
| PII retention | 90 days post-close; payments 7y pseudonymized | MVP |
| Crypto | Exclude entirely | V2+ eval |
| Overpay-to-rewards | Never as stored balance | Never |
| POS integration | Manual/CSV MVP | V1.1 read-only |
| Coalition loyalty | Never early | V2+ |

**Reference:** [scope-boundary.md](../product/scope-boundary.md) · [mvp-roadmap.md](../product/mvp-roadmap.md)

---

## Decision log (fill as founder confirms)

| Date | Question | Decision | Owner | Notes |
|------|----------|----------|-------|-------|
| — | Q1 Name | | Founder | |
| — | Q2 Pricing | | Founder | |
| — | Q3 Facilitator | | Counsel | |
| — | Q4 Geo | | Founder + Eng | |
| — | Q5 Refunds | | Founder + Ops | |
| — | Q6 Tips | | Founder + Pilot venue | |
| — | Q7 Service charge | | Pilot venue accountant | |
| — | Q8 Mollie model | | Founder + Eng | |

---

## Pre-pilot decision checklist (recommended order)

1. **Q1** Name — blocks QR print and domain  
2. **Q3** Model A legal memo — blocks terms of service  
3. **Q8** Mollie OAuth pilot setup — blocks test payment  
4. **Q7** Service charge + VAT — blocks menu config  
5. **Q6** Tip copy — blocks guest checkout UI  
6. **Q2** Pilot LOI pricing — blocks venue contract  
7. **Q5** Refund SOP — blocks ops runbook  
8. **Q4** PIN policy — can default off; revisit week 2 of pilot  

---

*Slice ownership: PART 19 — Open Questions & Founder Decisions Log. Resolves master prompt open questions with recommended defaults.*
