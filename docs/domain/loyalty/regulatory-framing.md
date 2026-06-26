# Regulatory Framing — Loyalty, Overpay, and Stored Value

**Slice:** Part 7 — Loyalty Economy and Overpay Reframe  
**Jurisdiction:** Netherlands / EU (PSD2, Wft, EU E-Money Directive 2009/110/EC as implemented in NL)  
**Disclaimer:** Product architecture document, not legal advice. Counsel review required before V2 loyalty launch or any overpay mechanic.

**Cross-references:** [scope-boundary.md](../../product/scope-boundary.md) §3, [payment-architecture.md](../../architecture/payments/payment-architecture.md), [flows-a-o.md](../../flows/flows-a-o.md) Flow L

---

## 1. Executive summary

| Product mechanic | Regulatory bucket | MVP | V2 path |
|------------------|-------------------|-----|---------|
| Split-pay via Mollie to merchant account | PSD2 payment initiation / SaaS on merchant PSP | **Ship** | Mollie Connect |
| Tip pass-through | Payment to merchant; wage/tax via venue | **Ship** | Same |
| Optional account + visit history | GDPR data controller/processor | V1.1 | Same |
| Venue-scoped non-transferable points | Promotional loyalty (low risk if designed correctly) | No | Legal review → ship |
| Overpay → **spendable cash balance** | **E-money / EMI** | **Never** | **Never** without license |
| Overpay → **multi-merchant wallet** | **E-money + possibly PSD2** | **Never** | Coalition only with EMI or partner structure |
| Cross-venue redemption marketplace | Stored value + marketplace ops | **Never** MVP/V1.1 | V2+ with dedicated legal entity |

**Primary recommendation:** MVP = **no loyalty ledger, no overpay UI**. V1.1 = **visit history only**. V2 = **venue points** with explicit non-monetary design. Kill **overpay-as-cash-balance** permanently unless the company obtains EMI or structurally separates value through a licensed partner.

---

## 2. PSD2 and payment facilitator scope

### 2.1 MVP posture (target)

```
Guest ──iDEAL/card──► Mollie ──► Restaurant Mollie balance ──► Restaurant bank
         ▲
         └── Platform creates payment via merchant OAuth key; does NOT hold funds
```

| Role | MVP intent |
|------|------------|
| Restaurant | Merchant of record; Mollie contract holder |
| Platform | Software provider (SaaS); payment initiation on behalf of merchant |
| Mollie | Licensed PSP / payment institution |

**PSD2 relevance:** Guest checkout is **payment initiation** through a licensed PSP. Platform avoids becoming payment institution by:

- Not holding guest funds overnight  
- Not pooling payers’ money on platform balance for later disbursement (without license)  
- Not issuing spendable payment credentials

### 2.2 Scope creep triggers (avoid)

| Trigger | Why it expands PSD2 / EMI |
|---------|---------------------------|
| Platform balance receives guest payments then pays restaurants | Money remittance / PI |
| Guest “wallet balance” used at multiple merchants | E-money |
| Platform advances value to guest before settlement | Credit / e-money |
| Overpay stored and applied to future checks platform-wide | Stored value |

### 2.3 Mollie Connect (V2)

Platform fee via **split payments** or **application fees** still routes through Mollie’s licensed infrastructure. Does **not** by itself authorize a dining wallet — only fee collection architecture changes.

---

## 3. E-money and EMI risk (critical)

### 3.1 EU / NL e-money definition (practical test)

E-money exists when users receive **monetary value** stored electronically that:

- Is issued on receipt of funds  
- Is accepted by persons other than the issuer (or issuer’s agents)  
- Is used for payment  

**AFM supervision:** Issuing e-money in NL generally requires **Electronic Money Institution (EMI)** authorization under Wft.

### 3.2 Master-prompt overpay mechanic — classification

**Proposed:** Guest pays bill + 10%; surplus becomes “platform credit / dining wallet” redeemable at partner restaurants.

| Design element | E-money indicator |
|----------------|-------------------|
| Surplus denominated in EUR | Strong |
| Balance persists across transactions | Strong |
| Redeemable at third-party merchants | Strong |
| Transferable or feels like cash | Strong |
| Refundable to bank account | Very strong |

**Conclusion:** This is **stored-value e-money**, not “loyalty points,” regardless of marketing label.

**Do-Not-Build (MVP, V1.1, and by default forever):** `wallet_balance_cents`, `dining_credit_eur`, or any UI showing “You have €4.50 to spend.”

### 3.3 EMI risk matrix

| Architecture | EMI risk | Notes |
|--------------|----------|-------|
| Points with no EUR display, non-transferable, single venue | **Low–medium** | Still needs promo/gift rules review |
| Points redeemable at 10+ unaffiliated venues | **High** | Functionally multi-purpose stored value |
| EUR voucher issued at overpay time | **Medium–high** | Gift voucher rules may apply |
| Platform holds overpay in segregated account for future use | **Very high** | Classic e-money |
| Immediate donation to charity (one-way) | **Low** | No stored balance |
| Immediate extra tip to staff | **Low** | Payment pass-through |

---

## 4. Gift voucher and discount voucher framing (NL)

### 4.1 Wet op de kansspelen / consumer law adjacent

NL implements EU **Gift Vouchers Directive** principles. Single-purpose vs multi-purpose vouchers differ in VAT and reporting.

| Voucher type | Definition sketch | Platform fit |
|--------------|-------------------|--------------|
| Single-purpose | Redeemable only for one venue’s goods (known VAT rate) | Same-restaurant instant discount — narrower path |
| Multi-purpose | Redeemable across categories/venues | **EMI-like scrutiny** when platform-wide |

### 4.2 Reframed overpay alternatives (if ever built)

**Option A — Instant matched discount (same visit, same venue)**

Guest pays €50 share; toggles “Support the house +€5.” Restaurant applies **€5 line discount** on same bill before checkout. **No balance remains.**

- Regulatory: Part of single payment/settlement; not stored value  
- UX: Must not promise “€5 for next time”  
- Accounting: Discount expense or marketing promo  

**Option B — Same-venue future discount code**

Overpay generates **single-use code** for **same restaurant only**, 90-day expiry, non-transferable, no cash refund.

- Regulatory: Closer to single-purpose voucher; **legal review required**  
- Still **not MVP**  

**Option C — Non-monetary points (recommended V2 path)**

+10% does **not** add EUR; optionally awards **bonus points** (e.g. +50 points) with no cash equivalence stated.

- Regulatory: Loyalty / promotional program  
- Fraud: Must cap bonuses; see [fraud-and-vat.md](./fraud-and-vat.md)  

**Rejected Option — Platform dining wallet**

Any balance usable at Partner A, B, C → **treat as EMI program** or do not build.

---

## 5. Loyalty points vs e-money — design guardrails

To keep venue points **outside** e-money:

| Guardrail | Requirement |
|-----------|-------------|
| Denomination | Integer points only; never EUR |
| Transfer | Non-transferable |
| Cash-out | No redemption for cash or IBAN transfer |
| Cross-venue | V2.0 same venue only; coalition requires separate legal structure |
| Expiry | Published expiry (e.g. 12 months) |
| Terms | “Promotional reward, no monetary value” |
| Refund | Points clawed on payment refund; no EUR payout for unused points |
| Marketing | No “1 point = €0.01” in consumer-facing copy |

**Weak assumption challenged:** “Points are not money so we can allow overpay to buy points at a discount rate.” If points purchase **multi-merchant redemption**, regulators may impute monetary value from economics, not copy.

---

## 6. Accounting and liability

### 6.1 MVP (no loyalty)

No loyalty liability on platform or restaurant balance sheet from points. Revenue = SaaS fees (future) + zero loyalty accrual.

### 6.2 V2 venue points — liability models

| Funding model | Who bears liability | P&L treatment (indicative) |
|---------------|---------------------|----------------------------|
| **Venue-funded** (default) | Restaurant | Marketing expense when redeemed; accrual optional under IFRS vs local GAAP |
| **Platform-funded promo** | Platform | CAC / marketing expense |
| **Co-funded coalition** | Shared | Requires intercompany settlement |

**Points accrual example (venue-funded):**

100 guests earn average 40 points/month; 1 point ≈ €0.01 **internal planning value only** (not shown to guest).

| Metric | Value |
|--------|-------|
| Outstanding points | 120,000 |
| Internal planning liability | €1,200 |
| Redemption rate assumption | 60% |
| Expected cost of rewards | €720/month marketing equiv. |

**Breakage** (expiration): Reduces expected liability — must be disclosed in venue contract if platform manages program.

### 6.3 Overpay wallet accounting (why we reject it)

If platform holds €10,000 aggregate overpay credits:

| Issue | Impact |
|-------|--------|
| Balance sheet | Customer liability (deferred revenue or e-money liability) |
| Revenue recognition | Cannot recognize until redemption or breakage rule applied |
| Insolvency | Guest credit claims against platform |
| Audit | EMI capital requirements if classified as e-money |

**vs tip pass-through:** €0 platform liability — flows to merchant Mollie payment.

### 6.4 Refund interaction

| Scenario | Payment ledger | Points ledger |
|----------|----------------|---------------|
| Full refund | Mollie refund | Full reversal |
| Partial refund | Partial | Proportional reversal |
| Redeemed comp then refund | Ops dispute | Manual adjustment; no automatic EUR clawback from guest |

Chargeback on payment that earned points: freeze account; reverse points; ops queue.

---

## 7. GDPR and profiling

| Data | Phase | Lawful basis (indicative) |
|------|-------|---------------------------|
| Visit history | V1.1 | Contract / legitimate interest + transparency |
| Points balance | V2 | Contract (loyalty terms) |
| Order-derived recommendations | V2+ | **Consent**; DPIA required |
| Cross-venue history | V2+ coalition | Consent + data sharing agreements |

**Minimization:** MVP payment sessions TTL-delete PII at 90 days unless account linked ([scope-boundary.md](../../product/scope-boundary.md)).

Loyalty accounts: retain ledger **7 years** for audit if required by tax/fraud; pseudonymize on erasure request where law permits retention of transactional records only.

---

## 8. Crypto rail (explicit non-scope)

Crypto acceptance is **not** a loyalty workaround. Converting overpay to USDC platform credit is **higher** regulatory surface (MiCA, AML), not lower.

| Path | MVP | Loyalty interaction |
|------|-----|---------------------|
| Mollie fiat | Yes | Points on fiat payment only (V2) |
| Crypto PSP | Never MVP | No “crypto points” or stablecoin wallet |

See [crypto-rail-design.md](../../architecture/payments/crypto-rail-design.md).

---

## 9. Coalition model (V2+ — separate legal program)

Cross-restaurant partner redemption requires:

1. **Legal entity** for coalition (platform or partner bank/EMI)  
2. **Merchant agreements** defining funding, breakage, settlement  
3. **VAT policy** on cross-border rewards (if any)  
4. **AML/KYC** if transfers or high-value redemptions  

**Do not** launch coalition by “sharing points pool” without structure — that is multi-merchant stored value.

### 9.1 Structural options (long-term)

| Model | Platform role | License burden |
|-------|---------------|----------------|
| Venue-only points | SaaS + promo rules | Lowest |
| Closed-loop coalition (NL venues, single issuer partner) | Program manager | Partner EMI |
| Platform EMI | Issuer | Highest capital / compliance |
| Discount marketplace (no stored balance) | Lead-gen / affiliate | Medium consumer law |

---

## 10. Decision log

| ID | Decision | Status |
|----|----------|--------|
| REG-001 | No stored EUR wallet in MVP/V1.1 | **Approved** |
| REG-002 | No overpay UI in MVP | **Approved** |
| REG-003 | Visit history without points in V1.1 | **Approved** |
| REG-004 | Venue-scoped points in V2 after legal memo | **Pending counsel** |
| REG-005 | Overpay → cash balance | **Rejected — Do-Not-Build** |
| REG-006 | Coalition marketplace | **Deferred — separate program** |

---

## 11. Counsel checklist (before V2 loyalty launch)

- [ ] Confirm points program is not e-money under Wft / EMD  
- [ ] Terms of service: no cash value, expiry, venue scope  
- [ ] Gift voucher classification for any discount codes  
- [ ] DPA with venues on guest data for loyalty  
- [ ] Marketing consent separate from loyalty enrollment (GDPR)  
- [ ] Insolvency clause: what happens to points if venue closes  
- [ ] Mollie Connect fee structure vs loyalty funding  

---

## 12. Consumer-facing copy constraints

**Allowed (V2):** “You earned 38 points at De Rekentafel.”  
**Allowed:** “Redeem 80 points for a free coffee — this visit only.”  
**Forbidden:** “Your wallet balance is €12.40.”  
**Forbidden:** “Use your credit at any partner restaurant.” (without coalition legal program)  
**Forbidden:** “Overpay 10% and spend it anywhere.”  

---

*Slice ownership: Part 7 — Loyalty Economy. File: `docs/domain/loyalty/regulatory-framing.md`.*
