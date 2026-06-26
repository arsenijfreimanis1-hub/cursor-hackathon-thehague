# Rekentafel — Restaurant Value Proposition (Owner One-Pager)

**Audience:** Restaurant owner / GM (Netherlands independent full-service)  
**Use:** Pilot LOI attachment, inbound sales, waiter buy-in meeting  
**Product:** Rekentafel — waiter-controlled table split-pay (not phone ordering)  
**Last updated:** 2026-06-26

---

## The problem you already pay for

| Today | Cost |
|-------|------|
| One guest pays the whole bill on card | **3–8 minutes** blocked at terminal |
| Group asks to split; waiter re-runs mental math | **Staff distraction** during peak |
| Tikkie / bank requests after guests leave | **5–15 minutes** async; wrong amounts; social friction |
| Table sits occupied while payment resolves | **Lost turn** — empty seats earn nothing |

**Example:** Table of six, bill **€186,40**. One payer fronts the full amount; two guests forget Tikkie; payer eats **€24**. Waiter revisits table **twice**. Next seating delayed **12 minutes**.

Rekentafel fixes the **last 10 minutes of the meal** — not your ordering workflow.

---

## What Rekentafel is (and is not)

| Rekentafel **is** | Rekentafel **is not** |
|-------------------|----------------------|
| Same table QR; waiter **opens payment mode** when bill is ready | Guests ordering food from phones |
| Guests claim items, split fairly, tip individually | A live public bill on QR before staff activate session |
| Payments via **your Mollie account** (iDEAL \| Wero, cards, Apple/Google Pay) | Platform holding your money |
| Shorter pay phase → **faster table turns** | Another POS replacement |

**You stay merchant of record.** Guest payments settle to **your Mollie balance** — same as today.

---

## ROI arguments (numbered for owner conversations)

### 1. Recover table turns (revenue)

| Assumption | Value |
|------------|-------|
| Tables | 28 |
| Extra turn from 6 min saved / split table | Conservative **0.15 turns/day/venue** (not every table) |
| Avg cover revenue / turn | **€86** |
| **Monthly upside** | 28 × 0.15 × 26 × €86 ≈ **€9,400/mo** potential *(upper bound if every minute converts — pilot measures actual)* |

**Conservative owner message:** Save **6 minutes** on **65%** of dinner tables → **~104 hours/month** of dining room capacity returned.

### 2. Reduce front-of-house payment labor

| Without | With Rekentafel |
|---------|-----------------|
| Waiter at terminal, splits bill manually | Waiter taps **"Payment mode"** once |
| Multiple partial terminal attempts | Guests pay **their share** from phones |
| "Can you split the wine?" debates | Item claims + equal/custom split built in |

**Staff message:** You still take orders. You stop being the table's accountant at 21:30 on Saturday.

### 3. Fairer splits → happier guests → repeat visits

| Pain | Rekentafel |
|------|------------|
| One payer subsidizes the group | Each guest pays **claimed items + their tip** |
| Shared bottle disputes | Shared-item split rules + waiter override |
| Post-meal Tikkie awkwardness | Settled **before they stand up** |

Guests still don't need an account at MVP.

### 4. Cleaner audit trail (chargebacks & corrections)

| Event | Benefit |
|-------|---------|
| Per-guest Mollie payment ID | Dispute maps to **one payer**, not whole table |
| Allocation snapshot at checkout | Evidence for partial refunds |
| Waiter close + audit log | End-of-shift reconciliation |

You bear chargeback liability today — itemized payments reduce opaque "I didn't authorize €186" disputes.

### 5. No hardware capex

| Alternative | Cost |
|-------------|------|
| Extra portable terminals | €300–800 + rental |
| Pay-at-table tablets | SaaS + hardware |
| **Rekentafel** | **QR on table tent** — uses guest phones |

### 6. Netherlands-native payments

- **iDEAL \| Wero** — what your guests already use  
- Tips on **each guest's payment**, metadata for your payroll policy  
- VAT lines displayed per hospitality norms (9% / 21% split visibility)

### 7. Pilot risk is capped

| Pilot term | Detail |
|------------|--------|
| Platform fee | **€0 for 90 days** |
| Guest fee | **€0 always** |
| You pay | **Mollie per guest payment** (see cost transparency below) |
| Exit | Stop using payment mode; keep menu QR if desired |

---

## Honest cost transparency (builds trust)

Split-pay uses **one Mollie payment per guest**, not one swipe for the whole table.

**Example bill €86,40, four guests pay via iDEAL:**

| Path | Mollie payments | Mollie cost (@ €0.32/iDEAL) |
|------|-----------------|-----------------------------|
| Terminal — one card | 1 | **€0.32** |
| Rekentafel — four iDEAL | 4 | **€1.28** |
| **Difference** | +3 | **+€0.96 per table** |

**Why it's still worth it:** **€0.96** buys **~6 minutes** back if guests self-pay. At **€15/hour** table opportunity, **6 min ≈ €1.50** — **net +€0.54** before happier staff/guests.

If you don't hit time savings, we don't deserve your subscription after pilot.

---

## What you control

| Control | Owner benefit |
|---------|---------------|
| Waiter **must activate** payment session | No random scanners see open bills |
| Waiter override / force-close | Bad split? Staff fixes it |
| Your Mollie dashboard | Payouts unchanged — **T+1 iDEAL**, cards slower |
| Menu + tables in admin | No IT project |
| Tips pass through to **your** account | Platform does **not** take a cut of tips |

---

## MVP pilot success criteria (joint)

We only ask for paid subscription after we prove:

1. **≥70%** of eligible tables use split-pay in a typical week **OR**
2. **≥6 minutes** median reduction from "payment mode" to table close

We share a **monthly report**: sessions, guest checkouts, pay-phase duration, GMV through Rekentafel.

---

## Pricing after pilot (no surprises)

| Phase | Your cost |
|-------|-----------|
| Pilot (90 days) | **€0** platform |
| Standard MVP | **€59/month** (excl. BTW) — flat, predictable |
| Later (optional) | Lower monthly + small per-checkout fee — **only if you opt in** |

**No percentage of your sales during pilot.** No guest surcharges. Ever.

---

## Comparison at a glance

| | Tikkie after dinner | Terminal split | Full QR ordering | **Rekentafel** |
|--|---------------------|----------------|------------------|----------------|
| Waiter-led service | Yes | Yes | Often no | **Yes** |
| Pay at table | No | Yes | Varies | **Yes** |
| Item-level split | No | Poor | Varies | **Yes** |
| Extra hardware | No | Often | Sometimes | **No** |
| Changes who takes orders | No | No | **Yes** | **No** |
| Setup complexity | None | Low | High | **Low** |

---

## Risks we disclose upfront

| Risk | Our mitigation |
|------|----------------|
| More Mollie txns vs one swipe | Time-savings math; iDEAL-first UX |
| Staff forget to activate payment mode | Training + simple waiter UI |
| Guest confusion | Dutch/English UI; waiter announces "scan to pay your part" |
| Wrong item claim | Waiter override; audit log |
| You need POS sync day one | **Not required for MVP** — manual bill entry or simple import |

---

## Implementation (first week)

| Day | Action |
|-----|--------|
| 1 | Connect **your Mollie account** (OAuth); add tables + menu |
| 2 | Train shift lead — **3 waiter flows**: start session, payment mode, close |
| 3–7 | Soft launch dinner service; we monitor pay-phase metrics |
| Week 4–12 | Tune; hit success criteria; decide post-pilot subscription |

**Your IT requirement:** Wi-Fi for staff tablet/phone. No install on POS.

---

## One sentence for your staff meeting

**"Guests pay their own share from the same QR after we open the bill — you still run the floor, we lose the Tikkie circus."**

---

## Contact / next step

Agree to **90-day pilot LOI** → we configure venue → measure → you decide.

*Internal reference: [pricing-recommendation.md](./pricing-recommendation.md), [unit-economics.md](./unit-economics.md)*
