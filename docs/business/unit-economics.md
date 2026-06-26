# PART 13C — Unit Economics Sketch

**Product:** Rekentafel / TabSettle  
**Slice:** Monetization — scenario modeling with stated assumptions  
**Last updated:** 2026-06-26

**Mollie fee basis:** [Mollie NL pricing](https://www.mollie.com/nl/pricing?country=nl&currency=EUR) — **€0.32** per successful domestic iDEAL | Wero payment; **2.99% + €0** EEA consumer cards (June 2026 public rates). Restaurant bears guest txn fees in Model A MVP.

---

## 1. Modeling scope

| Included | Excluded |
|----------|----------|
| Per-venue restaurant economics | Guest CAC / loyalty |
| Platform revenue & COGS per venue | POS integration COGS |
| Mollie fee impact on **restaurant** margin | Crypto rail |
| Support, infra, payment ops alloc | Partner marketplace |
| Pilot → Starter → Hybrid phases | Full P&L headcount (directional only) |

**Currency:** EUR. **BTW:** Restaurant GMV figures **incl. VAT** as diners experience; SaaS **excl. BTW** unless noted.

---

## 2. Core assumptions registry

### 2.1 Venue operating assumptions (pilot archetype: "Utrecht bistro")

| Variable | Symbol | Base | Low | High | Source / note |
|----------|--------|------|-----|------|---------------|
| Tables | `T` | 28 | 18 | 40 | Independent full-service |
| Service days / month | `D` | 26 | 24 | 30 | Closed Mon or seasonal |
| Table turns / day (all dayparts) | `turns` | 2.2 | 1.6 | 3.0 | Lunch + dinner |
| **Paid table sessions / month** | `S = T × D × turns` | **1,601** | 691 | 3,600 | Only tables that close a bill |
| Rekentafel attach rate (% sessions using split-pay) | `attach` | 65% | 40% | 85% | Post-training steady state |
| **Active split sessions / month** | `S' = S × attach` | **1,041** | 276 | 3,060 | Billable behavior denominator |
| Avg bill per session | `B` | €86.40 | €62.00 | €124.00 | Matches positioning doc example |
| Avg guests paying per split session | `G` | 3.2 | 2.0 | 4.5 | >1 implies split value |
| Avg guest checkout amount | `A = B / G` | **€27.00** | €31.00 | €27.56 | Derived |
| **Guest checkouts / month** | `C = S' × G` | **3,331** | 552 | 13,770 | Hybrid metering base |
| iDEAL mix (guest checkouts) | `ideal_mix` | 75% | 60% | 85% | NL dine-in default |
| Card/wallet mix | `card_mix` | 25% | 15% | 40% | Tourist-heavy ↑ |

### 2.2 Platform pricing assumptions

| Variable | MVP Starter | V1.1 Hybrid | Enterprise |
|----------|-------------|-------------|------------|
| Monthly SaaS | €59 | €49 | €99/location |
| Per guest checkout | €0 | €0.10 (after 150 incl.) | 10 bps (cap €0.35) |
| Included checkouts | ∞ de facto | 150 | 500 |

### 2.3 Platform COGS assumptions (per venue / month)

| Cost bucket | MVP Starter | Notes |
|-------------|-------------|-------|
| Cloud infra (API, DB, Redis, CDN) | €8 | Shared multi-tenant alloc |
| Mollie webhook / API ops | €2 | No guest txn fee to platform |
| Support (email, 0.5 hr/mo avg) | €25 | €50/hr loaded founder rate → scales to €40 at 50 venues |
| Onboarding amortized | €5 | €150 onboarding / 30 mo |
| Payment reconciliation labor | €3 | Daily job monitoring |
| **Total COGS / venue / mo** | **€43** | Rounded |

*Support scales sub-linearly with playbook — model sensitivity in §5.*

### 2.4 Restaurant time-value assumptions (ROI side)

| Variable | Value | Note |
|----------|-------|------|
| Pay-phase duration today (terminal + split requests) | 14 min median | Observational — **pilot must measure** |
| Pay-phase with Rekentafel | 8 min target | Waiter activates; guests self-serve |
| Minutes saved / split table | **6 min** | `14 − 8` |
| Opportunity value / table-hour | €15 | Conservative cover revenue proxy |
| Value of 6 min saved | **€1.50** | `6/60 × €15` |

---

## 3. GMV and Mollie fee mathematics

### 3.1 Monthly GMV through Rekentafel (restaurant)

```
GMV_R = S' × B
```

| Scenario | S' | B | **GMV_R / mo** |
|----------|-----|--------|----------------|
| Low | 276 | €62 | **€17,112** |
| Base | 1,041 | €86.40 | **€89,942** |
| High | 3,060 | €124 | **€379,440** |

### 3.2 Guest checkouts and Mollie fees (restaurant cost)

**Blended Mollie fee per guest checkout** (`m`):

```
m = ideal_mix × €0.32 + card_mix × (2.99% × A)
```

| Scenario | A | ideal_mix | **m (blended)** |
|----------|---|-----------|-----------------|
| Base | €27.00 | 75% | 0.75×0.32 + 0.25×0.8073 = **€0.442** |
| Low attach | €31.00 | 60% | **€0.425** |
| High tourist cards | €27.56 | 60% | **€0.606** |

**Monthly Mollie guest fees (Rekentafel path):**

```
Mollie_R = C × m
```

| Scenario | C | m | **Mollie_R** |
|----------|---|-----|--------------|
| Low | 552 | €0.425 | **€235** |
| Base | 3,331 | €0.442 | **€1,472** |
| High | 13,770 | €0.606 | **€8,345** |

### 3.3 Counterfactual — terminal-only Mollie (same sessions)

One payment per session @ iDEAL:

```
Mollie_terminal = S' × €0.32
```

| Scenario | S' | **Mollie_terminal** |
|----------|-----|---------------------|
| Low | 276 | **€88** |
| Base | 1,041 | **€333** |
| High | 3,060 | **€979** |

### 3.4 Incremental Mollie cost to restaurant (split-pay tax)

```
ΔMollie = Mollie_R − Mollie_terminal ≈ S' × (G − 1) × m_ideal
```

Using base: **1,041 × (3.2 − 1) × €0.32 ≈ €733/mo** incremental iDEAL-only; full blended **≈ €1,139/mo**.

| Scenario | ΔMollie (blended) | Per split session |
|----------|-------------------|-------------------|
| Low | €147 | **€0.53** |
| Base | **€1,139** | **€1.09** |
| High | €7,366 | **€2.41** |

**Platform sales implication:** Hybrid usage fee **€0.10/checkout × 3,331 = €333** is **less than** incremental Mollie at base — restaurant still net-negative unless turn-time ROI clears gap.

---

## 4. Platform revenue scenarios

### 4.1 Scenario table (primary acceptance artifact)

| ID | Venue type | Pricing model | Guest checkouts/mo | Platform revenue/mo | Platform COGS/mo | **Gross profit/mo** | **Gross margin** | Take rate on GMV_R |
|----|------------|---------------|--------------------|-----------------------|------------------|---------------------|------------------|-------------------|
| **P1** | Pilot | €0 SaaS | 3,331 | **€0** | €43 | **−€43** | n/m | 0% |
| **S1** | Base bistro | Starter €59 | 3,331 | **€59** | €43 | **€16** | **27%** | 0.07% |
| **H1** | Base bistro | Hybrid €49+usage | 3,331 | €49+(3181×€0.10)=**€367** | €55 | **€312** | **85%** | 0.41% |
| **H2** | Slow cafe | Hybrid | 552 | €49+(402×€0.10)=**€89** | €48 | **€41** | **46%** | 0.52% |
| **H3** | Busy city | Hybrid | 13,770 | €49+(13,620×€0.10)=**€1,411** | €78 | **€1,333** | **94%** | 0.37% |
| **E1** | 3-loc group | Enterprise €99×3 | 10,000 (agg) | **€297** + bps optional | €180 | **€117+** | 40%+ | ~0.10% SaaS only |

*Hybrid COGS +€12 vs Starter for metering pipeline at scale.*

### 4.2 Take rate definition

```
take_rate = platform_revenue / GMV_R
```

| Scenario | GMV_R | Platform rev | Take rate |
|----------|-------|--------------|-----------|
| S1 Base | €89,942 | €59 | **0.066%** |
| H1 Base | €89,942 | €367 | **0.408%** |
| H3 High | €379,440 | €1,411 | **0.372%** |

**Benchmark:** 0.4% platform take is **below** card interchange but must be justified vs **incremental €1,139/mo Mollie** restaurant pays — combined "payment stack cost" ≈ **1.7% of GMV_R** in base case.

---

## 5. Restaurant-side unit economics (base scenario H1)

### 5.1 P&L impact summary (monthly, directional)

| Line | Without Rekentafel | With Rekentafel (H1) | Δ |
|------|-------------------|----------------------|---|
| GMV (split sessions) | €89,942 | €89,942 | €0 |
| Mollie guest fees | €333 | €1,472 | **+€1,139** |
| Rekentafel platform | €0 | €367 | **+€367** |
| **Total payment stack cost** | **€333** | **€1,839** | **+€1,506** |
| Pay-phase minutes (1,041 sessions × 6 min) | — | 6,246 min saved | **104 hr** |
| Implied value @ €15/table-hr | — | — | **+€1,560** |
| **Net operational estimate** | — | — | **≈ +€54/mo** |

**Interpretation:** Base case is **marginally positive** for restaurant only if **6 min saved** claim holds. Pilot must instrument `payment_mode_opened_at` → `table_closed_at`. If savings = 3 min, restaurant **−€726/mo** — churn risk.

### 5.2 Sensitivity — minutes saved vs incremental cost

Incremental cost vs terminal ≈ **€1,506/mo** (base). Break-even minutes:

```
break_even_min = Δcost / (S' × €15/60) = 1506 / (1041 × 0.25) ≈ 5.8 min
```

| Minutes saved | Restaurant net vs status quo |
|---------------|------------------------------|
| 3 | **−€726/mo** |
| 6 | **+€54/mo** |
| 10 | **+€894/mo** |
| 15 | **+€1,844/mo** |

---

## 6. Platform portfolio economics (multi-venue)

### 6.1 Cohort model — first 12 months (illustrative)

| Month | Paying venues | Mix | MRR platform | COGS | **Gross profit** |
|-------|---------------|-----|--------------|------|------------------|
| 1–3 | 1 pilot | P1 | €0 | €43 | −€43 |
| 4–6 | 3 | 2×S1, 1×P1 | €118 | €129 | −€11 |
| 7–9 | 8 | 5×S1, 3×H1 early | €1,396 | €424 | €972 |
| 10–12 | 15 | 5×S1, 10×H1 | €4,265 | €825 | **€3,440** |

Assumptions: 2 pilots convert Starter month 4; hybrid available month 7; avg H1 revenue €367 by month 10.

### 6.2 CAC / LTV (directional — no invented ad spend)

| Metric | Starter | Hybrid H1 |
|--------|---------|-----------|
| Sales motion | Founder-led | Founder + 1 AE |
| Onboarding cost | €150 | €200 |
| Monthly gross profit | €16 → risky | €312 |
| Months to payback onboarding | **10+** | **<1** |
| 24-mo LTV (gross, no churn) | €384 rev / €272 GP | €8,808 rev / ~€7,000 GP |
| **Churn risk** | High if ROI unproven | Med |

**Strategic implication:** **Do not scale sales** until H1 gross profit/venue ≥€250 or Starter attach proves 6+ min savings.

---

## 7. Mollie fee stress tests

### 7.1 Wero pricing change (+20% on iDEAL flat)

| Metric | Base | Wero +20% (€0.384) |
|--------|------|---------------------|
| m blended | €0.442 | €0.478 |
| Mollie_R | €1,472 | €1,592 |
| Δ vs base | — | **+€120/mo restaurant** |

Platform margin **unchanged** (Model A). Renegotiate hybrid **€0.10 → €0.11** only if restaurant churn signals — do not auto-pass-through.

### 7.2 Card mix spike (tourist season, 50% cards)

| Metric | 25% cards | 50% cards |
|--------|-----------|-----------|
| m | €0.442 | €0.520 |
| Mollie_R | €1,472 | €1,733 |
| Δ | — | **+€261/mo** |

Mitigation: iDEAL-first checkout UX ([mollie-capabilities.md](../architecture/payments/mollie-capabilities.md) §2.3).

### 7.3 Chargeback cost (restaurant MoR)

Not modeled as platform COGS. Budget **€15–25/chargeback** Mollie fee to restaurant + admin time. At 0.2% card GMV dispute rate on €22k card volume → ~€44/mo restaurant — immaterial vs turn-time story at MVP.

---

## 8. Fraud and ops cost allowances

| Event | Frequency assumption | Platform cost |
|-------|---------------------|---------------|
| Bill hijack false claim | 0.1% sessions | €0.50/support min |
| Webhook replay investigation | 2/mo/venue | €5 |
| Refund assist | 1% checkouts | €2 avg |
| **Ops reserve / venue / mo** | — | **€15** |

Add to COGS for **net margin** view: H1 net GP ≈ €312 − €15 = **€297/mo** (base).

---

## 9. Weak assumptions challenged

| Assumption | Challenge | Mitigation |
|------------|-----------|------------|
| 65% attach rate day 1 | Unrealistic — staff habituation | Pilot KPI 70% by week 8, not week 1 |
| 6 min saved | Unmeasured | Instrument timestamps; withhold hybrid upsell until proven |
| €59 covers support forever | LTV-negative at 27% GM | Move to hybrid; raise Starter to €79 if needed |
| Platform bps is "free money" | Restaurant pays ΔMollie | ROI one-pager mandatory in sales |
| High G (3.2 payers) always | Couples date → G=2 | Model H2 slow cafe separately |

---

## 10. Crypto note (post-MVP economics placeholder)

| Item | Status |
|------|--------|
| Mollie crypto | **Not available** |
| Platform take | Separate quote: flat €0.25–0.50/crypto checkout + spread |
| Restaurant Mollie fee | N/A on crypto rail |
| Modeling | **Do not include in MVP unit economics** |

---

## 11. Key metrics dashboard (instrument before pilot)

| Metric | Formula | Target (base) |
|--------|---------|---------------|
| `attach_rate` | split_sessions / all_sessions | ≥65% |
| `guest_checkouts_per_session` | C / S' | 3.0–3.5 |
| `pay_phase_minutes_p50` | close − payment_mode | ≤8 |
| `platform_take_rate` | rev / GMV_R | 0.07% MVP → 0.4% hybrid |
| `restaurant_stack_cost_rate` | (Mollie_R + platform) / GMV_R | <2.0% |
| `gross_profit_per_venue` | rev − COGS | ≥€250 before scale |

---

## 12. Related documents

- [pricing-options.md](./pricing-options.md) — model comparison + Mollie §6
- [pricing-recommendation.md](./pricing-recommendation.md) — selected price card
- [restaurant-value-onepager.md](./restaurant-value-onepager.md) — owner-facing ROI
