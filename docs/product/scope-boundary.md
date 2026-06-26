# Scope Boundary Document

**Purpose:** Draw a hard line between what the Netherlands pilot must prove and what would dilute focus, trigger licensing, or ship untestable complexity. This document explains **opinionated tradeoffs** and **deferral rationale** for features named in the master product blueprint but excluded from MVP.

**Companion:** [mvp-roadmap.md](./mvp-roadmap.md) — feature tags and phase tables.

---

## Core Scope Thesis

The wedge is **collaborative split-pay at the table** while **waiters retain order authority**. Everything else is optional gravity.

| In scope (MVP) | Out of scope (MVP) |
|----------------|-------------------|
| Persistent table QR → menu + context | Discovery marketplace |
| Waiter opens session + enters bill | POS bi-directional sync |
| Payment mode + session token | Public bill on naked QR |
| Item/equal/custom/shared splits | Phone ordering |
| Per-guest tip + Mollie checkout | Crypto rail |
| Partial pay until €0 | Stored-value wallet / overpay credit |
| Waiter override + audit | Coalition loyalty redemption |
| Single pilot venue | Multi-venue franchise BI |
| Web responsive surfaces | Native apps |

**Challenge to master prompt assumption:** The founding brief bundles crypto, loyalty, discovery, and overpay-wallet into one vision. That is a **portfolio of three products** (payments, marketplace, loyalty bank). Shipping them together before one venue closes a split bill guarantees slow failure. MVP intentionally amputates everything that is not required for: *“Can four strangers pay their exact shares without one person fronting the card?”*

---

## MVP Boundary in One Flow

```
Guest scans QR
    │
    ├─ Table EMPTY/SEATED ──► Menu + "Call server" ONLY
    │                         (no bill, no pay button)
    │
    └─ Waiter activates PAYMENT + token
              │
              ▼
        Guest joins session ──► Claim/split ──► Mollie ──► Partial OK
              │
              └─ Remaining €0 or waiter close ──► Session CLOSED
```

Anything outside this spine is **V1.1 or later** unless it is pure bug-fix/security.

---

## Deferral Rationale by Feature

### 1. Crypto payments — **Never (MVP/V1.1); V2 optional eval**

**Master prompt ask:** Mollie primary + crypto if Mollie cannot support it.

**Decision:** MVP is **Mollie-only** (iDEAL, cards, Apple Pay via Mollie). Crypto is a **separate regulated payment rail**, not an MVP checkbox.

| Dimension | Analysis |
|-----------|----------|
| **Mollie** | Strong for EUR fiat in NL; no substitute for on-chain settlement without a crypto PSP partner |
| **Legal** | Crypto acceptance may trigger MiCA, AML/KYC, travel rule, and tax reporting — unrelated to restaurant SaaS licensing |
| **UX** | Table pay needs <60s checkout; chain confirmations violate that |
| **Ops** | FX volatility, wrong-chain sends, and chargeback analogs are non-trivial support load |
| **Fraud** | Irreversible chain txs worsen group-bill dispute handling |

**Architecture (when revisited in V2+):**

```
Guest checkout
    │
    ├─ Fiat path (default) ──► Mollie hosted checkout ──► Merchant Mollie balance
    │
    └─ Crypto path (opt-in, separate) ──► Licensed crypto PSP (e.g. BV partner)
              │                              │
              │                              ├─ EUR settlement to merchant (preferred)
              │                              └─ Or USDC with immediate EUR quote lock
              └─ Platform NEVER custodies keys or chain balances in MVP/V1.1
```

**Opinionated tradeoff:** Defer crypto even if a pilot guest asks. One crypto payment per month does not justify compliance surface. Revisit when **fiat split-pay PMF** is proven and a **named licensed partner** offers EUR settlement API.

**Tag:** Never MVP | Never V1.1 | V2 eval only

---

### 2. Coalition loyalty + partner rewards marketplace — **Never (MVP/V1.1); V2 fragment**

**Master prompt ask:** Loyalty, visit history, partner redemption, cross-restaurant rewards.

**Decision:** MVP has **no loyalty earn or burn**. V1.1 may add **optional accounts + single-venue visit history** (receipts only). **Cross-venue coalition** and **partner marketplace** are V2 at earliest and may remain Never if EMI/legal cost exceeds revenue.

| Layer | MVP | V1.1 | V2 |
|-------|-----|------|-----|
| Guest account | No | Optional | Yes |
| Visit history | No | Single venue | Cross-venue (GDPR) |
| Points earn | No | No | Venue-scoped |
| Partner redemption | No | No | Pilot partners only |

**Why defer coalition:**

1. **Cold start:** Partners won't integrate for one restaurant.
2. **Accounting:** Points liability sits on someone’s balance sheet — restaurants will not fund cross-venue subsidies at pilot.
3. **Scope:** Marketplace needs catalog, fulfillment, breakage rules, and customer support — not payment wedge.

**Opinionated tradeoff:** Single-venue “stamp card” digital equivalent is V2 **only after** restaurants renew SaaS. Coalition marketplace is a **different company motion** (BD-heavy). Do not conflate with split-pay.

**Tag:** Partner marketplace **Never** until venue density | Venue loyalty **V2**

---

### 3. Stored-value wallet / overpay-to-rewards — **Never (as cash balance)**

**Master prompt ask:** User overpays 10%; extra becomes platform credit / dining wallet redeemable with partners.

**Decision:** **Explicit Never** for any balance that behaves like spendable money.

| Mechanism | Allowed? | Why |
|-----------|----------|-----|
| Tip above bill | Yes (MVP) | Pass-through to venue/staff per config |
| Rounded-up donation to venue charity | V2 maybe | One-way; no stored balance |
| Platform credit usable next visit | **Never** without EMI | E-money |
| Overpay → generic wallet → partner discounts | **Never** MVP/V1.1 | Stored value + multi-merchant redemption = EMI/PSD2 complexity |

**Reframe (if product insists on “overpay” narrative later):**

- **V2 non-monetary:** Extra payment donates to staff tip pool or charity — no ledger balance.
- **V2 promotional points:** Non-transferable, expire in 90 days, single venue, no cash equivalence — requires legal review but lower risk than wallet.

**Opinionated tradeoff:** Kill the “dining wallet” fantasy early. It is the fastest path to **EMI license** and destroys the “we’re SaaS on your Mollie account” story.

**Tag:** **Never** as stored-value wallet | Overpay mechanics **Never** unless legal signs non-e-money design

---

### 4. Restaurant discovery feed — **Never (MVP/V1.1/V2 early)**

**Master prompt ask:** Restaurant discovery and personalized suggestions from order behavior.

**Decision:** **Never** in MVP/V1.1. Discovery is a **consumer marketplace** requiring geographic density, SEO, reviews moderation, and restaurant sales — orthogonal to B2B split-pay.

| Risk | Impact |
|------|--------|
| Two-sided cold start | Guests have nothing to discover with one venue |
| GDPR profiling | Order history → recommendations needs explicit consent + DPIA |
| Brand dilution | Restaurants fear platform stealing demand |

**Opinionated tradeoff:** The QR is **venue-owned entry**, not a platform homepage. Guest lands on **Restaurant X Table 5**, not “find nearby tacos.”

**Minimal V2 exception:** **Within-venue** suggestions only (“dessert special”) with no cross-venue data — still optional, not MVP.

**Tag:** Cross-venue discovery **Never** early | Within-venue upsell **V2 optional**

---

### 5. ML personalized recommendations — **Never (MVP/V1.1)**

**Master prompt ask:** Personalized suggestions based on order behavior.

**Decision:** Defer until **consented history** exists at scale. MVP guests are often **unauthenticated**; ML on anonymous sessions is thin and legally sensitive.

| Alternative | Phase |
|-------------|-------|
| Static menu + waiter specials | MVP |
| Rule-based “popular item” badge | V1.1 |
| ML ranking | V2+ with opt-in accounts |

**Opinionated tradeoff:** A logistic regression on 200 orders is not intelligence — it is theater. Ship trustworthy splits first.

**Tag:** **Never** MVP/V1.1 | Rule-based **V1.1** | ML **V2+**

---

### 6. Deep POS bi-directional order sync — **Never (MVP/V1.1); V2 per vendor**

**Master prompt ask:** Eventually sync with POS; MVP explicitly manual/import.

**Decision:**

| Integration depth | Tag | Notes |
|-------------------|-----|-------|
| Waiter manual entry | MVP | Default pilot path |
| CSV / export import | MVP | Batch lines onto open session |
| Read-only POS pull (check total + lines) | V1.1 | Reduces error; still no guest ordering |
| Bi-directional order + pay sync | **Never** MVP/V1.1 | Vendor-specific, fragile, sales blocker if promised early |

**Why bi-directional is deferred:**

1. **NL POS fragmentation** — each integration is a quarter, not a sprint.
2. **Product positioning** — orders stay with waiter; sync is back-office convenience, not guest feature.
3. **Failure modes** — POS desync vs platform bill destroys trust faster than manual entry.

**Opinionated tradeoff:** Sell “works tomorrow with typing” not “works after Lightspeed certification.” First POS partner chosen by **pilot venue’s actual system**, not roadmap fantasy.

**Tag:** Bi-directional **Never** until V2 + signed vendor | Read-only **V1.1**

---

### 7. Native iOS/Android apps — **Never (MVP/V1.1)**

**Master prompt assumption:** Web-first mobile-responsive unless justified otherwise.

**Decision:** **Responsive web + optional PWA** for MVP and V1.1. Native apps deferred.

| Factor | Web wins MVP |
|--------|--------------|
| QR entry | Opens browser — zero install |
| Team size | 4 devs cannot ship 3 clients + backend |
| App store | Review delays kill pilot iterations |
| Future option | API-shaped backend preserves native path |

**Opinionated tradeoff:** Staff panel is a **mobile web app** used on waiter phones/tablets. Native only if PWA push/Bluetooth constraints block geo gates in V1.1 — re-evaluate with data.

**Tag:** **Never** MVP/V1.1

---

### 8. Gamified rewards farming — **Never**

**Master prompt exclusion:** Gamified rewards farming mechanics.

**Decision:** Permanent **Never**. Any mechanic that rewards overpay, fake visits, or synthetic splits is **fraud-adjacent** and conflicts with honest split-pay.

**Examples rejected:**

- “Pay 10% extra, level up your diner rank”
- Cross-venue streak bonuses tied to payment volume
- Referral loops on payment sessions

**Tag:** **Never**

---

### 9. Additional master-prompt exclusions (explicit)

| Exclusion | Tag | Boundary statement |
|-----------|-----|-------------------|
| Full QR phone ordering | **Never** | Guests cannot submit kitchen orders from phone — only call-server / ready signal |
| Multi-venue franchise analytics | **Never** MVP/V1.1 | Single-venue admin only; no roll-up dashboards |
| Automated chargeback automation | **Never** MVP/V1.1 | Ops manual queue; snapshot claims at payment time |
| Public live bill without waiter token | **Never** | Security invariant — see state machine in roadmap |

---

## Payment Architecture Boundary (Mollie vs Crypto)

### MVP/V1.1 — Mollie only

```
┌──────────────┐     claim + amount      ┌─────────────┐
│  Guest web   │ ───────────────────────►│   Backend   │
└──────────────┘                         └──────┬──────┘
                                                │
                     create payment             │
                                                ▼
                                         ┌─────────────┐
                                         │   Mollie    │
                                         │  (merchant  │
                                         │   account)  │
                                         └──────┬──────┘
                                                │ webhook
                                                ▼
                                         ┌─────────────┐
                                         │ Reconcile   │
                                         │ claim paid  │
                                         │ update      │
                                         │ remaining   │
                                         └─────────────┘
```

**MVP legal posture:** Platform is **software**; restaurant’s **Mollie merchant account** receives funds. Platform does not hold guest money overnight.

**Pilot open question (not blocking build):** Move to **Mollie Connect** in V2 for platform bps fee — requires onboarding flow and agreement structure.

### V2+ — Crypto as optional parallel rail (not Mollie extension)

Crypto must **not** be bolted onto Mollie webhooks as “another payment method” without a ** licensed crypto PSP**. Architecture:

| Component | Owner |
|-----------|-------|
| EUR checkout | Mollie |
| Crypto quote + invoice | Partner PSP API |
| Settlement to restaurant | EUR bank payout from partner (preferred) |
| Platform custody | **None** |
| Refunds | Partner policy; manual ops until volume justifies automation |

**Scope boundary:** Crypto **must not** appear in MVP/V1.1 UI, marketing, or pricing. Separate legal memo before any checkbox.

---

## Accounts & Loyalty Boundary

```
MVP guest journey
─────────────────
Scan ──► Join with nickname ──► Pay ──► Session ends ──► PII TTL delete (90d)

V1.1 optional account
─────────────────────
Email login ──► Receipt history per venue ──► Still NO points wallet

V2 venue loyalty (if legal clears)
──────────────────────────────────
Account ──► Earn venue points (non-transferable) ──► Redeem at same venue only
```

**Hard line:** No cross-restaurant “platform points” in any V1.x release.

---

## UX Scope Boundaries

| Temptation | Why we say no (MVP) | MVP substitute |
|------------|---------------------|----------------|
| “Show bill on scan so guests can browse” | Hijacking + privacy | Menu only until payment mode |
| “Let guests add items they forgot” | Becomes ordering | Ask waiter; waiter edits bill |
| “Auto-split bill equally always” | Ignores item claims | Default suggest equal; claims win |
| “Force account before pay” | Drops conversion at table | Nickname session |
| “Chat with other guests” | Moderation nightmare | Shared session view only |

---

## Ops & Fraud Boundaries

| Scenario | MVP handling | Deferred automation |
|----------|--------------|---------------------|
| Guest not at table joins session | Waiter override + optional V1.1 geo | Automated block |
| Two guests claim same beer | Optimistic lock; second fails; waiter resolves | AI dispute |
| Payment succeeds; webhook delayed | Polling + manual reconcile tool | Fully automated heal |
| Chargeback 30 days later | Manual ops with claim snapshot | Auto dispute evidence pack |
| Staff typo on bill | Manager edit before payments | POS sync |

---

## What We Will Say “No” To (Sales / Pilot Discipline)

Use this list in restaurant conversations:

1. “Can customers order from the QR?” → **No — by design.**
2. “Can we take Bitcoin?” → **Not in pilot — iDEAL/card via Mollie.**
3. “Can guests get platform credit for next time?” → **No stored wallet.**
4. “Can you integrate with our POS day one?” → **Manual entry pilot; import on roadmap.**
5. “Can you help us get discovered by new customers?” → **Not our product; your QR, your guests.**
6. “Can head office see all franchises?” → **Not until much later.**

---

## Weak Assumptions Challenged

| Assumption in brief | Challenge | Scope decision |
|--------------------|-----------|----------------|
| Crypto + Mollie equally important | False equivalence | Mollie MVP; crypto separate V2+ |
| Overpay wallet drives loyalty | Regulatory trap | Tips only MVP; points V2 venue-only |
| Discovery grows restaurants | B2B wedge is split-pay ROI | Never early |
| POS sync required for launch | Manual works for 1 venue | POS read V1.1; bi-dir V2 |
| Native apps needed for payments | QR → browser is standard | Web only |
| ML recommendations differentiate | Trust differentiates | Defer ML |
| Gamification increases tips | Invites abuse | Never |

---

## MVP Pilot Contract (What “Done” Means)

The pilot venue agrees to:

1. Enter or import bills for participating tables during pilot hours.
2. Train staff on **one action**: activate payment mode when guests ask to pay.
3. Accept **Mollie** as sole payment method for platform-processed checks.
4. Tolerate **manual** menu updates and **no POS sync** for 8 weeks.
5. Participate in weekly dispute review (claim overrides, failed webhooks).

The platform agrees to:

1. **Bill visibility + trustworthy split-pay** with audit trail.
2. **No feature creep** from this document’s Never list during pilot.
3. GDPR-minimal retention and DPA for processor roles.
4. Same-day support for payment-blocking bugs.

**Success = operational**, not feature-count:

> ≥70% of eligible tables complete split-pay with ≤8% waiter overrides and no unresolved reconciliation incidents in the final pilot fortnight.

---

## Document Cross-References

| Master prompt exclusion | Primary section above | Roadmap tag |
|-------------------------|----------------------|-------------|
| Crypto payments | §1 Crypto | Never MVP/V1.1 |
| Coalition partner rewards | §2 Loyalty marketplace | Never early |
| Discovery feed | §4 Discovery | Never early |
| ML recommendations | §5 ML | Never MVP/V1.1 |
| Stored-value / overpay wallet | §3 Overpay | Never |
| Full QR ordering | §9 Additional | Never |
| Native apps | §7 Native | Never MVP/V1.1 |
| Franchise analytics | §9 Additional | Never MVP/V1.1 |
| Chargeback automation | §9 Additional | Never MVP/V1.1 |
| POS bi-directional sync | §6 POS | Never MVP/V1.1 |
| Gamified rewards | §8 Gamification | Never |
| Public bill without token | MVP Boundary flow | Never |

---

*Slice ownership: Part 4 — MVP vs Post-MVP Scope Boundary.*
