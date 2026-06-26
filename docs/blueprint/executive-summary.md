# PART 19 — Executive Product Summary

**Product (working name):** Rekentafel  
**Codename (engineering):** TabSettle  
**Market:** Netherlands-first hospitality fintech  
**Slice:** Executive Summary and Master PRD Compilation  
**Last updated:** 2026-06-26  
**Read time:** ~4 minutes

---

## What we are building

Rekentafel is a **waiter-controlled, table QR split-pay platform** for Dutch table-service restaurants. Each table has a **persistent QR code**. Before service, scanning shows the menu and lightweight server-call signals — **not phone ordering**. After the waiter opens a payment session, the same QR unlocks a **short-lived collaborative payment experience**: guests join, claim items or split equally/custom/shared, tip individually, and pay via **Mollie** (iDEAL, cards, wallets).

**One-sentence pitch:** Rekentafel lets every guest at the table pay their fair share from one QR code — after the waiter opens the bill — without phone ordering or post-meal Tikkie chaos.

---

## The problem (concrete)

| Today | Cost |
|-------|------|
| One guest pays the full bill on card | 3–8 min at terminal; table blocked |
| Payer sends Tikkies or bank requests | 5–15 min async; wrong amounts common |
| Shared items (wine, platters) disputed | Social friction; payer subsidizes |
| Waiter re-opens bill for corrections | Ops delay; slower table turns |

**Example:** Table of six, bill **€186,40** incl. mixed 9%/21% VAT + service charge. One payer fronts the card; five friends reconcile later in WhatsApp. The restaurant loses the last **10–20 minutes** of occupancy with zero incremental revenue.

**Root cause:** Payment is decoupled from consumption. The bill exists in POS or the waiter's hand, but settlement happens in messaging apps with no item-level truth.

---

## The wedge (what we are NOT)

| We are | We are NOT |
|--------|------------|
| Payment infrastructure for table service | Full QR phone ordering (Orderli-style) |
| Waiter-gated bill visibility | Public live bill on naked QR scan |
| Mollie-native split settlements | Crypto checkout (MVP) |
| Web-first mobile experience | Native iOS/Android apps (MVP) |
| SaaS on restaurant Mollie account | Stored-value wallet / dining credit |

**Category statement:** Rekentafel owns **collaborative settlement on the existing open bill**. Full QR ordering vendors own **order-from-phone**. POS terminals own **single-card checkout**. Tikkie owns **post-meal P2P reconciliation**.

---

## MVP definition (single NL pilot)

**Goal:** Prove **trustworthy bill visibility + collaborative split-pay** at **one pilot venue** — not loyalty, discovery, crypto, or POS sync.

### Primary outcome

Guests join a **waiter-activated payment session**, claim or split items, tip individually, pay via Mollie, while the restaurant sees a reconciled **remaining balance** until the table closes.

### Quantitative targets (8-week pilot)

| Metric | Target |
|--------|--------|
| Tables using payment mode (bill >€30) | ≥40% of eligible tables |
| Split-pay completion (remaining → €0) | ≥85% of activated sessions |
| Median pay-phase duration (activate → close) | ≤12 minutes |
| Claim dispute rate (waiter override) | ≤8% of sessions |
| Failed checkout retry success | ≥90% |

### MVP example session

**Table 12, 4 guests — worked total €105,60**

| Line | Amount |
|------|--------|
| 2× Burger @ €14,50 (9% VAT) | €29,00 |
| 1× Steak @ €28,00 (9% VAT) | €28,00 |
| 1× House wine (21% VAT) | €32,00 |
| 2× Cola @ €3,50 (9% VAT) | €7,00 |
| Service charge 10% | €9,60 |

- Guest A: 1 burger + 1 cola → pays ~€21,50 incl. tip via iDEAL  
- Guest B: steak + half wine (shared) → ~€42,00 + tip  
- Guests C & D: equal-split remainder → ~€30,10 each  
- Waiter closes when **remaining = €0,00**

---

## Core flow (MVP spine)

```
Guest scans persistent table QR
    │
    ├─ EMPTY / SEATED ──► Menu + "Call server" ONLY (no bill, no pay)
    │
    └─ Waiter activates PAYMENT + session token
              │
              ▼
        Guest joins ──► Claim/split ──► Mollie checkout ──► Partial OK
              │
              └─ Remaining €0 OR waiter force-close ──► CLOSED (audit frozen)
```

**Security invariant:** Scanning the table QR **never** exposes line items without a **waiter-activated payment session token** (TTL ~15 min, refreshable). Optional 6-digit table PIN for join.

---

## Product surfaces (MVP)

| Surface | Users | MVP |
|---------|-------|-----|
| Guest web | Diners | Yes — `/t/:slug/:tableCode` |
| Staff panel | Waiters | Yes — floor, bill entry, payment monitor |
| Restaurant admin | Owner/GM | Yes — tables, menu, Mollie, roles |
| Platform ops | Internal | Yes — webhooks, audit, reconciliation |
| Partner rewards | Brand admins | **No** — post-MVP only |

---

## Payment architecture (MVP)

| Decision | Choice |
|----------|--------|
| PSP | Mollie only |
| Account model | **Restaurant-owned Mollie org**; platform OAuth agent |
| Platform role | Pure SaaS — not merchant of record, no guest fund holding |
| Checkout unit | **One Mollie Payment per guest checkout** |
| Table settlement | Application-layer aggregation of partial payments |
| Crypto | **Excluded** — separate regulated rail at V2+ ([crypto-rail-design.md](../architecture/payments/crypto-rail-design.md)) |

---

## Post-MVP (explicit deferrals)

| Phase | Theme | Examples |
|-------|-------|----------|
| **V1.1** | Ops efficiency, 3–10 venues | Guest accounts, POS read-only import, payout reporting, optional geo gate |
| **V2** | Scale + retention | Mollie Connect platform fees, venue loyalty points, bi-directional POS (selected vendors) |
| **Never (now)** | Regulatory / scope traps | Crypto MVP, coalition marketplace, discovery feed, stored-value wallet, full QR ordering, native apps, franchise BI |

Full deferral rationale: [scope-boundary.md](../product/scope-boundary.md).

---

## Business model (pilot default)

| Horizon | Model | Price |
|---------|-------|-------|
| Pilot (venue 1–3) | Flat SaaS | **€0 for 90 days** |
| MVP paid (1–10 venues) | Flat SaaS | **€59/mo Starter** |
| V1.1 (10–50) | Hybrid | **€49/mo + €0,10 per paid guest checkout** |

Detail: [pricing-recommendation.md](../business/pricing-recommendation.md).

---

## Team and delivery

| Workstream | Owner | Scope |
|------------|-------|-------|
| **ws-1** | Guest web | QR landing, join, claim/split, Mollie return UX |
| **ws-2** | Staff/admin | Floor console, bill entry, payment activation, venue config |
| **ws-3** | Backend/payments | API, split engine, Mollie, webhooks, contracts, DB |
| **ws-4** | Design/DevOps | ui-core, CI, infra (supports all) |

**Timeline:** 6 calendar weeks to pilot-deployable (2 weeks Phase 0 contracts + 4 weeks MVP sprints + integration window). See [implementation-roadmap.md](../engineering/implementation-roadmap.md).

---

## Top risks (this product)

| Category | Risk | MVP mitigation |
|----------|------|----------------|
| **Legal** | PSD2/EMI scope creep if platform holds funds | Pass-through to merchant Mollie; no stored value |
| **Fraud** | Bill hijacking via shared QR photo | Waiter token + optional PIN; no public bill |
| **Technical** | Concurrent claim double-allocation | Optimistic locking + waiter override |
| **Compliance** | VAT display errors on splits | Line-level VAT; explicit rounding rules |
| **UX** | Waiter forgets payment activation | Training; guest "request bill" signal (disabled until session) |
| **Ops** | Mollie settlement T+1/T+2 vs cash expectations | Onboarding copy; payout view V1.1 |

---

## Open founder decisions

Eight unresolved items (product name, pricing enforcement, facilitator role, geo check, refunds, tips, service charge, Mollie account model) are consolidated with recommended defaults in [open-questions.md](./open-questions.md).

**Recommended consumer brand:** Rekentafel (NL-first). **Recommended engineering codename:** TabSettle.

---

## Document map (where detail lives)

| Topic | Document |
|-------|----------|
| Full PRD + MVP requirements | [prd.md](./prd.md) |
| User stories by workstream | [user-stories.md](./user-stories.md) |
| Architecture index | [system-architecture-overview.md](./system-architecture-overview.md) |
| Positioning & competition | [positioning.md](../product/positioning.md) |
| Flows A–O | [flows-a-o.md](../flows/flows-a-o.md) |
| Split engine | [rules-spec.md](../domain/split-engine/rules-spec.md) |
| Surfaces & RBAC | [surface-map.md](../surfaces/surface-map.md) |
| MVP vs post-MVP tags | [mvp-roadmap.md](../product/mvp-roadmap.md) |

---

*Slice ownership: PART 19 — Executive Summary and Master PRD Compilation.*
