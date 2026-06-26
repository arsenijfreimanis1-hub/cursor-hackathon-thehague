# MVP vs Long-Term Loyalty Policy

**Slice:** Part 7 — Loyalty Economy and Overpay Reframe  
**Cross-references:** [mvp-roadmap.md](../../product/mvp-roadmap.md), [scope-boundary.md](../../product/scope-boundary.md), [rewards-ledger-model.md](./rewards-ledger-model.md), [regulatory-framing.md](./regulatory-framing.md)

---

## 1. Policy statement

The Netherlands pilot proves **collaborative split-pay**, not loyalty economics. Loyalty features are **sequenced by regulatory risk and cold-start reality**, not by master-prompt enthusiasm.

**Hard exclusions (all phases until counsel + separate PRD):**

- Stored-value wallet / overpay-as-cash-balance  
- Cross-restaurant coalition marketplace  
- Gamified overpay or pay-to-earn multipliers  
- Platform points redeemable like currency  

---

## 2. Phase comparison matrix

| Dimension | MVP (pilot) | V1.1 (3–10 venues) | V2.0 (venue loyalty) | V2.5+ (coalition) |
|-----------|-------------|---------------------|------------------------|-------------------|
| **Primary goal** | Split-pay PMF | Ops efficiency + repeat receipts | Retention at enrolled venues | Network discounts |
| Guest account | Not required | Optional email login | Same | Same + partner SSO optional |
| Visit history | No | Single-venue receipts | + points on visits | Cross-venue (consent) |
| Points earn | **No** | **No** | Yes, venue-scoped | Yes + partner earn rules |
| Points burn | **No** | **No** | Same-venue offers only | Partner vouchers |
| Overpay UI | **Hidden** | **Hidden** | Optional reframe only | Coalition-funded promos |
| Ledger writes | Zero | Zero (`visit_records` only) | Full accrual/burn | Partitioned coalition ledger |
| Legal gate | SaaS on Mollie | GDPR account DPA | Loyalty legal memo | EMI/partner structure |
| Sales promise | “Pay your share” | “Receipts in your account” | “Stamp card digital” | “City dining rewards” |

---

## 3. MVP policy (8-week pilot)

### 3.1 What ships

| Feature | Behavior |
|---------|----------|
| Anonymous pay | Nickname session; no account |
| Tips | Per-guest tip via Mollie; pass-through to venue |
| Post-pay prompt | **No** “Save points” — **optional** “Email me receipt” only if trivial to add; otherwise defer to V1.1 |
| Admin loyalty config | **Disabled** / hidden |
| Schema | `rewards_*` tables may exist; **no runtime writes** |

### 3.2 What is forbidden in MVP

| Forbidden | Rationale |
|-----------|-----------|
| Points balance UI | Implies program before PMF |
| Overpay toggle (+10%) | EMI risk + distracts waiters |
| “Join loyalty” pre-pay friction | Drops conversion |
| Partner redemption links | Cold-start; no partners |
| Visit history requiring account before pay | Conversion killer |

### 3.3 MVP success metrics (loyalty-specific)

Loyalty is **not** measured in MVP. Success = split-pay metrics in [mvp-roadmap.md](../../product/mvp-roadmap.md).

**Anti-metrics (watch for scope creep):**

- Restaurant asks for stamp card → log as V2 demand signal, do not build  
- Guests ask for “credit next time” → explain no wallet policy  

### 3.4 Weak assumption challenged

**Assumption:** “Minimal loyalty in MVP increases retention.”  
**Challenge:** At one venue, unauthenticated table guests will not return because of 18 points. Retention requires **trustworthy splits** first. Flow K diagram showing MVP accrual is **superseded by this policy** — accrual moves to V2.

---

## 4. V1.1 policy (post-pilot, pre-loyalty)

### 4.1 What ships

| Feature | Behavior |
|---------|----------|
| Optional account | Email + magic link after payment or from account page |
| Visit history | `visit_records` per venue: date, venue, total, receipt link |
| Receipt email | PDF or link; no points line |
| Marketing consent | Separate checkbox; default off (GDPR) |
| Retroactive link | Link last 24h payment on same device → **visit only**, not points |

### 4.2 What remains off

| Off | Until |
|-----|-------|
| Points accrual | V2 legal sign-off |
| Redemption catalog | V2 |
| Overpay | Legal reframe doc approved |
| Cross-venue history | V2 coalition |

### 4.3 V1.1 UX — post-payment screen

```
Payment successful ✓
─────────────────────
[ Email me this receipt ]     ← primary optional action
[ Done ]

(No points teaser)
(No wallet)
(No +10% overpay)
```

### 4.4 Data retention

| Data | Retention |
|------|-----------|
| Anonymous session PII | 90 days post-close |
| Linked account visits | Until erasure request |
| Marketing prefs | Until withdraw consent |

---

## 5. V2.0 policy — venue loyalty (first earn/burn)

### 5.1 Entry criteria (all required)

1. ≥70% split-pay completion at **≥3 venues** for 4 consecutive weeks  
2. Signed loyalty legal memo (non-e-money design)  
3. Restaurant contract clause: venue funds redemptions or accepts platform promo subsidy  
4. Fraud rules from [fraud-and-vat.md](./fraud-and-vat.md) implemented  
5. Ops runbook for refund ↔ point reversal  

### 5.2 Program design defaults

| Parameter | Default |
|-----------|---------|
| Earn rate | 1 point / €1 eligible spend |
| Eligible base | Food + drink excl. tip |
| Expiry | 365 days |
| Transfer | Disabled |
| Cross-venue burn | Disabled |
| Max bonus campaign | +20 points per visit (not % of bill) |

### 5.3 Venue admin capabilities

- Enable/disable program  
- Configure earn exclusions (alcohol, service charge)  
- CRUD in-venue offers (points → free item / % off)  
- View liability dashboard (outstanding points × internal planning rate)  

### 5.4 Guest capabilities

- See balance and history  
- Redeem at **same venue** during payment session or at counter (staff confirm)  
- Pre-pay points estimate if logged in  

### 5.5 Overpay in V2.0

**Still no wallet.** Optional mechanics (pick **one** after legal review):

| Mechanic | User story | Stored balance? |
|----------|------------|-----------------|
| Round-up tip | “Round my €42.24 to €43 for staff” | No |
| Charity round-up | “Donate €0.76 to [charity]” | No |
| Bonus points purchase | **Rejected** — pay for points = stored value risk |
| Instant on-bill discount | Venue runs “pay €5 extra, get €5 off dessert now” | No — same checkout |

---

## 6. V2.5+ policy — coalition (long-term)

### 6.1 Preconditions

| Precondition | Threshold |
|--------------|-----------|
| Venue density | ≥25 NL venues in same metro or brand coalition |
| Partner pipeline | ≥5 non-restaurant partners OR ≥10 restaurant partners with signed deals |
| Legal structure | EMI partner OR closed-loop issuer contract |
| Ops headcount | Dedicated partner success + fraud analyst |

### 6.2 Coalition mechanics (design target)

```
Earn at Venue A (points)
    → Burn as voucher at Partner B (separate settlement)
    → Platform never shows EUR wallet; shows "450 points → €5 off at Partner B"
```

**Internal planning rate** may exist for partner settlement — **never** guest-facing EUR equivalence on balance.

### 6.3 Settlement sketch

| Event | Money flow |
|-------|------------|
| Guest pays meal | Mollie → Restaurant (unchanged) |
| Guest redeems partner voucher | Partner invoices coalition fund OR platform marketing budget |
| Breakage | Contract-defined split platform/venue/partner |

### 6.4 Coalition Do-Not-Build until preconditions met

- Public discovery feed tied to points  
- Peer-to-peer point transfer  
- Crypto-funded coalition pool  
- “Overpay 10% to unlock city-wide wallet”  

---

## 7. Overpay-to-rewards — explicit Do-Not-Build register

| Variant | Tag | Replacement |
|---------|-----|-------------|
| EUR balance after overpay | **Never** | Tips (MVP) |
| Platform dining wallet | **Never** | Venue points (V2) |
| Multi-merchant credit from overpay | **Never** | Coalition vouchers (V2.5+) |
| Gamified “level up by overpaying” | **Never** | — |
| Refundable overpay credit | **Never** | Instant discount same bill (legal review) |

**Reframe narrative for stakeholders:**

> “We don’t hold your money. We help you pay your share fast, optionally save receipts, and later earn **non-cash** rewards at places you already visit.”

---

## 8. Feature flag and API policy

| Flag | MVP | V1.1 | V2 |
|------|-----|------|-----|
| `loyalty.enabled` | `false` | `false` | `true` per venue |
| `loyalty.accrual_on_payment` | `false` | `false` | `true` |
| `loyalty.redemption` | `false` | `false` | `true` |
| `accounts.visit_history` | `false` | `true` | `true` |
| `checkout.overpay_toggle` | `false` | `false` | `false` until REG-004 |
| `coalition.enabled` | `false` | `false` | `false` until V2.5 gate |

API endpoints for `/v1/loyalty/*` return **404** or **501** in MVP — not empty balances (avoids implying feature exists).

---

## 9. Restaurant sales talking points

| Question | Answer |
|----------|--------|
| “Stamp card on pilot?” | Not yet — we prove split-pay first. |
| “Can guests prepay credit?” | No stored wallet — regulatory and ops simplicity. |
| “Cross-promo with café next door?” | Roadmap after venue loyalty works at your site. |
| “Tip pooling?” | MVP supports per-guest tip; pool reporting V1.1. |

---

## 10. Migration path (when V2 turns on)

1. Enable `VenueLoyaltyProgram` for opt-in pilot venue  
2. **No retroactive points** for V1.1 visits unless explicit promo (avoid liability surprise)  
3. Announce expiry policy day-one  
4. Staff training: redemption confirmation flow  
5. Monitor fraud metrics first 30 days  

---

## 11. Document conflict resolution

| Source | Says | This policy |
|--------|------|-------------|
| Master prompt | Loyalty + overpay in vision | Vision only; not MVP |
| flow-k-loyalty.mmd | MVP accrual | **Superseded** — accrual V2 |
| entity-dictionary | rewards V1.1 preview schema | Schema OK; writes V2 |
| scope-boundary §2 | No earn MVP; history V1.1 | **Aligned** |

---

## 12. Acceptance checklist (slice Part 7)

- [x] Overpay-as-cash-balance marked Do-Not-Build for MVP  
- [x] MVP = optional account deferred; visit history V1.1; no points  
- [x] V2 coalition separated with preconditions  
- [x] Reframes documented (tip, instant discount, non-monetary points)  
- [x] EMI risk flagged in [regulatory-framing.md](./regulatory-framing.md)  

---

*Slice ownership: Part 7 — Loyalty Economy. File: `docs/domain/loyalty/mvp-vs-longterm-policy.md`.*
