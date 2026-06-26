# PMF Signals and Post-Pilot Rollout Motion

**Product (working name):** Rekentafel  
**Slice:** Part 14 — Go-To-Market Plan and Pilot Scorecard  
**Last updated:** 2026-06-26  
**Cross-references:** [gtm-plan.md](./gtm-plan.md), [pilot-scorecard.md](./pilot-scorecard.md), [mvp-roadmap.md](../product/mvp-roadmap.md)

---

## 1. Purpose

This document defines **Product-Market Fit (PMF) signals** for Rekentafel after the single-venue MVP pilot — both quantitative thresholds and qualitative patterns — and the **rollout motion** triggered by each signal tier.

**PMF definition (this product):** Independent NL table-service restaurants **voluntarily activate** Rekentafel on most eligible group tables because it ** measurably shortens payment** without breaking waiter-led service — and owners **renew and refer** without founder bribery.

**Not PMF:** One famous logo, viral QR scans with low payment completion, or founder-subsidized free usage.

---

## 2. PMF signal framework

### 2.1 Signal tiers

```
┌─────────────────────────────────────────────────────────────┐
│                    PMF SIGNAL TIERS                          │
├──────────────┬──────────────────────────────────────────────┤
│ TIER 0       │ Pre-pilot — problem validated in shadow      │
│ TIER 1       │ Weak signal — fix or iterate (Week 4–6)      │
│ TIER 2       │ Emerging PMF — expand cautiously (Week 8)    │
│ TIER 3       │ Strong PMF — cluster rollout + pricing test  │
│ TIER 4       │ Category PMF — NL scale motion (6–12 mo)     │
└──────────────┴──────────────────────────────────────────────┘
```

### 2.2 Master signal table

| ID | Signal | Type | Tier 2 (Emerging) | Tier 3 (Strong) | Tier 4 (Category) |
|----|--------|------|-------------------|-----------------|-------------------|
| P1 | Payment activation (eligible tables) | Quant | ≥50% Wk8 | ≥55% sustained 4 wk | ≥60% multi-venue avg |
| P2 | Split completion rate | Quant | ≥85% | ≥88% | ≥90% |
| P3 | Median time-to-pay | Quant | ≤12 min | ≤10 min | ≤8 min |
| P4 | Guest session NPS | Quant | ≥+40 | ≥+45 | ≥+50 |
| P5 | Owner retention score | Quant | ≥8/10 | ≥9/10 + paid LOI | ≥80% logo retention @6mo |
| P6 | Unprompted owner referral | Qual | 1 intro offered | 2 signed intros | Inbound waitlist >20 |
| P7 | Waiter voluntary activation | Qual | Staff ask to use on busy tables | Shift leads train new hires | Owners cite staff buy-in in sales |
| P8 | "Very disappointed" survey | Quant | ≥25% (Sean Ellis) | ≥35% | ≥40% |
| P9 | Week-over-week session growth | Quant | +10% WoW Wk5–8 (same covers) | Sessions/track peak cover | Organic venue 2 request |
| P10 | Support tickets per 100 sessions | Quant | ≤8 | ≤5 | ≤3 |
| P11 | Manual bill error rate | Quant | ≤5% | ≤2% (CSV live) | ≤1% (POS sync) |
| P12 | Revenue willingness | Quant | LOI ≥€79/mo | 2 venues pay | Positive unit economics |

---

## 3. Quantitative PMF indicators (detailed)

### 3.1 Primary KPI bundle (must pass 4/6 for Tier 2)

| KPI | Source | Tier 2 threshold | Measurement window |
|-----|--------|------------------|-------------------|
| Activation | M1 | ≥50% | Last 2 pilot weeks |
| Completion | M2 | ≥85% | Full pilot |
| TTP | M3 | ≤12 min median | Last 4 weeks |
| Guest NPS | M5 | ≥+40 | n≥30 |
| Retention | M6 | ≥8/10 | Week 8 survey |
| Override | M4 | ≤8% | Full pilot |

**Tier 3:** All 6 pass **plus** P6 (referral) **plus** P8 ≥35%.

### 3.2 Sean Ellis "very disappointed" test

**Survey audience:** Restaurant owner + manager + ≥5 waitstaff (anonymous).

**Question:** *If Rekentafel disappeared tomorrow, how would you feel?*

- Very disappointed  
- Somewhat disappointed  
- Not disappointed  

**Scoring:**

| % Very disappointed | Interpretation |
|---------------------|----------------|
| <20% | No PMF — pivot ICP or product |
| 20–34% | Weak — iterate |
| 35–49% | Emerging PMF |
| ≥50% | Strong PMF (rare in pilot n) |

**MVP sample:** 8–12 respondents → treat as directional, not definitive.

### 3.3 Cohort retention (guest-side, informational)

Accounts are **optional in MVP** — guest retention is secondary.

| Metric | MVP (informational) | V1.1 target |
|--------|---------------------|-------------|
| Account creation post-payment | Track; ≤15% OK | ≥20% |
| Return guest joins 2nd session (same venue, 30d) | Track | ≥10% of account holders |
| Cross-venue guest | N/A | Deferred V2 |

**PMF is venue-side first**, guest network effects later.

### 3.4 Economic PMF (venue ROI)

| Input | Conservative pilot example |
|-------|---------------------------|
| Eligible tables/night (Fri+Sat) | 26 |
| Activation rate | 50% → 13 Rekentafel tables |
| Minutes saved/table | 6.8 |
| Staff-hour value | €18 loaded |
| **Weekly labor value** | 13 × 2 × 6.8 / 60 × €18 ≈ **€53/week** |
| Proposed SaaS | €99/mo ≈ €23/week |
| **Net** | Positive if activation holds |

**Tier 3 economic PMF:** Owner signs paid pilot extension **without** minutes-saved spreadsheet — "we just want to keep it."

---

## 4. Qualitative PMF indicators

### 4.1 Owner / manager language (positive)

| Quote pattern | PMF strength |
|---------------|--------------|
| "Friday tables turn faster" | Medium |
| "Guests stopped asking for the terminal three times" | Strong |
| "I'd pay for this" (unprompted) | Strong |
| "Can my friend at [venue] get it?" | Very strong |
| "Don't change ordering — this is enough" | Strong (positioning fit) |

### 4.2 Waiter language (positive)

| Quote pattern | PMF strength |
|---------------|--------------|
| "I use it on big tables now" | Strong |
| "Easier than explaining Tikkie" | Medium |
| "Don't take it away on busy nights" | Very strong |
| "Typing the bill is annoying" | Weak PMF — ops friction dominates |

### 4.3 Guest language (positive)

| Quote pattern | PMF strength |
|---------------|--------------|
| "Finally didn't send Tikkies" | Strong |
| "Shared wine split was clear" | Medium |
| "Didn't know I had to wait for waiter" | Onboarding gap — not PMF killer |
| "I'd use this at every restaurant" | Tier 3+ signal |

### 4.4 Negative qualitative patterns (anti-PMF)

| Pattern | Action |
|---------|--------|
| Owner disables after week 2 | Pause expansion; root-cause |
| Waiters revert to terminal on all 4-tops | Training or UX failure |
| Guests complain on Google Reviews about QR | Collateral + staff script fix |
| "Only works because founder was here" | Remote weeks failed — not PMF |
| Owner asks for phone ordering | Wrong product — decline |

---

## 5. PMF decision state machine

```
                    ┌─────────────┐
                    │ PILOT LIVE  │
                    └──────┬──────┘
                           │ Week 4 checkpoint
                           ▼
              ┌────────────────────────┐
              │ P1≥35% AND P2≥80% ?    │
              └────────────┬───────────┘
                     no    │    yes
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌─────────────┐           ┌─────────────┐
       │ ITERATE     │           │ CONTINUE    │
       │ (fix UX/ops)│           │ to Week 8   │
       └─────────────┘           └──────┬──────┘
                                        │ Week 8 scorecard
                                        ▼
                           ┌────────────────────────┐
                           │ ≥4/6 KPIs pass ?       │
                           └────────────┬───────────┘
                                  no    │    yes
                           ┌────────────┴────────────┐
                           ▼                         ▼
                    ┌─────────────┐           ┌─────────────┐
                    │ PIVOT /     │           │ TIER 2      │
                    │ PAUSE GTM   │           │ EMERGING    │
                    └─────────────┘           └──────┬──────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                             P8≥35% + P6      P8 25–34%         P8 <25%
                                    │                │                │
                                    ▼                ▼                ▼
                             ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                             │ TIER 3      │  │ EXTEND      │  │ PRODUCT     │
                             │ STRONG PMF  │  │ PILOT 4wk   │  │ WORKSTREAM  │
                             └──────┬──────┘  └─────────────┘  └─────────────┘
                                    │
                                    ▼
                             Cluster rollout
                             (venues 2–3)
```

---

## 6. Post-pilot rollout motion

### 6.1 Phase A — Reference customer (Week 9–12)

**Entry:** Tier 2 PMF (≥4/6 KPIs + owner willing reference).

| Action | Owner | Deliverable |
|--------|-------|-------------|
| Publish anonymized case study | Marketing | PDF + 90-sec video |
| Request 3 warm intros | Owner | Intro emails |
| Convert to paid LOI | Founder | €79–€129/mo or free+data extension |
| Document playbook deltas | Ops | Updated manual-ops from learnings |
| Lock V1.1 CSV import priority | Product | If M10 >3% |

**Exit criteria:** 1 signed intro call **or** paid LOI.

### 6.2 Phase B — Cluster expansion (Month 4–6)

**Entry:** Tier 3 signals (all KPIs + referral + Ellis ≥35%).

| Action | Detail |
|--------|--------|
| **Geo cluster** | Same city as pilot — founder can visit same day |
| **Venue count** | Add 2 venues (total 3) before crossing cities |
| **Onboarding** | 8 h remote per venue (down from 20 h) |
| **Pricing A/B** | Venue B: €79 flat; Venue C: €49 + 0.5% GMV cap €150 |
| **Support** | Shared Slack connect; office hours Tue/Thu |
| **Product** | Ship CSV import (Tier 1) before venue 3 if bill errors >5% |

**Venue selection:** Same ICP rubric ([gtm-plan.md](./gtm-plan.md) §4.2) score ≥70; **must** accept reference call with pilot owner.

**Exit criteria:** 3 venues live; ≥2 paying; M1 ≥45% avg across venues.

### 6.3 Phase C — NL beachhead scale (Month 7–12)

**Entry:** Tier 4 signals on 3-venue cohort (≥55% activation avg, ≥88% completion, waitlist >20).

| Motion | Detail |
|--------|--------|
| **Inbound** | Waitlist prioritized by ICP score |
| **Outbound** | 1 part-time Horeca BD; 20 qualified outreaches/month |
| **Channel** | Horeca Nederland event booth; Mollie co-webinar |
| **Product** | POS read-only for UnTill/Lightspeed top 2 |
| **Pricing** | Default €99/mo + optional 0.3% above €50k GMV |
| **Ops** | Self-serve onboarding beta for ICP ≥80 |

**Target:** 25 venues by month 12 (V2 entry per [mvp-roadmap.md](../product/mvp-roadmap.md)).

### 6.4 Stop / pivot triggers (any phase)

| Trigger | Response |
|---------|----------|
| Activation <30% after retrain at 2 venues | Narrow ICP to 5+ tops only |
| Completion <75% sustained | Engineering sprint: payment UX |
| Owner NPS <+20 | Pause sales; fix product |
| Hijack >5% | Mandatory PIN + fraud sprint |
| Manual errors >12% | Block new venues until CSV shipped |
| Counsel flags EMI creep | Freeze loyalty/wallet GTM permanently |

---

## 7. MVP vs post-MVP PMF scope

| Dimension | MVP PMF (1 venue) | V1.1 PMF (3–10) | V2 PMF (25+) |
|-----------|-------------------|-----------------|--------------|
| **Core proof** | Split-pay works | Replicable across venues | Default option in ICP segment |
| **Integration** | Manual Tier 0 OK | CSV import required | POS sync for some |
| **Accounts / loyalty** | Not required | Nice-to-have | Venue loyalty opt-in |
| **Crypto** | Excluded from PMF | Excluded | Separate eval |
| **Discovery marketplace** | Excluded | Excluded | Excluded |
| **Revenue** | Free OK | ≥1 paying venue | Positive gross margin |
| **Geography** | 1 city | Same metro | NL-wide |
| **Sales motion** | Founder | Founder + reference | BD + inbound |

**Weak assumption challenged:** *PMF requires loyalty wallet and partner rewards.* **Reject.** Those add EMI risk and cold-start failure. Venue-side payment PMF is sufficient for V1.1.

---

## 8. Competitive PMF moat signals

PMF is **not** moat — these signals show **defensibility emerging**:

| Signal | Moat implication |
|--------|------------------|
| Waiters trained on override patterns | Switching cost (SOP embedding) |
| Guest repeat use at same venue (V1.1) | Habit |
| Mollie reconciliation audit trail | Trust / compliance |
| POS adapter live (V2) | Integration lock-in (read-only) |
| Multi-venue guest account (V2+) | Weak until coalition — do not overclaim |

---

## 9. Rollout RACI (post-pilot)

| Activity | Founder | Ops | Eng | Pilot owner |
|----------|---------|-----|-----|-------------|
| Week 8 scorecard | A | R | C | I |
| Case study | A | R | I | C |
| Intro calls | R | C | — | R |
| Venue 2 onboarding | A | R | C | I |
| Pricing test | A | R | — | C |
| V1.1 CSV import | C | I | A/R | I |
| Legal review Connect | A | C | — | — |

*R=Responsible, A=Accountable, C=Consulted, I=Informed*

---

## 10. Example PMF readout (illustrative)

**Pilot:** De Gouden Lepel, Week 8  
**Tier assessment:** **Tier 3 — Strong emerging PMF**

| Signal | Result | Tier |
|--------|--------|------|
| P1 Activation | 52.3% | 2 ✓ |
| P2 Completion | 91.1% | 3 ✓ |
| P3 TTP | 10.1 min | 3 ✓ |
| P4 Guest NPS | +38 | 2 ~ |
| P5 Retention | 9/10 | 3 ✓ |
| P6 Referral | 2 intros (1 signed call) | 3 ✓ |
| P8 Ellis | 33% very disappointed | 2 ~ |
| P10 Support | 6.2 tickets/100 sessions | 2 ✓ |

**Recommendation:** Proceed **Phase B** cluster expansion; run 4-week paid LOI at €99/mo; ship CSV import before venue 3; defer loyalty GTM.

---

## 11. Risks specific to PMF measurement

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Survivorship bias** | Only happy venue measured | Document churned pilots |
| **Founder onsite effect** | Inflated activation | Remote weeks 5–8 weighted higher |
| **Seasonality** | Summer terrace vs winter | Compare like-for-like weeks |
| **Single venue n** | Overfit ICP | Replicate before Tier 4 claim |
| **Free pilot distortion** | Retention drops when priced | Phase B pricing test mandatory |
| **Metric gaming** | Activation on tiny bills | Eligible table definition locked |

---

## 12. Artifacts produced at each tier

| Tier | Required artifacts |
|------|-------------------|
| Tier 2 | Week 8 scorecard PDF; updated objection playbook; 1-page owner ROI |
| Tier 3 | Case study; reference phone list; paid LOI template; V1.1 PRD slice |
| Tier 4 | Pricing page; self-serve onboarding; partner deck for Mollie; waitlist CRM |

---

## Related artifacts

- [gtm-plan.md](./gtm-plan.md) — beachhead and acquisition
- [pilot-scorecard.md](./pilot-scorecard.md) — metric definitions
- [objection-playbook.md](./objection-playbook.md) — sales blockers vs PMF gaps
