# PART 14 — Go-To-Market Plan

**Product (working name):** Rekentafel | Codename: TabSettle  
**Slice:** Part 14 — Go-To-Market Plan and Pilot Scorecard  
**Market:** Netherlands-first hospitality fintech  
**Last updated:** 2026-06-26  
**Status:** Execution-ready for single-venue pilot  
**Cross-references:** [positioning.md](../product/positioning.md), [manual-ops-playbook.md](../integrations/manual-ops-playbook.md), [integration-tiers.md](../integrations/integration-tiers.md), [mvp-roadmap.md](../product/mvp-roadmap.md)

---

## 1. Executive summary

Rekentafel enters the Netherlands with a **single-venue design partner pilot** before any paid outbound sales. The beachhead is **independent table-service restaurants** where group dining and iDEAL are the norm, POS replacement is unacceptable, and full QR ordering is culturally rejected. MVP GTM proves **collaborative split-pay at the table** — not loyalty, discovery, or crypto.

**GTM thesis:** Win one venue with measurable turn-time and payment-completion gains; convert that venue into a reference customer; expand to 3–10 venues in the same metro cluster via warm intro and Horeca peer networks.

**Pilot economics (MVP):** Free software + founder-led onboarding. Success measured by scorecard in [pilot-scorecard.md](./pilot-scorecard.md), not revenue.

---

## 2. Beachhead segment (Netherlands)

### 2.1 ICP definition

| Dimension | Beachhead (MVP pilot) | Post-MVP expansion (V1.1+) |
|-----------|----------------------|----------------------------|
| **Geography** | Randstad: Amsterdam (non-Centrum), Utrecht, Haarlem, Den Haag | NL nationwide; BE/DE border cities V2 |
| **Venue type** | Independent **casual dining** / modern bistro / wine bar | Same + small groups (2–4 sites) |
| **Service model** | Full table service; waiters take orders | Same |
| **Covers** | 40–80 seats; 1.0–1.4 turns on Fri/Sat | 25–120 seats |
| **Avg check (4-top)** | €90–€220 incl. VAT + service | €60+ for payment-mode eligibility |
| **Tech stack** | Existing POS (UnTill, Lightspeed, cash+terminal mix); **no** pay-at-table SaaS | POS read-only import (V1.1) |
| **Payment today** | One card + Tikkie; occasional terminal at bar | Same |
| **Decision maker** | Owner-operator or GM with floor authority | Multi-site ops manager (V2) |
| **Language** | NL staff; NL/EN guest UI | + DE for tourist corridors |

### 2.2 Ideal first pilot restaurant profile

**Archetype name:** *"The Friday Four-Top Bistro"*

| Attribute | Target value | Why it matters |
|-----------|--------------|----------------|
| Name pattern | e.g. neighborhood bistro, natural wine bar, shared-plates concept | High shared-item split frequency |
| Location | Residential neighborhood, 15–25 min from Amsterdam/Utrecht core | Staff stability; repeat locals; less tourist QR confusion |
| Tables | 18–28 tables; 60% are 4-tops or combinable 2+2 | Split-pay pain concentrated |
| Weekly covers | 350–550 | Enough sessions for stats in 8 weeks |
| Fri/Sat peak | 2 seatings; 45–90 min table occupancy | Turn-time ROI visible |
| Group mix | ≥35% parties of 3+ | Above threshold for Rekentafel vs single-card |
| Alcohol mix | 25–40% of revenue (wine bottles) | Shared-item UX stress test |
| POS | UnTill or Lightspeed export-capable | V1.1 CSV path without custom API |
| Mollie | Willing to connect merchant account (or open one) | Payment rail non-negotiable |
| Owner mindset | "We are not becoming a QR order restaurant" | Positioning fit |
| Staff turnover | <40% annual | Training investment survives pilot |

**Concrete example (illustrative, not a signed customer):**

> *De Gouden Lepel*, 52 seats, Utrecht Oudwijk. €28 lunch / €42 dinner avg. 22 tables. Friday: 38 tables served, 11 tables with bill >€120 and 4+ guests. Owner cites "Tikkie chaos" as top guest complaint in Google reviews.

### 2.3 Pilot type selection rationale (manual ops feasibility)

Tier 0 integration ([integration-tiers.md](../integrations/integration-tiers.md)) requires waiters to **enter bills manually** or managers to **CSV import** before opening payment. This is feasible only when:

| Feasibility factor | Required for pilot | Rationale |
|--------------------|-------------------|-----------|
| Menu size | ≤80 active items; ≤15 daily specials | Manual entry cognitive load |
| Bill complexity | Mostly à la carte; limited tasting menus | Tasting menus = single payer edge case |
| Modifier chaos | Low (no 20-option build-your-own) | Each modifier is a line-entry tax |
| Ticket time | Waiter can re-key 6–12 lines in ≤3 min | Matches playbook §4.4 |
| Manager bandwidth | 2 h/week for menu admin + incident review | Pilot ops budget |
| POS receipt | Printed or bar-screen itemized | Reconciliation source of truth |
| Peak discipline | Shift lead can spot-check 3 bills/night | Catches VAT errors before payment open |

**Rejected pilot profiles (MVP):**

| Profile | Why reject |
|---------|------------|
| Fine dining tasting menu (€85+ pp, 7 courses) | One payer norm; low split demand |
| Fast-casual counter service | No table QR ritual; wrong service model |
| Centrum tourist trap (60%+ walk-in, 2 languages minimum) | Support load; hijack anxiety; staff churn |
| All-you-can-eat / rijsttafel fixed price | Equal split only; weak item-claim value |
| 120+ seats multi-room banquet | Manual entry breaks at scale |
| Venue without smartphone-comfortable staff | Training failure risk |

**Weak assumption challenged:** *"Any restaurant with QR codes will work."* Manual ops cap means the first pilot must be **operationally simple** even if marketing wants a famous name.

---

## 3. Problem-solution fit (GTM narrative)

### 3.1 Core message by stakeholder

| Stakeholder | Pain (quantified) | Rekentafel promise | Proof artifact |
|-------------|-------------------|-------------------|----------------|
| **Owner** | Last 10–20 min of occupancy = €0 revenue; 12 large tables × 8 min = 96 min/night wasted | Parallel guest payments; faster turns | Median time-to-close ≤12 min |
| **Waiter** | Mediates split math; runs terminal 3× per table | One tap → guests self-serve pay | Activation ≤30 sec; override ≤8% |
| **Guest** | 5–15 min Tikkie chase; wrong splits on shared wine | Claim items; iDEAL on own phone | ≥85% session completion |

### 3.2 Category wedge

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESTAURANT QR LANDSCAPE                       │
├──────────────────────┬──────────────────────┬───────────────────┤
│ Full QR ordering     │ Pay-at-table terminal│ Rekentafel        │
│ (Orderli, etc.)      │ (Zettle, POS module) │ (MVP wedge)       │
├──────────────────────┼──────────────────────┼───────────────────┤
│ Changes service model│ Single payer UX      │ Multi-payer split │
│ High onboarding      │ Hardware cost        │ Web + Mollie      │
│ Guest orders food    │ Waiter runs card     │ Waiter opens bill │
└──────────────────────┴──────────────────────┴───────────────────┘
```

**Sales line:** *"We're the split-pay layer for restaurants that still want waiters — not another order-from-your-phone app."*

---

## 4. Pilot acquisition motion

### 4.1 Funnel state machine

```
                    ┌──────────────┐
                    │   IDENTIFY   │  ICP score ≥70/100
                    └──────┬───────┘
                           │ warm intro or inbound
                           ▼
                    ┌──────────────┐
         no ◄───────│  QUALIFY     │───────► archive (wrong ICP)
                    │  (30 min)    │
                    └──────┬───────┘
                           │ yes
                           ▼
                    ┌──────────────┐
                    │  DISCOVERY   │  shadow Fri/Sat service
                    │  (2 h onsite)│
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐ ┌──────────┐ ┌──────────┐
         │ DECLINE │ │  PILOT   │ │  WAITLIST│
         │         │ │  SIGN    │ │  (V1.1)  │
         └─────────┘ └────┬─────┘ └──────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │  ONBOARD     │  Week -2 to 0
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │  LIVE PILOT  │  8 weeks
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐ ┌──────────┐ ┌──────────┐
         │ CHURN   │ │ REFERENCE│ │ EXPAND   │
         │         │ │ CUSTOMER │ │ (venue 2)│
         └─────────┘ └──────────┘ └──────────┘
```

### 4.2 ICP scoring rubric (0–100)

| Criterion | Weight | 0 | 5 | 10 |
|-----------|--------|---|---|-----|
| Group dining frequency (3+ tops) | 15 | <20% | 20–34% | ≥35% |
| Owner rejects phone ordering | 15 | Open to QR order | Neutral | Explicit anti-QR-order |
| Avg dinner check 4-top | 10 | <€80 | €80–119 | ≥€120 |
| Mollie-ready or willing | 15 | Refuses | Willing if easy | Already on Mollie |
| Manager ops bandwidth | 10 | None | 1 h/week | 2+ h/week |
| Menu/bill complexity | 15 | Tasting menu / 100+ SKUs | Moderate | Simple à la carte |
| Randstad location | 10 | Outside NL | Secondary city | Amsterdam/Utrecht belt |
| Reference potential | 10 | Anonymous | Local only | Horeca network hub |

**Pilot gate:** Score ≥70 **and** no automatic disqualifier (phone-ordering mandate, no smartphone staff, no itemized POS).

### 4.3 Acquisition channels (MVP only)

| Channel | Motion | Expected yield (8 weeks) | Cost |
|---------|--------|--------------------------|------|
| **Founder network** | Direct outreach to 15 owner-operators | 3 discovery calls | €0 |
| **Horeca supplier intro** | Ask POS reseller / accountant / wine rep for 1 intro | 1 qualified lead | €0 + reciprocity |
| **Mollie partner desk** | Apply for hospitality showcase / co-marketing (no rev share MVP) | 0–1 inbound | Time |
| **LinkedIn NL Horeca** | Case-study teaser post after pilot week 4 | Waitlist signups | €0 |
| **Inbound website** | Single landing + waitlist form | 5–20 emails | €200/mo ads optional |

**Explicitly NOT in MVP GTM:** paid performance ads at scale, enterprise POS partnerships, franchise sales, discovery marketplace SEO, crypto community outreach.

### 4.4 Discovery call script (30 minutes)

| Minute | Topic | Exit criterion |
|--------|-------|----------------|
| 0–5 | Current payment flow; last bad split story | Quantified pain (time, €) |
| 5–12 | Demo video or live sandbox table | Owner sees waiter-gated bill |
| 12–18 | Manual ops honesty: waiter enters bill 2–3 min | Owner accepts Tier 0 |
| 18–24 | Mollie, GDPR, no stored wallet | Legal objections surfaced |
| 24–28 | 8-week pilot terms (free, success metrics) | Verbal yes/no |
| 28–30 | Schedule shadow shift | Calendar hold |

### 4.5 Pilot commercial terms (MVP)

| Term | Value |
|------|-------|
| Duration | 8 weeks live + 2 weeks onboarding |
| Price | €0 platform fee |
| Transaction fee | €0 (restaurant pays Mollie only) |
| Commitment | Manager 2 h/week; floor training 45 min/server |
| Data | Anonymized metrics for case study with approval |
| Exit | Either party 7 days notice |
| Success definition | [pilot-scorecard.md](./pilot-scorecard.md) thresholds |
| Post-pilot pricing | Letter of intent to discuss €79–€129/mo or 0.5% GMV (TBD) — not contracted at signup |

---

## 5. Onboarding timeline (Week -2 → Week 8)

### 5.1 Pre-live (Week -2 to 0)

| Day | Activity | Owner | Artifact |
|-----|----------|-------|----------|
| D-14 | Sign pilot MSA + DPA ([compliance/policy-drafts-needed.md](../compliance/policy-drafts-needed.md)) | Owner + founder | Executed PDF |
| D-12 | Mollie Connect merchant API key (restaurant-owned) | Owner | Green in admin |
| D-10 | Venue setup: tables, menu, VAT rates | Manager + founder | 18–28 QRs exported |
| D-7 | QR print/install ([qr-lifecycle.md](../integrations/qr-lifecycle.md)) | Manager | Sticker audit log |
| D-5 | Staff training session 1 (45 min) | Founder onsite | Training sign-off |
| D-3 | Shadow service (observe payment pain) | Founder | Baseline time study (5 tables) |
| D-1 | Dry run: fake bill €105.60, 4 test phones | Shift lead | Checklist pass |
| D0 | Go-live soft launch (weeknight) | All | Incident channel live |

### 5.2 Live pilot (Week 1–8)

| Week | Focus | Founder activity |
|------|-------|------------------|
| 1 | Activation habit | Floor presence opening 2 services |
| 2 | Bill entry accuracy | Review 10 bills for VAT errors |
| 3 | Guest education | Table tent copy A/B |
| 4 | Mid-pilot readout | Scorecard draft vs targets |
| 5–6 | Steady state | Remote; on-call |
| 7 | Staff feedback survey | NPS + override root causes |
| 8 | Final scorecard + renewal conversation | Reference agreement |

---

## 6. Guest and staff activation tactics

### 6.1 Table collateral (MVP)

| Asset | Placement | Copy (NL) |
|-------|-----------|-----------|
| QR sticker | Table corner | *Scan voor menu · betalen kan als de bediening de rekening opent* |
| Tent card (payment) | Appears when bill delivered | *Samen betalen? Scan en claim je eigen deel — geen app nodig* |
| Waiter verbal script | Payment open | *"Scan de code op mijn scherm; je kunt je eigen deel betalen met iDEAL."* |
| PIN card (backup) | Waiter tablet | 6-digit join PIN for low-light scans |

**Do not say:** "Scan to see your bill" (implies always-on bill — security violation).

### 6.2 Staff incentive alignment (pilot)

| Tactic | Detail | Risk |
|--------|--------|------|
| Shift lead bonus | €50 if week-4 activation ≥50% | Gaming: open payment on tiny bills |
| No per-transaction waiter tip change | Tips pass through as today | Tip pool politics |
| "Fast close" leaderboard | Tables closed <10 min (internal) | Rushing guests |

**Mitigation:** Scorecard excludes bills <€30 from activation denominator ([pilot-scorecard.md](./pilot-scorecard.md)).

---

## 7. Competitive displacement (GTM battlecards)

| Incumbent behavior | Rekentafel counter | When to walk away |
|--------------------|-------------------|-------------------|
| "We use Tikkie" | In-venue settlement vs async chase | Owner sees no turn-time pain |
| "We have Sunday / Orderli" | Confirm: ordering or pay-only? If ordering-only competitor locked in, pitch split-only module | They want full QR order replacement |
| "Terminal at bar works" | Parallel phone pay vs sequential terminal | Avg party size ≤2 |
| "Guests won't scan" | No app; iDEAL native | Demographic anti-smartphone |

Full matrix: [competitive-matrix.md](../product/competitive-matrix.md).

---

## 8. MVP vs post-MVP GTM

| Motion | MVP (1 venue) | V1.1 (3–10 venues) | V2 (25+) |
|--------|---------------|---------------------|----------|
| Sales | Founder-led design partner | Reference sell + waitlist | Inside sales + partner channel |
| Pricing | Free | Pilot pricing test €79/mo | SaaS + optional bps via Mollie Connect |
| Onboarding | White-glove 20 h | 8 h remote + template | Self-serve + certification |
| Marketing | None paid | 2 case studies | Horeca trade press |
| Product proof | Split-pay scorecard | POS import + retention | Loyalty opt-in |
| Geo | 1 city | Same metro cluster | NL-wide |
| Crypto / wallet pitch | **Forbidden** | **Forbidden** | Separate eval if legal clears |

---

## 9. Risks specific to GTM slice

### 9.1 Legal / regulatory

| Risk | GTM impact | Mitigation |
|------|------------|------------|
| Payment facilitator confusion | Owner thinks we hold funds | Contract + Mollie merchant-of-record clarity |
| GDPR guest data | Owner fear of fines | DPA template; 90-day retention story |
| Alcohol VAT mis-display in marketing | Overclaiming compliance | "Supports 9%/21% display" not "guarantees fiscal receipt" |

### 9.2 Fraud

| Risk | GTM impact | Mitigation |
|------|------------|------------|
| Bill hijack story spreads | Owner rejects QR | Demo waiter-gated session first |
| Fake pilot testimonials | Brand damage | Only signed reference quotes |

### 9.3 UX

| Risk | GTM impact | Mitigation |
|------|------------|------------|
| Guest confusion empty vs pay QR | Bad first scan reviews | Distinct UI states; staff script |
| iDEAL drop-off | Owner says "failed" | Retry UX; set 90% retry target |

### 9.4 Ops

| Risk | GTM impact | Mitigation |
|------|------------|------------|
| Manual entry fatigue | Waiters disable feature | ICP filter; V1.1 CSV promise |
| Founder bottleneck | Can't onboard venue 2 | Document playbook; hire part-time ops at 3 venues |
| Mollie KYC delay | Go-live slip | Start KYC at D-14; test mode dry run |

---

## 10. Rollout motion post-pilot (summary)

Detailed PMF gates: [pmf-signals.md](./pmf-signals.md).

| Phase | Trigger | Action |
|-------|---------|--------|
| **Reference launch** | ≥4 of 6 core metrics pass | Publish case study; ask 3 intros |
| **Cluster expand** | Venue 1 renews + NPS ≥40 | Sign venues 2–3 same city |
| **Pricing test** | 3 venues active 30 days | A/B €79 flat vs €49 + 0.5% GMV |
| **POS import GTM** | Manual error >5% tickets | Sell "reliability upgrade" Tier 1 |
| **Stop / pivot** | <50% activation week 6 | Pause outbound; fix product or ICP |

---

## 11. Open GTM decisions

| Question | MVP default | Revisit |
|----------|-------------|---------|
| Final brand name | Rekentafel consumer / TabSettle internal | Before public case study |
| Pilot pricing post-week-8 | Letter of intent only | After PMF signals |
| Mollie co-marketing | Apply, no dependency | Month 3 |
| Tourist EN-first venues | Defer | After NL-local proof |
| Franchise inbound | Politely waitlist | V2 |

---

## Related artifacts

- [pilot-scorecard.md](./pilot-scorecard.md) — measurable success metrics
- [objection-playbook.md](./objection-playbook.md) — owner, staff, guest responses
- [pmf-signals.md](./pmf-signals.md) — PMF indicators and rollout gates
