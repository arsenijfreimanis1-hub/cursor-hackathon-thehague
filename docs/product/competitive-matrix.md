# Competitive Matrix — Rekentafel (Table QR Split-Pay)

**Slice:** Product Reframe and Competitive Positioning  
**Market:** Netherlands-first  
**Last updated:** 2026-06-26

---

## Primary comparison matrix (required dimensions)

Scoring: **Strong** / **Partial** / **Weak** / **N/A**  
Context: Dutch table-service restaurant, 4–6 guests, open itemized bill, waiter-led ordering.

| Alternative | Waiter control | Split granularity | Onboarding friction | NL payment fit | Regulatory surface |
|-------------|----------------|-------------------|---------------------|----------------|---------------------|
| **Tikkie (ABN AMRO P2P)** | **Strong** — waiters unchanged; payment happens off-platform | **Weak** — fixed EUR amounts only; no item claims, no shared-item rules, no partial table | **Strong** — zero restaurant setup; guest-side only | **Strong** — iDEAL-native; ubiquitous in NL | **Low** — bank P2P; no merchant payment facilitation |
| **Full QR ordering** (e.g. Orderli, Mr.Yum-class) | **Weak** — guest submits orders; staff become fulfillment | **Partial** — pay-at-order or end-of-session; splits vary by vendor | **Weak** — menu sync, kitchen flow, staff retraining | **Partial** — often Stripe/Adyen; iDEAL varies | **Medium** — merchant payments + platform SaaS; order liability |
| **POS pay-at-table** (Zettle, Adyen terminal, Untill pay-at-table) | **Strong** — waiter still owns service; terminal at table | **Weak** — one card per swipe; manual split math | **Partial** — hardware + POS module; no new guest app | **Strong** — NL terminals support iDEAL/card | **Medium** — merchant acquirer relationship |
| **Rekentafel (us)** | **Strong** — no phone ordering; payment session waiter-gated | **Strong** — item claim, equal/custom, shared items, partial payers | **Partial** — QR print, menu upload, Mollie connect; no POS day one | **Strong** — Mollie-first (iDEAL, cards, wallets) | **Medium** — SaaS + payment orchestration; no e-money in MVP |

---

## Extended competitor / alternative set (≥4)

Includes direct, adjacent, and status-quo alternatives relevant to NL pilot positioning.

### Summary scorecard

| # | Alternative | Category | Threat to Rekentafel | Our wedge |
|---|-------------|----------|----------------------|-----------|
| 1 | **Tikkie** | Status-quo P2P | High habit; zero restaurant cost | In-venue bill truth + itemized split |
| 2 | **Full QR ordering** | Direct adjacent | Same QR real estate | Payment-only; preserve table service |
| 3 | **POS pay-at-table terminal** | Hardware | Already owned by venue | Multi-phone concurrent checkout |
| 4 | **Sunday / competitor pay-at-table apps** | Software pay-at-table | Similar "scan and pay" story | Waiter-gated session; no ordering |
| 5 | **Payment link in WhatsApp** | Informal | Zero friction | Structured session + remaining balance |
| 6 | **Splitwise + manual calc** | Consumer app | Groups already use | Integrated to live bill + iDEAL |
| 7 | **Bancontact / iDEAL QR (generic)** | Bank QR | Free | No split logic, no restaurant dashboard |

---

## Detailed competitor profiles

### 1. Tikkie (status quo)

| Field | Detail |
|-------|--------|
| **What it is** | Dutch P2P payment request via iDEAL or bank app |
| **Typical flow** | One guest pays full bill → sends €37,50 requests to five friends → async settlement over hours/days |
| **Waiter control** | Unchanged — strongest alignment with traditional service |
| **Split granularity** | Amount-only; no line-item awareness; shared items require manual math |
| **NL payment fit** | Best-in-class iDEAL adoption |
| **Regulatory surface** | Consumer P2P; restaurant not in payment chain |
| **Weakness we exploit** | Social debt, errors, delays, no restaurant visibility, payer concentration risk |
| **When Tikkie wins** | Couples, small trusted groups, cashless payer already has card out |

**Example failure:** €186,40 bill, payer requests €31,07 × 6; two guests round to €30; payer eats €12,40 gap.

---

### 2. Full QR ordering systems

| Field | Detail |
|-------|--------|
| **Representatives** | Orderli (NL), Mr.Yum, me&u-class platforms |
| **What it is** | Scan QR → browse menu → submit order → pay (sometimes pre-pay) |
| **Waiter control** | Reduced — orders originate on guest device |
| **Split granularity** | Varies: individual carts, pay-at-end, or no native multi-payer split |
| **Onboarding** | Heavy — menu, modifiers, kitchen routing, allergen sync |
| **NL payment fit** | Depends on PSP integration |
| **Regulatory surface** | Platform + merchant; order accuracy liability |
| **Weakness we exploit** | Cultural mismatch for fine dining / waiter-led venues; ops complexity |
| **When they win** | High-volume casual, brewery halls, stadiums, labor-constrained QSR |

**Positioning line:** "They replace the waiter at order time. We support the waiter at payment time."

---

### 3. POS pay-at-table (terminal / integrated)

| Field | Detail |
|-------|--------|
| **Representatives** | Zettle Reader, Adyen terminal, Untill/Mplus pay-at-table modules |
| **What it is** | Physical device or POS function brings payment to table |
| **Waiter control** | Strong — staff initiates or delivers terminal |
| **Split granularity** | Typically single amount; split requires multiple transactions or staff calculator |
| **Onboarding** | Medium — already sunk if POS owned |
| **NL payment fit** | Strong for card; iDEAL on terminal varies |
| **Regulatory surface** | Merchant acquirer standard |
| **Weakness we exploit** | Sequential multi-payer UX; device hygiene; no concurrent iDEAL on 6 phones |
| **When they win** | Single payer, business dining, card-only fast checkout |

**Example:** Six guests, terminal passed clockwise — 6× card insert + PIN ≈ 8–12 min vs parallel web checkout.

---

### 4. Sunday-style pay-at-table software

| Field | Detail |
|-------|--------|
| **What it is** | Scan QR → view bill → pay (often POS-integrated) |
| **Overlap with us** | High — same "pay at table" category |
| **Typical differentiation** | Often POS-native; may include ordering or loyalty |
| **Waiter control** | Partial — depends on bill exposure model |
| **Split granularity** | Varies; many focus on full-bill or equal split |
| **Onboarding** | Medium–heavy if POS integration required |
| **Our angle** | MVP without POS; explicit item-claim + partial-table payers; NL Mollie-first; **no ordering** |

**Risk:** If Sunday (or similar) ships strong item-split without POS lock-in, wedge narrows. Pilot must prove **partial participation** UX (2 of 4 pay now, others later).

---

### 5. WhatsApp payment link (informal)

| Field | Detail |
|-------|--------|
| **What it is** | Waiter or payer sends Mollie/Stripe link in chat |
| **Split granularity** | None — usually one link for remainder |
| **Onboarding** | Zero |
| **Weakness** | No audit trail, no item map, no waiter dashboard |
| **Our wedge** | Same low setup, structured multi-payer session |

---

### 6. Splitwise (+ manual bank transfer)

| Field | Detail |
|-------|--------|
| **What it is** | Expense splitting app; settlement via bank/Tikkie later |
| **Waiter control** | N/A — post-visit |
| **Split granularity** | Strong math; no payment rail integration |
| **Weakness** | Not in-restaurant; extra app; async |
| **Our wedge** | Split logic **at payment time** on authoritative bill |

---

## Feature-level matrix (secondary)

| Feature | Tikkie | QR ordering | POS terminal | Sunday-class | **Rekentafel MVP** |
|---------|--------|-------------|--------------|--------------|---------------------|
| Item-level claim | No | Partial | No | Partial | **Yes** |
| Partial table pay (2 of 4) | Awkward | Rare | No | Partial | **Yes** |
| Shared item split (e.g. wine) | Manual | Partial | Manual | Partial | **Yes** |
| Per-guest tip | No | Partial | Single | Partial | **Yes** |
| Waiter payment dashboard | No | Partial | POS-only | Partial | **Yes** |
| No app download | Yes | Yes | N/A | Yes | **Yes** |
| Menu on empty table | No | Yes | No | Partial | **Yes (no order)** |
| Call server signal | No | Sometimes | No | Rare | **Yes** |
| POS sync required | No | Often | Yes | Often | **No (MVP)** |
| iDEAL-native | Yes | Varies | Varies | Varies | **Yes (Mollie)** |
| Bill hijack protection | N/A | Varies | N/A | Varies | **Session token** |

---

## Competitive response scenarios

| If competitor… | Rekentafel response |
|------------------|---------------------|
| Tikkie adds "group bill" UI | Still no restaurant bill truth; emphasize waiter-activated itemized session |
| QR ordering adds split pay | Double down on **no phone ordering** for service-led venues |
| POS vendor ships native multi-split | Integrate (V1.1), don't compete on receipt printing |
| Sunday expands NL without POS | Win pilot venues first; prove partial-payer UX moat |

---

## Win / loss criteria (pilot sales)

**We win when:**

- Venue rejected phone ordering but wants modern payments
- Large group tables common (≥4 tops on weekends)
- Owner cites Tikkie reconciliation complaints from staff/guests
- Mollie already in use or easy KYC

**We lose when:**

- Venue wants order-volume lift via QR (wrong product)
- Single-payer culture (business hotel lunch)
- POS vendor bundles pay-at-table "good enough" at zero marginal cost
- Owner won't manually enter bills (address in V1.1 POS sync)

---

## Related artifacts

- [Positioning](./positioning.md)
- [Elevator pitch](./elevator-pitch.md)
