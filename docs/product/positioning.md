# PART 1 — Product Reframe & Positioning

**Slice:** Product Reframe and Competitive Positioning  
**Market:** Netherlands-first hospitality fintech  
**Last updated:** 2026-06-26  
**Status:** Working draft for MVP pilot

---

## Executive summary

Rekentafel is a **waiter-controlled, table QR split-pay platform** for Dutch restaurants. Each table has a persistent QR code. Before service, scanning shows menu and lightweight server-call signals — **not phone ordering**. After the waiter opens a table session and the bill exists, the same QR unlocks a short-lived collaborative payment experience where guests claim items, split fairly, tip individually, and pay via Mollie (iDEAL, cards, wallets).

**This product is NOT phone ordering.** Waiters remain the order-taking authority. We remove end-of-meal payment friction — the "one person pays, everyone sends a Tikkie later" ritual — without replacing front-of-house workflow.

---

## Product name candidates

| Name | Meaning / signal | Strengths | Weaknesses | Domain / trademark risk |
|------|------------------|-----------|------------|-------------------------|
| **Rekentafel** | Dutch: *rekening* (bill/check) + *tafel* (table) | Instantly legible to NL diners; category-defining locally; memorable story ("the settlement table") | Pronunciation barrier for tourists; harder international expansion without sub-brand | Moderate — check Benelux trademark classes 36/42 |
| **TabSettle** | English: tab + settle | Clear fintech positioning; investor-friendly; works in code/repos immediately | Generic; less emotional resonance in NL market; sounds US-centric | Higher — crowded "tab/settle" space |
| **SplitTable** | Descriptive English | Obvious value prop; SEO-friendly for "split bill" | Commodity naming; easily confused with competitors; weak brand moat | High collision risk |
| **BillQR** | Bill + QR code | Describes mechanism, not outcome | Sounds like bill presentment only; implies live bill on QR (security concern we explicitly avoid) | Descriptive, weak protectability |
| **TafelPay** | Dutch table + pay | Short, mobile-friendly; bilingual readability | Sounds like generic pay-at-table; doesn't convey split/collaboration | Moderate |
| **De Rekening** | Dutch: "the bill" | Culturally native; conversational ("shall we do De Rekening?") | Too generic for trademark; ambiguous product vs feature | Very high collision |

### Recommended working name: **Rekentafel**

**Rationale:**

1. **Netherlands-first fit:** The core pain is Dutch dining culture — one payer, fragmented Tikkie reconciliation, iDEAL as default rail. A Dutch-forward brand signals local payment and hospitality norms, not another US "tab app."
2. **Semantic precision:** The name describes the *moment* we own (settling the table bill together), not the QR mechanism (BillQR) or a generic split verb (SplitTable).
3. **Differentiation anchor:** Full QR ordering vendors brand around "order from your phone." Rekentafel brands around **pay together at the table** — a distinct category wedge.
4. **Pilot venue narrative:** Amsterdam/Utrecht/Rotterdam independents and small groups want a tool that respects *bediening* (table service), not disruption. "Rekentafel" communicates collaboration, not automation of waiters.
5. **Codename alias:** Use `TabSettle` as internal repo/package codename for developer ergonomics; consumer-facing NL brand is Rekentafel. Revisit unified global brand at V2 if expanding beyond Benelux.

**Challenge:** Tourist-heavy venues (Centrum Amsterdam) may need UI language toggle (NL/EN/DE) regardless of brand. Name pronunciation in staff training: *RAY-ken-tah-fel*.

---

## One-sentence pitch

**Rekentafel lets every guest at the table pay their fair share from one QR code — after the waiter opens the bill — without phone ordering or post-meal Tikkie chaos.**

---

## Problem statement

### Guest pain (quantified example)

A table of six at a Utrecht bistro. Total bill: **€186,40** incl. 9% VAT on food, 21% on wine, plus **€9,32** service charge.

| Today (Tikkie reconciliation) | Friction |
|------------------------------|----------|
| One person pays €186,40 on card | 3–8 min at terminal; front-of-house blocked |
| Payer creates Tikkie or sends bank requests | 5–15 min async; wrong amounts common |
| 2 guests forget; 1 disputes shared bottle split | Social friction; payer subsidizes |
| Waiter re-opens bill for correction | Ops delay; table turn suffers |

**Root cause:** Payment is **decoupled** from consumption. The bill exists in the POS/waiter's head, but settlement happens in messaging apps with no item-level truth.

### Restaurant pain

- **Table turn delay:** Last 10–20 minutes of occupancy often generate zero revenue but block the next seating.
- **Staff intervention load:** Waiters mediate "can you split this?" repeatedly with no tooling.
- **Chargeback exposure:** When one card pays group bill, disputes are opaque vs itemized guest payments.
- **No guest data without POS integration:** MVP accepts manual bill entry; still better than zero capture at payment moment.

### Market gap

| Alternative | Gap |
|-----------|-----|
| Tikkie / bank transfer | Post-hoc, no live bill truth, no item claims, no partial table pay |
| Full QR ordering (Orderli, etc.) | Changes service model; waiter disintermediation; higher onboarding |
| POS pay-at-table terminals | Hardware cost; poor multi-payer split UX; vendor lock-in |
| "Just add a payment link" | No session model; bill hijack risk; no split logic |

**Rekentafel** occupies the gap: **collaborative settlement on the existing open bill, waiter-gated, web-native, Mollie-native.**

---

## Target users

### 1. Guest (diner)

| Attribute | Detail |
|-----------|--------|
| Primary | NL residents, 25–45, iDEAL-comfortable, group diners 2–8 |
| Secondary | Tourists in EN/DE UI; business lunch pairs |
| Job to be done | Pay only what I consumed, quickly, without awkward math or chasing friends |
| MVP needs | No forced account; join via QR + short-lived session token; claim items; pay with iDEAL |
| Post-MVP | Optional account, visit history, loyalty accrual |

**Weak assumption challenged:** "Guests will create accounts for loyalty." At MVP, **guest conversion drops 40–60%** with mandatory signup (industry pattern). Account is opt-in after successful payment.

### 2. Waiter (front-of-house staff)

| Attribute | Detail |
|-----------|--------|
| Primary | Floor staff at independent restaurants, 20–80 covers |
| Job to be done | Close tables fast without becoming payment support; stay authoritative on orders |
| MVP needs | One-tap "open payment session"; see payment progress; override/split assist; close table |
| Failure mode | If activation flow >2 taps or unclear, staff will disable feature |

**Weak assumption challenged:** "Waiters want less guest interaction." They want **less payment admin**, not less service. UI must not bypass them for orders.

### 3. Restaurant owner / manager

| Attribute | Detail |
|-----------|--------|
| Primary | Owner-operator or GM at 1–3 NL venues, €500k–€2M revenue |
| Job to be done | Faster turns, fewer payment disputes, modern guest experience without POS rip-and-replace |
| MVP needs | Table/QR setup, menu upload, staff roles, Mollie connection, basic audit log |
| Buy trigger | Pilot ROI: 5–10 min saved per large table × Friday/Saturday volume |

**Pricing open question:** Flat SaaS (€49–€149/mo per venue) vs bps on GMV vs hybrid. MVP pilot likely **free + success metric** before pricing test.

### 4. Platform ops (internal)

| Attribute | Detail |
|-----------|--------|
| Role | Support, reconciliation, fraud review, onboarding |
| MVP needs | Webhook reconciliation dashboard, failed payment queue, manual refund initiation |
| Post-MVP | Chargeback automation, multi-venue analytics |

---

## Value propositions

### For restaurants

| Value | Mechanism | MVP? |
|-------|-----------|------|
| **Faster table turns** | Parallel guest payments vs sequential terminal | Yes |
| **No POS replacement** | Manual bill entry or CSV import; POS sync deferred | Yes |
| **Waiter authority preserved** | Payment session requires waiter activation | Yes |
| **Itemized payment audit trail** | Per-guest Mollie payments linked to claims | Yes |
| **Lower chargeback ambiguity** | Guest pays own items (future dispute scope narrower) | Yes |
| **Guest data & loyalty** | Opt-in accounts, visit history | Post-MVP |
| **Discovery / demand gen** | Restaurant feed, recommendations | Do not build yet |

**ROI sketch (pilot venue, conservative):**

- 40 tables, 1.2 turns/night, 25% tables use Rekentafel split
- 12 tables/night × 8 min saved = **96 staff-minutes/night**
- At €18/h loaded labor ≈ **€29/night** + improved guest satisfaction (unmeasured in MVP)

### For guests

| Value | Mechanism | MVP? |
|-------|-----------|------|
| **Pay your share, not someone else's** | Item claim + equal/custom/shared splits | Yes |
| **No app download** | Mobile web + iDEAL | Yes |
| **No post-meal Tikkie chase** | Pay at table before leaving | Yes |
| **Transparent VAT/service charge** | Display on bill breakdown | Yes |
| **Individual tip** | Per-guest tip line before Mollie checkout | Yes |
| **Rewards on overpay** | Platform credit / partner pool | Do not build yet (e-money risk) |

---

## Differentiation

### vs Tikkie (and generic bank-request reconciliation)

| Dimension | Tikkie post-meal | Rekentafel |
|-----------|------------------|------------|
| **Timing** | After leaving; async | At table; synchronous with meal end |
| **Bill truth** | Payer's memory/screenshot | Live bill from waiter-activated session |
| **Split model** | Fixed amount requests | Item claims, partial table participation, shared items |
| **Partial pay** | Awkward (new requests) | Native remaining balance tracking |
| **Waiter visibility** | None | Progress dashboard; close when settled |
| **Payment rail** | iDEAL via Tikkie | iDEAL/cards/wallets via Mollie |

**Concrete scenario:** Four colleagues, shared €32 wine bottle. With Tikkie, payer guesses €8 each. With Rekentafel, guests mark bottle as **shared 4-way** (€8,00 each ex tip) while one guest who had only salad claims only their €14,50 main.

**What we don't claim:** Tikkie is zero-cost and universal. Rekentafel requires restaurant adoption. Our wedge is **in-venue experience**, not P2P payments.

### vs full QR ordering systems (Orderli, Mr.Yum, Sunday-style order-from-phone)

| Dimension | Full QR ordering | Rekentafel |
|-----------|------------------|------------|
| **Order path** | Guest phone → kitchen | Waiter takes order (unchanged) |
| **Service model** | Staff as runners; upsell via app | Staff as hospitality; QR for menu/pay only |
| **Onboarding** | Menu sync, kitchen routing, training overhaul | Tables, QR print, payment session training |
| **Failure cost** | Wrong order from guest typo; kitchen chaos | Lower — no order submission |
| **Revenue story** | Order volume lift | Turn time + payment completion |

**Explicit positioning statement:**

> Rekentafel is **payment infrastructure for table service**, not **ordering infrastructure for counter service**. Restaurants that believe waiters differentiate the experience should not be forced into phone-ordering UX to get modern split payments.

**Weak assumption challenged:** "Restaurants want QR for everything." Many NL sit-down venues explicitly **reject** phone ordering as anti-social. We capture QR budget without cultural mismatch.

### vs POS pay-at-table (Zettle, Adyen terminal, integrated POS modules)

- Terminals excel at **single-card, single-amount** checkout.
- Multi-payer itemized splits on a terminal are UX-hostile (pass device, trust stranger, repeat).
- Rekentafel: **each guest on their own phone**, concurrent checkout, one settlement view for waiter.

POS integration is **post-MVP** — we don't compete on fiscal receipt printing day one.

---

## What this product is NOT (MVP boundary)

| Not in scope | Why deferred |
|--------------|--------------|
| Phone ordering | Waiter authority is core brand promise |
| Public live bill on raw QR scan | Session token + waiter activation prevents bill hijacking |
| Stored-value wallet / overpay-as-balance | EMI/e-money regulatory surface |
| Crypto payments | Separate regulated rail; not bundled in MVP |
| Coalition partner rewards marketplace | Two-sided marketplace complexity |
| Discovery / ML recommendations | Needs scale + GDPR profiling review |
| Deep POS bi-directional sync | Integration tax; manual bill entry for pilot |
| Native iOS/Android apps | Web-first; add native when retention proves |

---

## Positioning statement (internal)

**For** independent table-service restaurants in the Netherlands  
**who** lose time and guest goodwill to one-payer-plus-Tikkie settlement,  
**Rekentafel** is a table QR payment session platform  
**that** lets guests collaboratively split and pay the open bill via iDEAL  
**unlike** full QR ordering apps or post-meal Tikkie requests  
**because** it keeps waiters in control of ordering while making multi-payer checkout parallel, itemized, and auditable.

---

## Assumption challenges (this slice)

| Assumption | Verdict | Action |
|------------|---------|--------|
| "QR on table is enough to unlock bill" | **Reject** | Waiter-activated short-lived session token required |
| "Geo-fence stops bill hijacking" | **Weak alone** | Waiter unlock primary; geo optional signal only |
| "Guests want loyalty wallet" | **Unproven** | MVP: optional account post-payment |
| "Overpay-to-rewards drives revenue" | **Risky** | Reframe as marketing budget / discount codes, not e-money |
| "Restaurants will pay per-transaction bps" | **Uncertain** | Pilot flat SaaS; measure willingness after turn-time proof |
| "Manual bill entry is too friction" | **Acceptable for pilot** | One venue, waiter entry ≤2 min; POS sync V1.1 |

---

## Risks specific to positioning (legal, fraud, UX, ops)

### Legal / regulatory

| Risk | Detail | Mitigation in positioning |
|------|--------|---------------------------|
| PSD2 / EMI scope creep | Holding funds or issuing spendable balance → e-money | MVP: pass-through to merchant Mollie; no stored value |
| GDPR | Payment session ties device to visit | Minimal retention; no profiling in MVP; clear privacy copy |
| VAT display | Split checks must show correct 9%/21% breakdown | Position as compliance feature vs Tikkie guesswork |
| Payment facilitator role | Who is merchant of record? | Pure SaaS atop restaurant Mollie account for MVP |

### Fraud

| Risk | Detail |
|------|--------|
| Bill hijacking | Stranger scans QR, claims expensive items | Session token only after waiter activation; optional table PIN |
| Malicious partial pay | Guest pays small amount, leaves | Remaining balance visible; waiter blocks table close |
| Chargeback abuse | Guest pays, disputes card charge | Itemized audit; manual ops queue MVP |

### UX

| Risk | Detail |
|------|--------|
| Waiter forgets to activate payment mode | Guest sees menu-only; confusion | Staff training; prominent "ready to pay" guest signal |
| Split arguments at table | Shared bottle, unequal appetites | Shared-item UX + waiter override |
| iDEAL redirect drop-off | Guest abandons mid-flow | Retry; show countdown on session expiry |

### Ops

| Risk | Detail |
|------|--------|
| Mollie settlement T+1/T+2 vs cash expectations | Restaurant expects instant | Set expectations in onboarding |
| Manual bill entry errors | Wrong item/prices | Waiter review step before session open |
| Refund policy ambiguity | Split refund across guests | Restaurant-mediated MVP; document in admin |

---

## MVP vs post-MVP (positioning lens)

| Capability | MVP | Post-MVP |
|------------|-----|----------|
| Persistent table QR (menu + call server) | Yes | — |
| Waiter-activated payment session | Yes | — |
| Item/equal/custom/shared split + tips | Yes | — |
| Mollie iDEAL/cards/wallets | Yes | — |
| Optional guest account | Yes (light) | Full history |
| Loyalty accrual | No | V1.1 |
| POS sync | No | V1.1–V2 |
| Partner rewards / overpay wallet | No | V2+ (if legally cleared) |
| Crypto rail | No | Separate product decision |
| Discovery / recommendations | No | V2+ |

---

## Related artifacts

- [Competitive matrix](./competitive-matrix.md)
- [Elevator pitch](./elevator-pitch.md)
