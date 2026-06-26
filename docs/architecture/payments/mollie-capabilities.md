# Mollie Capability Analysis — Table Split-Pay Platform

**Purpose:** Concrete assessment of Mollie APIs and payment methods for Netherlands-first MVP and post-MVP scaling.

**Sources:** Mollie public documentation (Payments API, Connect, iDEAL product page, settlement support articles). Verify pricing and feature flags with Mollie account manager before pilot contract.

---

## 1. API surface relevant to this product

| API / feature | Use in product | MVP |
|---------------|----------------|-----|
| **Payments API** `POST /v2/payments` | Guest checkout | **Required** |
| **Payments API** `GET /v2/payments/{id}` | Webhook fulfillment, return URL poll | **Required** |
| **Refunds API** `POST /v2/payments/{id}/refunds` | Partial / full guest refunds | **Required** |
| **Methods API** `GET /v2/methods` | Show iDEAL + cards + wallets available | **Required** |
| **Connect OAuth** (Platforms) | Onboard restaurant orgs | **Required (Model A)** |
| **Client Links API** | Prefill restaurant KYC | Recommended |
| **Onboarding / Capabilities API** | Block go-live until `payments` enabled | Recommended |
| **Connect Split Payments** `routing[]` | Platform bps at capture | Post-MVP / fallback |
| **Delayed Routing** | Route within 90 days | **Not needed** (dine-in immediate) |
| **Orders API** | Multi-shipment e-commerce | **Not used** (wrong model) |
| **Subscriptions API** | SaaS billing to restaurants | Optional (Mollie or separate) |
| **Settlements API** | Payout ↔ payment reconcile | V1.1 |
| **Balance API** | Restaurant payout visibility | V1.1 |
| **Classic webhooks** | Payment status | **Required** |
| **Next-gen webhooks** + signature | Non-payment events | Optional later |

---

## 2. Payment methods — Netherlands MVP matrix

### 2.1 Primary methods (enable day one)

| Method | API name | Min | Max (documented) | Session timeout | Chargeback risk | Partial refund | Multi partial refund | Recurring | NL guest fit |
|--------|----------|-----|------------------|-----------------|-----------------|----------------|----------------------|-----------|--------------|
| **iDEAL** | `ideal` | €0.01 | €50,000 | **15 min** | **None** | Yes | Yes | No (first pay only) | **Primary** |
| **Credit card** | `creditcard` | €0.01 | Profile limit | Checkout session | **Yes** (~120 days dispute window via scheme) | Yes | Yes | Possible | Secondary (tourists) |
| **Apple Pay** | via card wallet | — | — | Wallet | Card chargeback rules | Yes | Yes | — | High mobile UX |
| **Google Pay** | via card wallet | — | — | Wallet | Card chargeback rules | Yes | Yes | — | High Android UX |

### 2.2 Optional / post-MVP methods

| Method | API name | MVP | Reason to defer |
|--------|----------|-----|-----------------|
| PayPal | `paypal` | Optional | Separate payout rail (PayPal-direct); ops complexity |
| Bancontact | `bancontact` | No | Belgium expansion |
| Klarna | `klarna` | **No** | BNPL; T+6 settlement; dine-in mismatch |
| SEPA Direct Debit | `directdebit` | **No** | Wrong UX; T+9; mandate management |
| Gift cards | `giftcard` | No | Issuer-specific settlement |
| in3 | `in3` | No | Installments regulatory/UX mismatch |

### 2.3 Method selection UX recommendation

```
Default checkout order (NL venue):
1. iDEAL (pre-selected copy: "Pay with your bank")
2. Apple Pay / Google Pay (if device supports)
3. Credit / debit card
```

**Rationale:** Maximize iDEAL share → faster settlement, zero chargebacks, lower ops burden.

---

## 3. iDEAL deep dive (Netherlands critical path)

| Property | Value | Product impact |
|----------|-------|----------------|
| Currency | EUR only | Matches MVP |
| Country | NL consumer banks | 100% pilot market |
| Merchant location | EEA, UK, CH | Platform/restaurant eligible |
| Capture | Auto-capture | No auth/capture split needed |
| Settlement to available | **Next business day** | Train restaurants on T+1 not instant |
| Refund window | 365 days | Sufficient for hospitality disputes |
| Failed payment | `failed` / `expired` | Release allocation; guest retry |
| Consumer cancel on method pick | May redirect to method picker | Handle `open` longer than expected |

**Weak assumption challenge:** Master prompt implies "partial payments" as a Mollie feature. **Correction:** iDEAL supports partial **refunds**, not partial **capture** of a single open authorization for multi-payer table pay. Table partial pay = **multiple Payment objects**.

---

## 4. Cards and wallets

### 4.1 Settlement delays (Mollie documented)

| Rail | Pending → available (default) | With Revenue Day T+3 |
|------|----------------------------|----------------------|
| Credit cards | ~4–5 business days | T+3 harmonized |
| Apple Pay / Google Pay | Same as underlying card | Same |

### 4.2 Chargebacks

| Fact | Implication |
|------|-------------|
| Payment `status` stays `paid` on chargeback | Webhook handler must call `hasChargebacks()` separately |
| Partial chargebacks possible | Track `amountChargedBack` per `tr_xxx` |
| Merchant of record liable | Restaurant bears loss; platform provides audit trail only |

### 4.3 3-D Secure

Mollie handles SCA for cards. Platform uses hosted checkout — **no PCI SAQ-D**.

---

## 5. "Partial payments" — terminology disambiguation

| Term | Meaning in Mollie | Meaning in this product |
|------|-------------------|-------------------------|
| Partial refund | Refund < payment amount | Admin adjusts guest overpay |
| Multiple partial refunds | Several refunds on one `tr_xxx` | Item-level correction |
| Partial capture | Orders API / auth flows | **Not used MVP** |
| Remaining balance | Not a Mollie primitive | **Platform table session state** |

**Architecture rule:** Never create one Mollie Payment for €86.40 and attempt to collect €27 + €22.40 + €22.50 sequentially against it. Create three payments.

---

## 6. Connect: Platforms vs Marketplaces

### 6.1 Connect for Platforms (OAuth) — Model A

| Capability | Details |
|------------|---------|
| Purpose | Act on behalf of restaurant Mollie org |
| Onboarding | Client Links API, co-branded flow |
| Payment creation | OAuth access token → `POST /v2/payments` on restaurant profile |
| Funds destination | Restaurant balance only |
| Platform fee | Off-rail (SaaS invoice) |
| Permissions | `payments.write`, `payments.read`, `refunds.write`, `profiles.read`, `organizations.read`, `onboarding.read` |
| Token storage | Refresh token per restaurant; rotate access token |

**Limits:** Platform cannot unilaterally move money between restaurants. No cross-venue settlement.

### 6.2 Connect for Marketplaces (Split) — Model B

| Capability | Details |
|------------|---------|
| Purpose | Split single payment across orgs |
| Enablement | **Not default** — partner form / account manager |
| Upfront routing | `routing[]` on `POST /v2/payments` |
| Currencies | EUR, GBP (split); delayed routing supports more |
| Route limit | No documented cap on route count |
| Delayed routing | Create routes after `paid`; up to **90 days** |
| Release date | Per-route delay up to 2 years (10 days test) |
| Klarna / PayPal / gift cards | Delayed routing only (not upfront) |

**Split payment example (Model B fallback):**

Guest pays €27.00 (Anna share + tip):

```json
{
  "amount": { "currency": "EUR", "value": "27.00" },
  "routing": [
    {
      "amount": { "currency": "EUR", "value": "26.19" },
      "destination": { "type": "organization", "organizationId": "org_restaurant" }
    },
    {
      "amount": { "currency": "EUR", "value": "0.81" },
      "destination": { "type": "organization", "organizationId": "org_platform" }
    }
  ]
}
```

**Refund complexity:** Refunding €8.00 may require proportional route reversal — confirm with Mollie support before Model B go-live.

### 6.3 Comparison table

| Question | Platforms OAuth | Marketplaces Split |
|----------|-----------------|-------------------|
| Who holds KYC? | Each restaurant | Each restaurant + platform |
| Guest sees merchant name | Restaurant profile | Restaurant profile (verify Mollie statement descriptor) |
| Platform txn revenue | Separate billing | In-rail split |
| Feature flag default | **On** | **Off** |
| Pilot complexity | Lower | Higher |

---

## 7. Webhooks (capability summary)

| Event | Classic webhook | Action |
|-------|-----------------|--------|
| Payment `paid` | `id=tr_xxx` | Fulfill allocation |
| `failed` / `canceled` / `expired` | Yes | Release locks |
| Refund `processing` / `refunded` / `failed` | Yes | Adjust ledger |
| Chargeback received | Yes | Ops queue |
| Status in POST body | **No** — ID only | Must GET payment |

Details: [webhook-reconciliation.md](./webhook-reconciliation.md).

---

## 8. Refunds API capabilities

| Property | Value |
|----------|-------|
| Full refund | Up to `amountRemaining` |
| Partial refund | Multiple until exhausted |
| Payment status after refund | Stays `paid` until fully refunded |
| Webhook | Refund status transitions |
| Failed refund | Insufficient Mollie balance — restaurant must fund account |

**Split-bill rule:** Refund scope = one guest's `tr_xxx`. Cross-guest redistribution is platform ledger logic, not Mollie.

---

## 9. Settlement and payouts

### 9.1 Balance types

| Balance | Description |
|---------|-------------|
| Pending | Paid but settlement delay not elapsed |
| Available | Eligible for payout to IBAN |
| Reserved | Rolling reserve (high-risk merchants) |

### 9.2 Payout frequency options (merchant dashboard)

| Setting | Effect |
|---------|--------|
| Daily / weekly / monthly | Batch available balance |
| Revenue Day Payouts T+1 | Harmonize methods; daily business payouts |
| Revenue Day Payouts T+3 | Slower harmonization; better for card-heavy |

### 9.3 Liability / rolling reserve

Mollie may hold % of transactions for high-risk profiles. Restaurants with chargeback spikes may see delayed available balance — surface in admin FAQ.

---

## 10. Limits, quotas, and operational constraints

| Limit | Documented value | Product handling |
|-------|------------------|------------------|
| iDEAL max per txn | €50,000 | Above any table bill; no concern |
| iDEAL min | €0.01 | Enforce min guest share ≥ €0.01 |
| iDEAL session | 15 minutes | UI timer + retry |
| API rate limits | Mollie standard (undocumented exact) | Exponential backoff; queue creates |
| Test mode | Separate API keys | Never mix test/live webhook URLs |
| Metadata size | Keep minimal | Store heavy audit in platform DB |
| EUR only MVP | — | No FX |

---

## 11. Pricing (indicative — confirm with Mollie)

Mollie publishes method-specific transaction fees (iDEAL flat fee typical; cards % + fixed). Platform SaaS fee is separate in Model A.

| Cost bearer | Model A | Model B |
|-------------|---------|---------|
| Mollie txn fee | Restaurant | Usually restaurant portion |
| Platform revenue | Monthly SaaS | SaaS + optional bps split |
| Chargeback fee | Restaurant | Restaurant (+ ops support tier) |

**Pilot negotiation:** Ask Mollie for hospitality / platform volume pricing and Connect enablement timeline if Model B is contingency.

---

## 12. Test strategy

| Test | Method |
|------|--------|
| iDEAL happy path | Mollie test mode + test bank |
| Expired payment | Wait 15 min or simulate |
| Webhook retry | Replay same `id=tr_xxx` POST |
| Partial refund | Refund €5 of €27 test payment |
| OAuth token refresh | Force expiry in staging |
| Bill version conflict | Pay with stale allocation metadata |
| Split routing | Model B sandbox only after enablement |

---

## 13. Known gaps / verify with Mollie

| Item | Question for account manager |
|------|------------------------------|
| Split refund behavior | Pro-rata route reversal on partial refund? |
| Statement descriptor | Guest bank shows restaurant name? |
| Multi-profile restaurants | One org, multiple venues — profile per location? |
| Platform liability | Contractual MoR clarification for Connect Platforms |
| Revenue Day eligibility | All NL hospitality merchants? |
| Apple Pay domain verification | Per restaurant profile vs platform |

---

## 14. MVP capability verdict

| Requirement | Mollie support | Notes |
|-------------|----------------|-------|
| iDEAL checkout | **Native** | Primary |
| Cards + wallets | **Native** | Chargeback ops |
| Multi-guest table pay | **App-layer** | Multiple payments |
| Partial table balance | **App-layer** | Not Mollie primitive |
| Per-guest tip | **Metadata** | Pass-through |
| Restaurant settlement | **Native** | T+1 iDEAL |
| Webhook reconciliation | **Native** | ID-only POST |
| Partial refunds | **Native** | Per payment |
| Platform bps at pay | **Split Payments** | Partner enablement |
| Crypto | **Not via Mollie** | Separate rail doc |
| Stored-value wallet | **Out of scope** | Regulatory |

**Conclusion:** Mollie fully covers MVP **if** partial table pay is implemented in platform ledger, not expected as a PSP primitive. Recommend Model A (OAuth per restaurant) for pilot; keep Model B capability analysis for pricing experiments in V1.1.
