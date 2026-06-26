# Pilot Scorecard — Success Metrics and Targets

**Product (working name):** Rekentafel  
**Slice:** Part 14 — Go-To-Market Plan and Pilot Scorecard  
**Pilot window:** 8 weeks live service (excluding 2-week onboarding)  
**Last updated:** 2026-06-26  
**Cross-references:** [gtm-plan.md](./gtm-plan.md), [manual-ops-playbook.md](../integrations/manual-ops-playbook.md), [mvp-roadmap.md](../product/mvp-roadmap.md)

---

## 1. Purpose

This scorecard defines **what "pilot success" means** in numbers. It is the contract between platform ops, the pilot venue, and product/engineering for go/no-go on V1.1 expansion.

**Rules:**

1. Metrics are measured **per service** (lunch/dinner) and rolled up weekly.
2. Denominators exclude tables with bill **≤€30** unless noted (low split incentive).
3. Baseline is captured in **Week 0 shadow shift** (pre-product) for time-to-pay comparison.
4. All thresholds are **MVP**; post-MVP targets are listed separately.

---

## 2. Scorecard at a glance

| # | Metric | Definition | MVP target | Red flag | Data source |
|---|--------|------------|------------|----------|-------------|
| M1 | **Payment activation rate** | % eligible tables with payment mode opened | ≥40% Wk4; ≥50% Wk8 | <30% Wk6 | `table_sessions` |
| M2 | **Split completion rate** | Sessions reaching €0 remaining without force-close | ≥85% | <70% | `payment_sessions` |
| M3 | **Median time-to-pay (TTP)** | Payment open → table close | ≤12 min | >18 min | Event timestamps |
| M4 | **Waiter override rate** | Sessions with ≥1 claim override | ≤8% | >15% | `claim_overrides` |
| M5 | **Guest NPS (session)** | Post-payment micro-survey | ≥+40 | <+20 | In-app 0–10 |
| M6 | **Venue retention intent** | Manager "would renew" (Week 8) | ≥8/10 | <6/10 | Survey |
| M7 | **Bill entry latency** | Bill ready → payment open | ≤3 min median | >5 min | Staff events |
| M8 | **Payment retry success** | Failed checkout → paid within 15 min | ≥90% | <75% | Mollie webhooks |
| M9 | **Hijack / foreign join rate** | Joins flagged distant IP + no override | ≤2% sessions | >5% | Fraud log |
| M10 | **Manual bill error rate** | Bills corrected before payment open | ≤5% | >12% | `bill_validations` |

**Pilot pass rule:** **≥4 of M1–M6** meet MVP target at Week 8 **and** no red flag on M2, M4, or M9.

---

## 3. Metric definitions (detailed)

### M1 — Payment activation rate

**Formula:**

```
activation_rate = tables_payment_active / tables_eligible

tables_eligible = tables with:
  - session state SEATED or PAYMENT_ACTIVE at bill time
  - final bill total > €30
  - party size ≥2 OR bill lines ≥3
  - not marked "single payer" by waiter
```

**Example (Friday dinner, Week 4):**

| Count | Value |
|-------|-------|
| Total tables served | 42 |
| Eligible (>€30, 2+ guests) | 28 |
| Payment mode opened | 13 |
| **Activation rate** | **46.4%** ✓ (target ≥40%) |

**Segmentation (report weekly):**

| Segment | Hypothesis |
|---------|------------|
| Party 2 | Lower activation; equal split sufficient |
| Party 3–4 | Core wedge |
| Party 5+ | Highest activation; monitor override rate |
| Lunch vs dinner | Dinner should exceed lunch by ≥10 pp |

**Weak assumption challenged:** *100% activation is success.* Forcing activation on 2-tops creates staff resentment. Target 50% on eligible tables, not 100% of all tables.

---

### M2 — Split completion rate

**Formula:**

```
completion_rate = sessions_closed_zero_balance / sessions_payment_opened

Exclude: manager force-close with written reason "single terminal payment"
```

**Session outcome state machine:**

```
PAYMENT_OPENED
      │
      ├──► IN_PROGRESS (claims/payments partial)
      │         │
      │         ├──► COMPLETED (remaining = 0, normal close)
      │         ├──► FORCE_CLOSED (cash/terminal remainder)
      │         └──► ABANDONED (token expired, remaining > 0)
      │
      └──► CANCELLED (payment mode cancelled before any pay)
```

**Success = COMPLETED / (PAYMENT_OPENED − CANCELLED within 60s)**

**Example (Week 3):**

| Outcome | Count |
|---------|-------|
| Payment opened | 52 |
| Cancelled <60s (waiter mistake) | 3 |
| Completed €0 | 44 |
| Force closed (single card) | 4 |
| Abandoned (remaining > €0) | 1 |
| **Completion rate** | 44 / 49 = **89.8%** ✓ |

**Red flag diagnosis:**

| Pattern | Likely cause |
|---------|--------------|
| High ABANDONED | Session TTL too short; guest confusion |
| High FORCE_CLOSED | Waiters revert to terminal under pressure |
| High CANCELLED | Training issue; wrong table |

---

### M3 — Median time-to-pay (TTP)

**Definition:** Elapsed time from `payment_mode_activated_at` to `table_closed_at` for COMPLETED sessions.

**Baseline (pre-Rekentafel):** Shadow 5 eligible tables in discovery week.

| Baseline method | Measure |
|-----------------|---------|
| Stopwatch shadow | Bill delivered → last guest leaves / terminal done |
| Owner estimate | "How long on a bad 4-top?" |

**Example baseline vs pilot:**

| Cohort | n | Median TTP | p90 TTP |
|--------|---|------------|---------|
| Baseline (terminal + Tikkie) | 5 | **16.2 min** | 24 min |
| Pilot Wk8 Rekentafel | 38 | **9.4 min** | 14 min |
| **Delta** | | **−6.8 min** | |

**ROI translation (for owner review):**

```
Minutes saved per table × eligible activations/week × 2 peak nights
= 6.8 × 13 × 2 ≈ 177 min/week ≈ 3.0 staff-hours/week
At €18/h loaded ≈ €54/week labor equivalent
```

**MVP target:** Median ≤12 min (≥25% improvement vs baseline if baseline ≥16 min).

---

### M4 — Waiter override rate

**Formula:**

```
override_rate = sessions_with_override / sessions_payment_opened

Override = claim reassignment, force equal split, lock guest, manager edit
```

**Example:**

| Week | Sessions | Overrides | Rate |
|------|----------|-----------|------|
| 2 | 18 | 3 | 16.7% ✗ (training) |
| 6 | 41 | 2 | 4.9% ✓ |

**Override reason codes (staff app):**

| Code | Expected share |
|------|----------------|
| `GUEST_DISPUTE` | 40% |
| `WRONG_CLAIM` | 30% |
| `SHARED_ITEM_CONFUSION` | 20% |
| `FRAUD_SUSPECT` | <5% |
| `OTHER` | remainder |

**Post-MVP target (V1.1):** ≤5% with POS import reducing bill entry errors.

---

### M5 — Guest NPS (session-level)

**Collection:** One question after successful Mollie payment (optional dismiss).

> *"How easy was paying your share tonight?"* 0–10

**Formula:** Standard NPS = % promoters (9–10) − % detractors (0–6).

**Sample size rule:** Minimum 30 responses before reporting; expect 60–120 over 8 weeks at 50% activation.

**Example:**

| Score bucket | Count | % |
|--------------|-------|---|
| 9–10 | 42 | 48% |
| 7–8 | 28 | 32% |
| 0–6 | 17 | 20% |
| **NPS** | | **+28** (approaching target +40) |

**Qualitative tags (multi-select):**

- Easy iDEAL
- Confusing shared items
- Slow to load
- Waiter helped
- Would use again

---

### M6 — Venue retention intent

**Week 8 manager survey (private):**

| Question | Scale |
|----------|-------|
| Would you continue using Rekentafel after pilot? | 1–10 |
| Would you recommend to another owner? | 1–10 |
| Fair monthly price if split-pay keeps working? | € open |

**Target:** Question 1 ≥8/10 average across manager + owner.

**Repeat venue retention (post-pilot):**

| Milestone | Target |
|-----------|--------|
| Month 3 post-pilot still active | 100% (1 venue) |
| Month 6 without 14-day usage gap | 100% |
| V1.1 cohort (3 venues) Month 6 | ≥2 of 3 |

---

### M7 — Bill entry latency

**Formula:** `payment_mode_activated_at − bill_finalized_at`

**Target:** Median ≤3 min (playbook §4.5 says ≤30 sec from bill ready — this metric includes re-key time from POS receipt).

**Feasibility link:** High latency predicts low activation (waiters skip when busy).

| Lines on bill | Expected entry time |
|---------------|----------------------|
| 1–4 | ≤90 sec |
| 5–8 | ≤3 min |
| 9–14 | ≤5 min |
| 15+ | Consider CSV import (manager) |

---

### M8 — Payment retry success

**Formula:**

```
retry_success = failed_checkouts_retried_and_paid / failed_checkouts_total
Window: 15 minutes from first failure
```

**Mollie failure buckets:**

| Type | Retry expectation |
|------|-------------------|
| User cancelled iDEAL | Low retry — guest choice |
| Insufficient funds | Medium |
| Network timeout | High retry |

**Report excluding** user-cancelled if >50% of failures (otherwise investigate UX bug).

---

### M9 — Hijack / foreign join rate

**Formula:**

```
hijack_rate = sessions_with_foreign_join_flag / total_sessions

Foreign join flag = join IP geo ≠ NL AND >50km from venue AND no waiter override within 5 min
```

**MVP target ≤2%:** Aligns with [threat-register.md](../security/threat-register.md) pilot assumption.

**If red:** Enable table PIN mandatory (already supported); consider V1.1 geo gate.

---

### M10 — Manual bill error rate

**Formula:**

```
error_rate = bills_with_pre_open_correction / bills_finalized
Correction = line delete, VAT change, qty change after Validate
```

**Ties to manual ops:** High errors → owner distrust; drives V1.1 CSV import priority.

---

## 4. Weekly reporting template

### Week N summary (ops dashboard)

| Metric | Wk N | Wk N-1 | Target | Status |
|--------|------|--------|--------|--------|
| M1 Activation | | | ≥40% | 🟢/🟡/🔴 |
| M2 Completion | | | ≥85% | |
| M3 Median TTP | | | ≤12m | |
| M4 Override | | | ≤8% | |
| M5 Guest NPS | | | ≥+40 | |
| M7 Bill latency | | | ≤3m | |
| M8 Retry | | | ≥90% | |
| Sessions (n) | | | ≥30 by Wk4 | |

**Narrative (3 bullets max):**

1. What improved
2. Top override/failure reason
3. Action for next week

---

## 5. Baseline capture protocol (Week 0)

| Step | Detail |
|------|--------|
| 1 | Founder shadows 2 dinner services |
| 2 | Record 5 eligible tables: bill delivery → settlement complete |
| 3 | Note payment method (terminal/Tikkie/mixed) |
| 4 | Interview 3 waiters: "Hardest part of closing a big table?" |
| 5 | Store in `pilot_baselines` (ops); do not show guests |

---

## 6. MVP vs post-MVP targets

| Metric | MVP (8 wk, 1 venue) | V1.1 (3–10 venues) | V2 |
|--------|---------------------|---------------------|-----|
| M1 Activation | ≥50% Wk8 | ≥55% avg | ≥60% |
| M2 Completion | ≥85% | ≥88% | ≥90% |
| M3 Median TTP | ≤12 min | ≤10 min | ≤8 min |
| M4 Override | ≤8% | ≤5% | ≤4% |
| M5 Guest NPS | ≥+40 | ≥+45 | ≥+50 |
| M6 Retention | ≥8/10 | ≥2/3 venues renew | ≥80% logo retention |
| M10 Bill error | ≤5% | ≤2% (CSV import) | ≤1% (POS sync) |
| Accounts created | ≤15% guests (informational) | ≤25% | Track for loyalty |

---

## 7. Leading vs lagging indicators

```
LEADING (weekly)                    LAGGING (pilot outcome)
─────────────────                   ───────────────────────
M7 Bill entry latency               M3 Time-to-pay
M1 Activation rate                  M2 Completion rate
Override reason mix                 M5 Guest NPS
Staff training completion           M6 Retention intent
Support tickets / service           Reference agreement signed
```

**Week 4 go/no-go (continue pilot):**

| Signal | Continue | Escalate | Pause |
|--------|----------|----------|-------|
| M1 | ≥35% | 25–34% | <25% |
| M2 | ≥80% | 70–79% | <70% |
| Overrides | ≤12% | 12–15% | >15% |
| Staff sentiment | ≥3.5/5 | 3.0–3.4 | <3.0 |

---

## 8. Example full scorecard (illustrative Week 8)

**Venue:** De Gouden Lepel (fictional pilot)  
**Period:** 8 weeks, 86 eligible tables, 48 payment sessions

| Metric | Result | Target | Pass? |
|--------|--------|--------|-------|
| M1 Activation | 52.3% (45/86) | ≥50% | ✓ |
| M2 Completion | 91.1% (41/45) | ≥85% | ✓ |
| M3 Median TTP | 10.1 min | ≤12 min | ✓ |
| M4 Override | 6.7% (3/45) | ≤8% | ✓ |
| M5 Guest NPS | +38 (n=52) | ≥+40 | ~ (close) |
| M6 Retention | 9/10 | ≥8/10 | ✓ |
| M7 Bill latency | 2.4 min | ≤3 min | ✓ |
| M8 Retry success | 92% | ≥90% | ✓ |
| M9 Hijack | 0% | ≤2% | ✓ |
| M10 Bill error | 4.2% | ≤5% | ✓ |

**Verdict:** **PASS** (5/6 core + M5 near-miss) → proceed to reference GTM per [pmf-signals.md](./pmf-signals.md).

---

## 9. Risks to metric integrity

| Risk | Distortion | Control |
|------|------------|---------|
| Waiters open payment on €15 bills to game activation | Inflates M1 | Eligible table definition |
| Force-close labeled "single terminal" hides failures | Inflates M2 | Audit force-close reasons |
| Founder presence speeds TTP | Optimistic M3 | Blinded weeks 5–8 remote |
| NPS only happy guests respond | Inflates M5 | Show dismiss rate; minimum n |
| Shadow baseline too small (n=5) | Noisy M3 delta | Confidence interval in report |

---

## Related artifacts

- [gtm-plan.md](./gtm-plan.md) — acquisition and onboarding
- [objection-playbook.md](./objection-playbook.md) — when metrics stall
- [pmf-signals.md](./pmf-signals.md) — PMF gates beyond scorecard
