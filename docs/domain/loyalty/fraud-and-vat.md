# Fraud Vectors and VAT-on-Earn

**Slice:** Part 7 — Loyalty Economy and Overpay Reframe  
**Cross-references:** [regulatory-framing.md](./regulatory-framing.md), [rewards-ledger-model.md](./rewards-ledger-model.md), [scope-boundary.md](../../product/scope-boundary.md) §8, [split-engine/concurrency.md](../split-engine/concurrency.md)

---

## 1. Scope

This document covers **fraud and abuse** specific to loyalty, overpay, and coalition mechanics, plus **VAT (BTW) open questions** on earn and burn in the Netherlands. Payment-session fraud (bill hijacking, double claims) belongs to the split-engine slice — referenced here only where loyalty intersects.

---

## 2. Threat model summary

| Actor | Goal | Phase at risk |
|-------|------|---------------|
| Guest (collusive) | Farm points without real spend | V2+ |
| Guest (remote) | Link payments to steal accrual | V2+ |
| Restaurant staff | Issue fake comps / adjust points | V2+ |
| Partner merchant | Accept voucher without service | V2.5+ |
| Organized ring | Multi-account accrual + resale | V2.5+ |
| Insider | Manipulate ledger / balances | V2+ |

**MVP note:** With **no accrual**, loyalty fraud surface is **empty**. Fraud effort focuses on split-pay (other slice). Do not add loyalty UI that creates attack surface before controls exist.

---

## 3. Fraud vectors — earn side

### 3.1 Synthetic payment farming

**Attack:** Colluding staff creates low-value bills, processes fake Mollie payments (refund off-hours), accrues points, redeems, repeat.

| Control | Implementation |
|---------|----------------|
| Accrue only on `settlement_status != CHARGEBACK` | Delay accrual until T+2 or chargeback window subset |
| Velocity cap | Max 3 accruals per `user_id` per venue per day |
| Minimum eligible spend | e.g. €5 |
| Staff conflict | Staff `user_id` cannot earn at employing venue |
| Refund clawback | Automatic `REVERSAL` on refund webhook |
| Anomaly alert | >500 points earned/day across venue → ops |

**Numeric example:**

| Day | Pattern | Flag |
|-----|---------|------|
| Mon | 10× €5 payments, same user, same waiter | Block accrual #4+ |
| Tue | €200 payment, full refund 1h later | Reversal −200 points if accrued |

### 3.2 Split-pay gaming for points

**Attack:** Four fake participants; one real payer; split €100 bill four ways; each account earns 25 points on €25 eligible.

| Control | Notes |
|---------|-------|
| Accrue on **actual payment**, not claim | Already in ledger model |
| One accrual per `payment_id` | Idempotency |
| Device fingerprint clustering | Multiple “guests” same device → accrual review |
| Waiter-activated token | Reduces remote join (split-engine) |

**Weak assumption challenged:** “Points on every participant’s share” is correct economically but enables micro-splits. **Mitigation:** accrual requires **verified account** (email) in V2, not nickname.

### 3.3 Retroactive link abuse

**Attack:** User links account to stranger’s payment within 24h window.

| Control | |
|---------|--|
| Same `guest_device_id` required for retro-link | |
| Max 1 retro-link per payment | |
| Notification email to payer’s address on link | |

### 3.4 Overpay farming (if ever enabled)

**Attack:** Overpay €5 on €50 bill to get €5 wallet + points on €55.

| Control | |
|---------|--|
| **Do-Not-Build wallet** | Primary control |
| If instant discount only: cap €3 per visit | |
| No points on overpay portion | |
| No multiplier campaigns tied to overpay | **Never** (scope-boundary §8) |

---

## 4. Fraud vectors — burn side

### 4.1 Double redemption

**Attack:** Redeem same offer twice via race on API.

| Control | |
|---------|--|
| Optimistic lock on `points_balance` | |
| Redemption idempotency key | |
| Staff confirm step for high-value offers | |

### 4.2 Staff comp fraud

**Attack:** Waiter confirms redemptions for friends without points deduction.

| Control | |
|---------|--|
| Manager PIN for offers >100 points | |
| Audit log: `staff_id` on confirm | |
| Daily report: redemptions vs accruals ratio | |

### 4.3 Negative balance exploit

**Attack:** Redeem 100 points, trigger chargeback, keep comp.

| Control | |
|---------|--|
| Freeze redemptions if payment disputed | |
| Claw back via `REVERSAL`; ops for physical comp | |
| Block account at −50 points | |

### 4.4 Coalition voucher resale

**Attack:** Redeem points for partner voucher; sell on marketplace.

| Control | |
|---------|--|
| Non-transferable codes bound to `user_id` | |
| ID check at partner for high value (V2.5) | |
| Short voucher TTL (72h) | |
| One active voucher per user | |

---

## 5. Fraud vectors — account layer

### 5.1 Multi-account / email churn

| Signal | Action |
|--------|--------|
| Same device, 5+ accounts/week | CAPTCHA + delay accrual |
| Disposable email domains | Block list |
| Identical payment card across accounts | Mollie metadata if available → link |

### 5.2 Account takeover

| Control | |
|---------|--|
| Magic link expiry 15 min | |
| Notify on new device login | |
| Freeze loyalty on email change 24h | |

---

## 6. Fraud response state machine

```
                    ┌─────────────┐
         accrue     │   ACTIVE    │
        ──────────► │             │
                    └──────┬──────┘
                           │
              rule hit (velocity / chargeback / manual)
                           │
                           ▼
                    ┌─────────────┐
                    │   REVIEW    │ accrual paused; burn blocked
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         CLEARED      FROZEN       CLOSED
         resume       ops only     forfeiture + ban
```

| Status | Accrual | Redemption | Display balance |
|--------|---------|------------|-----------------|
| ACTIVE | Yes | Yes | Yes |
| REVIEW | Queue | No | Yes |
| FROZEN | No | No | Yes (read-only) |
| CLOSED | No | No | Hidden |

---

## 7. Monitoring metrics (V2+)

| Metric | Alert threshold |
|--------|-----------------|
| Accrual/refund ratio | >15% weekly at venue |
| Points issued per € revenue | >1.5× program config |
| Redemptions without prior accrual | Any |
| Retro-link success rate | >5% of payments |
| Mean time payment→refund | <2h recurring pattern |
| Coalition voucher unredeemed rate | >80% (partner fraud signal) |

---

## 8. VAT (BTW) — Netherlands hospitality context

**Disclaimer:** Tax determination requires restaurant’s accountant and Belastingdienst guidance. This section flags **open questions**, not filing instructions.

### 8.1 NL VAT rates (reference)

| Category | Rate | Split-pay relevance |
|----------|------|---------------------|
| Food (most on-premise) | 9% | Bill lines |
| Alcohol | 21% | Often excluded from loyalty base |
| Service charge | Often 9% | Venue policy |

Platform displays line VAT; loyalty must **not** distort VAT shown on guest payment.

### 8.2 VAT on earn (accrual) — open questions

**Question VAT-E1:** Is issuing **free points** (no guest payment for points) a taxable supply?

| View | Argument |
|------|----------|
| Not immediately taxable | Promotional grant; no consideration |
| Taxable when redeemed | Discount reduces taxable price of supply |
| Taxable at accrual | If points sold for money — **we reject paid points** |

**Working policy:** Points are **free promotional grants** tied to prior taxable meal payment. Accrual event **likely not** a separate VAT supply. **Confirm with tax advisor.**

**Question VAT-E2:** Earn base includes amounts that include VAT?

| Approach | Example |
|----------|---------|
| Points on **gross incl. VAT** (simple) | €38.40 payment → 38 points |
| Points on **net ex-VAT** (accounting-pure) | Requires VAT split per line |

**Recommendation:** Match **guest-facing spend** (incl. VAT on eligible lines) for UX simplicity; store `eligible_cents` and VAT breakdown in `metadata_json` for audit.

**Numeric example:**

| Line | Incl. VAT | VAT 9% | Eligible for points |
|------|-----------|--------|---------------------|
| Burger | €15.85 | €1.31 | €15.85 |
| Wine | €32.00 | €5.55 (21%) | €0 if alcohol excluded |
| **Total eligible** | **€15.85** | | **15 points** |

### 8.3 VAT on burn (redemption) — open questions

**Question VAT-B1:** Free item redemption (100 points = coffee)

| Treatment sketch | Effect |
|--------------------|--------|
| Reduce consideration of current sale | Guest buys €30 meal, redeems coffee; coffee line €0 comp |
| Separate supply at €0 | May require justification as promo |

Restaurant issues **credit note / discount line** in POS (manual MVP; integrated V2).

**Question VAT-B2:** Percent discount redemption (10% off bill)

Discount applies **before** VAT calculation on remaining taxable amount per NL rules for price reductions — **venue POS responsibility**.

**Question VAT-B3:** Cross-venue coalition voucher

Partner B accepts voucher from points earned at Restaurant A:

| Complexity | |
|------------|--|
| Who invoices whom? | Platform settlement |
| VAT on voucher face value? | Multi-purpose voucher rules — **high complexity** |
| Why deferred? | Primary reason coalition is V2.5+ |

### 8.4 VAT on overpay (rejected wallet)

If overpay were stored as EUR credit:

| Issue | |
|-------|--|
| Multi-purpose voucher VAT timing | On issue vs redemption |
| Partial redemption | Breakage VAT treatment |

**Policy:** Avoid entirely by not building wallet.

**Instant same-bill discount reframe:** Overpay €5 matched by €5 discount = **no change in net consideration** for VAT purposes (still one supply of meal). **Likely simplest VAT path** — confirm with advisor.

### 8.5 VAT on tips

Tips via Mollie pass-through are **not** loyalty earn base and generally **outside** BTW for voluntary tips (venue configuration dependent). Do not award points on tip to avoid perceived “tip tax” UX controversy.

---

## 9. VAT decision table (engineering)

| Event | Store in metadata | Display to guest | POS export |
|-------|-------------------|------------------|------------|
| Accrual | `eligible_cents`, `vat_cents_by_rate` | Points only | N/A |
| Redemption comp item | `offer_id`, `nominal_value_cents` | “Free coffee redeemed” | Comp reason code |
| Redemption % off | `discount_bps`, `applied_to_cents` | “10% off applied” | Discount line |
| Refund + reversal | `refund_id`, `points_reversed` | Email notice | N/A |

---

## 10. Open questions register (tax + fraud)

| ID | Question | Owner | Blocker for |
|----|----------|-------|-------------|
| VAT-E1 | Taxable supply at accrual? | Tax advisor | V2 launch |
| VAT-E2 | Gross vs net earn base | Product + advisor | V2 config |
| VAT-B3 | Coalition voucher VAT | Advisor + legal | V2.5 |
| FRAUD-1 | Accrual delay vs instant | Product | V2 |
| FRAUD-2 | Chargeback window length NL cards | Ops | V2 |
| FRAUD-3 | Partner voucher KYC threshold | Legal | V2.5 |

---

## 11. MVP / V1.1 fraud posture

| Risk | MVP handling |
|------|--------------|
| Loyalty farming | N/A — no points |
| Overpay abuse | N/A — no overpay |
| Receipt email harvesting | Rate limit; double opt-in marketing |
| Fake accounts for history | Low value; CAPTCHA on signup |

**Principle:** Do not ship loyalty mechanics without the controls in §3–7.

---

## 12. Gamification — permanent Never

Per [scope-boundary.md](../../product/scope-boundary.md) §8:

| Rejected mechanic | Fraud reason |
|-------------------|--------------|
| Pay 10% extra → rank up | Incentivizes fake spend |
| Streak bonuses on payment volume | Collusion with staff |
| Referral bonus on payment session | Synthetic sessions |
| Leaderboards by spend | Privacy + farming |

---

## 13. Worked fraud scenario (V2)

**Setup:** Restaurant “De Rekentafel”, earn 1pt/€1, offer 100pts = €10 dessert.

1. Fraudster creates 3 verified accounts.  
2. One real dinner €120; split 3 ways €40 each.  
3. Each earns 40 points (120 total).  
4. Combined balance 120 — not enough for 100pt offer individually.  
5. **Control:** Redemption per account; cannot pool points.  
6. Fraudster redeems one dessert on one account (100pts) — needs 100 earn on **that** account.  
7. Only 40 earned → **blocked**.  

**Without per-account isolation:** 120pts could redeem — **must enforce account-scoped balance**.

---

## 14. Acceptance criteria mapping

| Criterion | Section |
|-----------|---------|
| Farming risks | §3–5, §12 |
| VAT-on-earn open questions | §8.2 |
| VAT-on-burn | §8.3 |
| Overpay fraud | §3.4, §8.4 |
| MVP exclusion | §11 |

---

*Slice ownership: Part 7 — Loyalty Economy. File: `docs/domain/loyalty/fraud-and-vat.md`.*
