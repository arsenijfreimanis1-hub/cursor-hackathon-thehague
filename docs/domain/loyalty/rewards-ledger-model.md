# Rewards Ledger Model

**Slice:** Part 7 — Loyalty Economy and Overpay Reframe  
**Product (working name):** TabSettle / Rekentafel  
**Market:** Netherlands-first hospitality fintech  
**Cross-references:** [entity-dictionary.md](../../architecture/data-model/entity-dictionary.md) §9, [scope-boundary.md](../../product/scope-boundary.md) §2–3, [flows-a-o.md](../../flows/flows-a-o.md) Flow K/L/M

---

## 1. Purpose and hard boundaries

This document defines how **earn** and **burn** movements are recorded when venue-scoped loyalty is enabled. It explicitly **does not** define a stored-value wallet, EUR-denominated balance, or cross-venue coalition ledger.

| Capability | MVP | V1.1 | V2 venue loyalty | V2+ coalition |
|------------|-----|------|------------------|---------------|
| `rewards_accounts` table | Schema stub only | Schema stub only | Active | Active |
| `rewards_ledger_entries` writes | **None** | **None** | Yes | Yes + partner scope |
| Visit history (receipts) | No | Yes (`visit_records`) | Yes | Yes |
| Points accrual on payment | **No** | **No** | Yes | Yes |
| Points redemption | **No** | **No** | Same-venue only | Partner vouchers |
| Overpay → platform credit | **Never** | **Never** | **Never** as cash balance | See regulatory doc |

**Invariant:** `points_balance` is an **integer count of non-transferable promotional points**, never EUR cents. No API field exposes `points_balance * conversion_rate = EUR`.

---

## 2. Challenge to master-prompt assumption

The founding brief bundles **overpay → dining wallet → partner redemption** into one loyalty story. That conflates three ledgers:

1. **Payment ledger** (Mollie, EUR, settled to merchant) — MVP core  
2. **Promotional points ledger** (non-monetary, venue-scoped) — V2  
3. **Stored-value / e-money ledger** (EUR balance spendable at multiple merchants) — **Do-Not-Build**

Building (3) to fund (2) across partners is the fastest path to **EMI licensing** and destroys the pilot posture: *software on the restaurant’s Mollie account, no overnight fund holding.*

**Recommendation:** Treat tips (MVP) and venue points (V2) as separate products from any “overpay wallet.”

---

## 3. Canonical entities

### 3.1 Registry (cross-slice)

| Canonical name | Owner slice | DB table | MVP active? |
|----------------|-------------|----------|-------------|
| `RewardsAccount` | Part 7 / Part 9 | `rewards_accounts` | No writes |
| `RewardsLedgerEntry` | Part 7 / Part 9 | `rewards_ledger_entries` | No writes |
| `VisitRecord` | Part 7 | `visit_records` | V1.1+ |
| `VenueLoyaltyProgram` | Part 7 | `venue_loyalty_programs` | V2 |
| `LoyaltyOffer` | Part 7 | `loyalty_offers` | V2 |
| `Redemption` | Part 7 / Part 9 | `redemptions` | Post-MVP |
| `PartnerMerchant` | Part 7 / Part 9 | `partner_merchants` | Post-MVP |

### 3.2 `RewardsAccount`

One row per `user_id`. Scoped to **platform identity**, not restaurant — but **redemption scope** is enforced by program rules, not by duplicating accounts per venue.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | uuid | FK → `users`, UNIQUE |
| `points_balance` | int | ≥ 0 in normal ops; negative blocked at redemption |
| `lifetime_points_earned` | int | Monotonic; analytics only |
| `lifetime_points_redeemed` | int | Monotonic |
| `status` | enum | `ACTIVE`, `FROZEN`, `CLOSED` |
| `frozen_reason` | text | Fraud, chargeback cluster |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**No column:** `balance_cents`, `wallet_eur`, `stored_value`.

### 3.3 `RewardsLedgerEntry` (append-only)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK (UUID v7) |
| `rewards_account_id` | uuid | FK |
| `entry_type` | enum | See §4 |
| `points_delta` | int | Signed integer; accrual > 0, burn < 0 |
| `venue_id` | uuid | FK; NULL only for platform adjustments |
| `restaurant_id` | uuid | FK; denormalized for reporting |
| `payment_id` | uuid | FK → `payments`; set on accrual/reversal |
| `visit_record_id` | uuid | FK; optional link to visit |
| `redemption_id` | uuid | FK; set on burn |
| `loyalty_offer_id` | uuid | FK; set on burn |
| `idempotency_key` | varchar(128) | UNIQUE; e.g. `accrual:{payment_id}` |
| `metadata_json` | jsonb | Rule version, base cents, exclusions |
| `created_at` | timestamptz | Immutable |

**Rule:** Updates and deletes forbidden. Corrections = compensating entry (`ADJUSTMENT` or `REVERSAL`).

### 3.4 `VisitRecord` (V1.1 — not points)

Receipt-grade history without loyalty economics.

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `user_id` | uuid | FK |
| `dining_session_id` | uuid | FK |
| `venue_id` | uuid | FK |
| `payment_ids` | uuid[] | Guest’s payments in session |
| `food_total_cents` | int | Excl. tip; for display |
| `tip_total_cents` | int | |
| `visited_at` | timestamptz | Table close or last payment |
| `receipt_pdf_url` | text | Optional V1.1 |

MVP and V1.1: **no** automatic `RewardsLedgerEntry` on visit close.

### 3.5 `VenueLoyaltyProgram` (V2)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | PK |
| `venue_id` | uuid | FK, UNIQUE (one program per venue MVP of loyalty) |
| `earn_rule_json` | jsonb | See §5 |
| `burn_rules_json` | jsonb | Offer catalog references |
| `points_expire_days` | int | Default 365; max 730 without legal review |
| `status` | enum | `DRAFT`, `ACTIVE`, `PAUSED` |
| `funded_by` | enum | `VENUE` (default), `PLATFORM_PROMO` |

---

## 4. Entry types and sign convention

| `entry_type` | `points_delta` | Trigger | Idempotency key pattern |
|--------------|----------------|---------|-------------------------|
| `ACCRUAL` | +N | Payment settled; earn rule applied | `accrual:{payment_id}` |
| `REVERSAL` | −N | Full/partial refund, chargeback | `reversal:{refund_id}` |
| `REDEMPTION` | −N | Offer claimed at venue | `redemption:{redemption_id}` |
| `EXPIRATION` | −N | Batch job; FIFO by accrual age | `expire:{account_id}:{bucket_date}` |
| `ADJUSTMENT` | ±N | Manual ops; fraud correction | `adjust:{ticket_id}` |
| `CAMPAIGN_BONUS` | +N | Marketing grant (venue-scoped) | `campaign:{campaign_id}:{user_id}` |

**Balance computation:**

```
points_balance = SUM(points_delta) WHERE rewards_account_id = ? AND entry_type != 'PENDING'
```

(Do not use `PENDING` type — accrual writes only after `payment.status = PAID`.)

---

## 5. Earn rules (V2 venue loyalty)

### 5.1 Default earn formula (recommended)

Points accrue on **eligible food + beverage subtotal**, excluding tip, service charge pass-through if configured, and alcohol if venue opts out.

```
eligible_cents = payment.subtotal_share_cents
                 - payment.tip_cents
                 - excluded_categories_cents

points = FLOOR(eligible_cents / earn_cents_per_point)
```

**Default:** `earn_cents_per_point = 100` → **1 point per €1.00** of eligible spend.

### 5.2 Numeric example — accrual

**Guest B payment at De Rekentafel**

| Component | Cents |
|-----------|-------|
| Claimed food + drink (excl. tip) | 3,840 |
| Tip | 384 |
| **Mollie charge** | **4,224** |

Earn base = 3,840 cents → **38 points** (`FLOOR(3840/100)`).

Ledger row:

```json
{
  "entry_type": "ACCRUAL",
  "points_delta": 38,
  "payment_id": "pay_…",
  "venue_id": "ven_…",
  "idempotency_key": "accrual:pay_…",
  "metadata_json": {
    "eligible_cents": 3840,
    "earn_cents_per_point": 100,
    "rule_version": "2026-06-1",
    "tip_excluded_cents": 384
  }
}
```

### 5.3 Accrual eligibility gates

| Gate | Must pass |
|------|-----------|
| Payment status | `PAID` (Mollie webhook confirmed) |
| User link | `participant.user_id` NOT NULL at accrual time OR retro-link within 24h (V2) |
| Program status | `VenueLoyaltyProgram.status = ACTIVE` |
| Venue match | Payment’s venue = program’s venue |
| Minimum spend | Optional; e.g. ≥ €5 eligible → else 0 points |
| Fraud score | Account not `FROZEN`; velocity checks pass |

### 5.4 Retroactive link (V2)

If guest pays anonymously then verifies email within **24 hours** on same `guest_device_id`:

1. Emit `account.linked`  
2. Backfill accrual for eligible `payment_ids` on that device/session  
3. Idempotency prevents double accrual if already linked at pay time  

**MVP/V1.1:** Retroactive accrual **disabled** — no ledger writes exist yet.

---

## 6. Burn rules (V2 same-venue only)

### 6.1 `LoyaltyOffer` (venue-scoped)

| Field | Example |
|-------|---------|
| `title` | Free coffee |
| `points_cost` | 80 |
| `offer_type` | `IN_VENUE_ITEM`, `PERCENT_DISCOUNT`, `FIXED_EUR_DISCOUNT` |
| `discount_bps` | 1000 (= 10%) if percent |
| `max_redemptions_per_user_per_day` | 1 |
| `valid_days` | Mon–Thu |

**Hard rule (MVP of loyalty):** `offer.venue_id` MUST equal accrual venue for points being spent. No cross-venue burn in V2.0.

### 6.2 Redemption flow (ledger)

```
REDEMPTION requested
    → lock points (optimistic: balance >= cost)
    → create redemption row status=REQUESTED
    → append REDEMPTION entry (points_delta = -cost)
    → staff confirms OR auto-confirm via QR
    → redemption status=REDEEMED
```

On failure before confirm: compensating `ADJUSTMENT` (+cost) and status `CANCELLED`.

### 6.3 Numeric example — burn

Balance: **120 points**. Offer: **80 points = free dessert** (€8 menu value).

| Step | points_balance |
|------|----------------|
| Before | 120 |
| REDEMPTION −80 | 40 |
| Guest pays remainder of bill via Mollie as normal | — |

**Accounting note:** Discount is applied as **line-level adjustment on bill** or **comp item** entered by staff — not as EUR credit in a wallet. See [regulatory-framing.md](./regulatory-framing.md).

---

## 7. Reversal and refund logic

### 7.1 Full refund

Payment €42.24 refunded in full; original accrual was 38 points.

```
REVERSAL entry: points_delta = -38
idempotency_key: reversal:{refund_id}
```

If guest already redeemed 80 points from balance that included these 38:

- Balance may go negative **internally** during reversal  
- **Policy:** block new redemptions until balance ≥ 0; do not claw back fulfilled in-venue comps via ledger alone (ops manual)

### 7.2 Partial refund

Original eligible €38.40 → 38 points. Refund €10.00 eligible portion.

```
points_to_claw = FLOOR(1000 / earn_cents_per_point) = 10
REVERSAL: -10
```

Use proportional claw unless refund metadata specifies line-level allocation.

---

## 8. Expiration (V2)

Batch job (daily 03:00 Europe/Amsterdam):

1. Select accrual buckets older than `points_expire_days`  
2. FIFO consume against remaining balance  
3. Write `EXPIRATION` entries  

**Breakage:** Expired points reduce venue/platform liability — see accounting section in [regulatory-framing.md](./regulatory-framing.md).

Example: 50 points accrue 2025-01-01, expire 365 days → `EXPIRATION` −50 on 2026-01-01 if unredeemed.

---

## 9. State machines

### 9.1 Rewards account lifecycle

```
                    ┌──────────┐
         create     │  ACTIVE  │◄──── unfreeze (ops)
        ──────────► │          │
                    └────┬─────┘
                         │
           fraud/chargeback cluster
                         │
                         ▼
                    ┌──────────┐
                    │  FROZEN  │──► redemptions blocked; accrual may continue
                    └────┬─────┘
                         │ GDPR erasure / user request
                         ▼
                    ┌──────────┐
                    │  CLOSED  │──► balance forfeited; ledger retained 7y audit
                    └──────────┘
```

### 9.2 Accrual pipeline (V2)

```
payment.mollie.webhook.paid
        │
        ▼
┌───────────────────┐
│ Link user?        │──no──► (optional) queue retro-link window; no accrual yet
└─────────┬─────────┘
          │ yes
          ▼
┌───────────────────┐
│ Program ACTIVE?   │──no──► stop
└─────────┬─────────┘
          │ yes
          ▼
┌───────────────────┐
│ Compute points    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ INSERT ACCRUAL    │ idempotent on payment_id
│ (append-only)     │
└─────────┬─────────┘
          │
          ▼
   emit loyalty.accrued
```

### 9.3 Redemption lifecycle

```
REQUESTED ──confirm──► REDEEMED
    │                      │
    cancel                 └──► immutable; no un-burn
    ▼
CANCELLED (+ ADJUSTMENT restore points)

REQUESTED ──timeout 15m──► EXPIRED (+ ADJUSTMENT)
```

---

## 10. What is explicitly NOT in the ledger

| Mechanism | Why excluded |
|-----------|--------------|
| Overpay surplus → EUR credit | E-money / EMI |
| Overpay surplus → generic platform wallet | Stored value |
| Tip amount → points multiplier | Gamification / farming risk |
| Transfer points to another user | Stored value + AML |
| Cash-out points to IBAN | E-money |
| Crypto-denominated rewards | Separate regulated rail |
| Cross-venue burn without coalition contract | Multi-merchant stored value |

---

## 11. Overpay reframe (no ledger row in MVP)

If product later wants a **virtue signal** without wallet:

| Alternative | Ledger impact | Phase |
|-------------|---------------|-------|
| Round-up tip to staff | Tip table only; Mollie | MVP |
| Round-up to venue charity | Separate donation line; no balance | V2 |
| “Bonus points” on full bill pay | `CAMPAIGN_BONUS` non-monetary | V2 |
| Instant % discount voucher same visit | Promo code; no stored balance | V2 legal review |

**Do-Not-Build:** Checkout toggle “+10% to dining wallet for partner discounts.”

---

## 12. Events (event catalog alignment)

| Event | When | Payload |
|-------|------|---------|
| `loyalty.accrued` | ACCRUAL committed | `user_id`, `payment_id`, `points`, `venue_id` |
| `loyalty.reversed` | REVERSAL committed | `refund_id`, `points` |
| `loyalty.redemption.requested` | Burn initiated | `redemption_id`, `offer_id` |
| `loyalty.redemption.completed` | Staff confirm | `redemption_id` |
| `loyalty.account.frozen` | Fraud ops | `reason_code` |
| `visit.recorded` | V1.1 table close | `visit_record_id` — **no points** |

MVP emits: **`visit.recorded` only in V1.1** (optional). No `loyalty.*` events in MVP.

---

## 13. Implementation phases vs schema

| Phase | Schema | Runtime behavior |
|-------|--------|------------------|
| MVP | Tables may exist empty | Zero ledger writes; zero accrual UI |
| V1.1 | + `visit_records` | Email account + receipt history |
| V2.0 | + `venue_loyalty_programs`, `loyalty_offers` | Earn/burn same venue |
| V2.5+ | + `partner_merchants`, coalition partition | Separate PRD + legal sign-off |

---

## 14. Open engineering questions

| Question | Default recommendation |
|----------|------------------------|
| Per-venue sub-ledger vs single account? | Single `RewardsAccount`; scope burns by `venue_id` on entries |
| Negative balance after reversal? | Allow internal negative; block redemption |
| Points on service charge? | Venue-configurable; default exclude |
| Alcohol exclusion? | Venue flag for NL hospitality norms |
| Rounding on split pay accrual | Accrue per `payment_id`, not per table |

---

*Slice ownership: Part 7 — Loyalty Economy. File: `docs/domain/loyalty/rewards-ledger-model.md`.*
