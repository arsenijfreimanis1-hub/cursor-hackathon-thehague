# MVP vs Post-MVP Priority Roadmap

**Product (working name):** TabSettle / SplitTable / Rekentafel / BillQR — TBD  
**Market:** Netherlands-first hospitality fintech  
**Pilot constraint:** One venue, manual bill entry, Mollie split-pay, waiter-activated payment mode  

This document tags every feature **MVP | V1.1 | V2 | Never** and defines verifiable exit criteria per phase.

---

## Phase Summary

| Phase | Goal | Venue count | Bill source | Payments | Success signal |
|-------|------|-------------|-------------|----------|----------------|
| **MVP** | Prove split-pay removes Tikkie friction without breaking service | 1 pilot | Waiter manual entry or CSV import | Mollie (iDEAL/cards/wallets) | ≥70% of pilot tables close via split-pay within 8 weeks |
| **V1.1** | Reduce ops friction and repeat usage | 3–10 venues | + POS read-only import | Same + payout reporting | Waiter activation <30s; <5% claim disputes |
| **V2** | Network effects and integrations | 25+ venues | Bi-directional POS (selected vendors) | Mollie Connect; optional crypto rail | POS-synced bills; optional accounts/loyalty |
| **Never (for now)** | Regulatory/scope traps | — | — | — | Explicit deferral — see Do-Not-Build |

---

## MVP Success Definition (Single NL Pilot)

The MVP is **not** a loyalty platform, discovery app, or ordering system. It is a **trustworthy bill visibility + collaborative split-pay** layer on top of waiter-controlled service.

### Primary outcome

Guests at an open table can join a **waiter-activated payment session**, claim or split items, tip individually, and pay their portion via Mollie while the restaurant sees a reconciled remaining balance until the table closes.

### Quantitative pilot targets (8-week window)

| Metric | Target | Rationale |
|--------|--------|-----------|
| Tables using payment mode per service | ≥40% of seated tables with bill >€30 | Validates adoption beyond novelty |
| Split-pay completion rate | ≥85% of activated sessions reach €0 remaining | Core product promise |
| Median time from “payment mode on” to table close | ≤12 minutes | Must beat “one payer + Tikkie chase” |
| Claim dispute rate (waiter override) | ≤8% of sessions | Fraud/UX guardrails working |
| Payment failure + successful retry | ≥90% of failed checkouts retry successfully | Mollie UX acceptable |
| Guest account creation | Optional; ≤15% uptake acceptable | Accounts are not MVP dependency |

### Qualitative gates (all must pass)

1. **Waiter authority preserved** — no guest-initiated orders; payment mode requires staff action.
2. **Bill not public by QR alone** — persistent table QR never exposes live bill without short-lived session token.
3. **VAT line items visible** — split amounts match merchant receipt expectations (9%/21% NL hospitality).
4. **Partial pay works** — 4 guests, 2 pay now, 2 pay later; remaining balance accurate.
5. **Audit trail** — every claim, payment, override, and webhook event reconstructable for one table.

### Example MVP session (concrete)

**Table 12, 4 guests, bill €126.40**

| Line | Qty | Unit | VAT | Line total |
|------|-----|------|-----|------------|
| Burger | 2 | €14.50 | 9% | €29.00 |
| Steak | 1 | €28.00 | 9% | €28.00 |
| House wine (bottle) | 1 | €32.00 | 21% | €32.00 |
| Cola | 2 | €3.50 | 9% | €7.00 |
| Service charge (optional venue setting) | — | 10% | 9% | €9.60 |
| **Total** | | | | **€105.60** *(ex-VAT subtotal + service; VAT shown separately in UI)* |

- Guest A claims 1 burger + 1 cola → €18.00 + VAT share + tip €2 → pays €21.50 via iDEAL.
- Guest B claims steak + half wine (shared) → pays €42.00 + tip.
- Guests C & D equal-split remainder → €30.10 each.
- Waiter closes table when remaining = €0.00.

---

## Feature Roadmap Tables

### Guest experience

| Feature | Tag | MVP scope | V1.1 | V2 |
|---------|-----|-----------|------|-----|
| Scan persistent table QR | **MVP** | Resolves venue + table ID | Same | Deep links for marketing |
| Empty-table: menu only | **MVP** | Static/cached menu, table label | Menu sync from admin | Allergen filters |
| Empty-table: call server / ready signal | **MVP** | Push to staff console; no SLA guarantee | Ack + ETA optional | Priority queue rules |
| Full QR phone ordering | **Never** | — | — | — |
| Waiter-activated table session | **MVP** | Staff toggles “seated / ordering” | Auto-suggest from covers count | POS-triggered session (read-only) |
| Waiter-activated payment mode + session token | **MVP** | Short-lived token (e.g. 2h TTL, refreshable) | Configurable TTL per venue | Token tied to POS check ID |
| Public live bill on raw QR | **Never** | Blocked by design | — | — |
| Join payment session (no account) | **MVP** | Nickname + browser session | SMS magic link optional | Account merge |
| View itemized bill with VAT | **MVP** | Per-line VAT rate + amounts | Rounding policy config | Multi-currency display (EUR only MVP) |
| Item-level claiming | **MVP** | Single claimant per line qty unit | Partial qty split UI | — |
| Equal split (subset or full table) | **MVP** | 2 of 4, or all 6, etc. | Save split presets | — |
| Custom amount split | **MVP** | Fixed € amounts; validation vs remaining | Percentage mode | — |
| Shared-item split | **MVP** | Split bottle/wine/platter N-way | Auto-suggest even split | — |
| Per-guest tip | **MVP** | € or %; pass-through to venue config | Tip pool reporting | Staff payout export |
| Mollie checkout (iDEAL/cards/wallets) | **MVP** | Hosted checkout per guest payment | Apple Pay prominence | Connect split payouts |
| Partial payments + remaining balance | **MVP** | Real-time balance bar | Push “your friends still owe €X” | — |
| Payment retry on failure | **MVP** | Same claim lock for 15 min | — | — |
| Optional guest account | **V1.1** | — | Email login; visit history | Social login |
| Visit history | **V1.1** | — | Per-venue history | Cross-venue (GDPR) |
| Loyalty accrual | **V2** | — | Points preview only | Full earn/burn at venue |
| Overpay-to-rewards / stored balance | **Never** | — | — | — |
| Restaurant discovery feed | **Never** | — | — | — |
| ML personalized suggestions | **Never** | — | — | — |
| Native iOS/Android apps | **Never** | Responsive web only | PWA install prompt | Evaluate native if retention data supports |

### Staff / waiter

| Feature | Tag | MVP scope | V1.1 | V2 |
|---------|-----|-----------|------|-----|
| Staff web panel (mobile-first) | **MVP** | Login, table list, session controls | Offline-tolerant UI | Native wrapper optional |
| Start/end table session | **MVP** | Manual | Cover count field | POS auto-open |
| Activate payment mode | **MVP** | One tap; issues session token | Training mode / demo | Auto on POS “print check” |
| Manual bill entry | **MVP** | Add lines, qty, price, VAT rate | Templates / favorites | — |
| CSV/simple bill import | **MVP** | One-off import per session | Scheduled re-import | — |
| Waiter override claims | **MVP** | Reassign line, force equal split, lock guest | Audit reason codes | — |
| Close table / force settle | **MVP** | Block new joins; mark cash remainder | Manager PIN | — |
| Call-server inbox | **MVP** | List + dismiss | Sound/vibration prefs | — |
| POS read-only sync | **V1.1** | — | Selected NL POS (UnTill, Lightspeed export) | — |
| Deep POS bi-directional order sync | **Never** | — | — | — |
| Shift analytics | **V1.1** | — | Tips, split-pay %, overrides | — |
| Multi-venue franchise analytics | **Never** | — | — | — |

### Restaurant admin

| Feature | Tag | MVP scope | V1.1 | V2 |
|---------|-----|-----------|------|-----|
| Venue onboarding | **MVP** | Tables, QR PDF export, menu CRUD | Bulk table import | Self-serve KYC flow |
| Staff roles (waiter/manager) | **MVP** | RBAC basic | Custom roles | SSO |
| Menu management | **MVP** | Categories, prices, VAT | Photos | Multi-language |
| Mollie connection | **MVP** | Restaurant-owned Mollie API key (pilot) | Mollie Connect onboarding | Platform split fees |
| Service charge rules | **MVP** | On/off + % | Mandatory vs optional flag | — |
| Refund initiation | **MVP** | Manager manual via Mollie dashboard + log in app | In-app partial refund | Split refund rules engine |
| Payout/settlement view | **V1.1** | — | T+1/T+2 visibility | Reconciliation export |
| Loyalty program config | **V2** | — | — | Venue-specific points |
| Partner rewards marketplace | **Never** | — | — | — |

### Platform ops

| Feature | Tag | MVP scope | V1.1 | V2 |
|---------|-----|-----------|------|-----|
| Pilot venue provisioning | **MVP** | Manual ops | Self-serve waitlist | — |
| Webhook reconciliation dashboard | **MVP** | Mollie payment ↔ claim mapping | Alert on mismatch | — |
| Audit logs (immutable) | **MVP** | Claims, payments, overrides | Export | SIEM integration |
| Chargeback/dispute queue | **MVP** | Manual ops spreadsheet + status field | In-app queue | — |
| Automated chargeback automation | **Never** | — | — | — |
| Fraud rules (velocity, IP) | **V1.1** | — | Basic heuristics | ML risk scoring |
| Crypto payment rail | **Never** | — | — | Separate regulated eval in V2+ |

### Payments & compliance

| Feature | Tag | MVP scope | V1.1 | V2 |
|---------|-----|-----------|------|-----|
| Mollie primary PSP | **MVP** | iDEAL, cards, wallets Mollie supports | — | Mollie Connect |
| Platform as pure SaaS on merchant Mollie | **MVP** | Pilot legal posture; no fund holding | Legal review for Connect | — |
| PSD2-compliant guest checkout | **MVP** | Redirect/hosted; no stored PAN | — | — |
| Crypto payments | **Never** | — | — | Optional V2+ rail if licensed/partnered |
| Stored-value wallet / e-money | **Never** | — | — | — |
| Geo/proximity gate for payment join | **V1.1** | MVP: waiter unlock only | Optional WiFi/BT beacon | — |

---

## MVP Delivery Checklist (Engineering)

Ordered build sequence for parallel team — foundations first.

| # | Deliverable | Tag | Exit artifact |
|---|-------------|-----|---------------|
| 1 | Table + QR registry; empty-table guest page | MVP | QR resolves to menu + table context |
| 2 | Staff auth + table session state machine | MVP | Session states: `empty → seated → payment_active → closed` |
| 3 | Manual bill entry + VAT fields | MVP | Bill totals match waiter-entered receipt |
| 4 | Payment session token issuance | MVP | Bill hidden until token valid |
| 5 | Multi-guest join + claim engine (optimistic lock) | MVP | No double-allocation in concurrent test |
| 6 | Split modes: item, equal, custom, shared | MVP | Numeric examples pass (see above) |
| 7 | Tip + Mollie checkout per guest | MVP | Successful iDEAL test payment |
| 8 | Partial pay + remaining balance | MVP | 4-guest partial scenario passes |
| 9 | Webhooks + reconciliation log | MVP | Ops can trace payment ID → guest claim |
| 10 | Waiter override + table close | MVP | Manager can resolve dispute in <2 min |
| 11 | Restaurant admin (tables, menu, roles) | MVP | Pilot venue self-manages menu |
| 12 | Audit log export | MVP | JSON/CSV for one session |

---

## V1.1 Scope (Post-Pilot, Pre-Scale)

**Theme:** Operational efficiency and trust at 3–10 venues — still no network effects.

| Capability | Rationale |
|------------|-----------|
| Optional guest accounts + visit history | Repeat diners ask for receipts; low regulatory burden vs wallet |
| POS read-only import (CSV/API) | Cuts manual entry errors; not full order sync |
| Payout/settlement reporting | Restaurants ask “where is my money?” after week 2 |
| Geo/proximity optional gate | Reduces bill hijacking if pilot sees abuse |
| In-app partial refunds | Manager workflow without Mollie dashboard context switch |
| PWA install + push (web) | Native apps deferred; installable web sufficient |
| Basic fraud heuristics | Velocity limits on payment joins from distant IPs |

**V1.1 explicit non-goals:** coalition loyalty, discovery, crypto, bi-directional POS, gamification.

---

## V2 Scope (Scale & Network)

**Theme:** Integrations and retention mechanics — only after split-pay PMF proven.

| Capability | Rationale | Dependency |
|------------|-----------|------------|
| Mollie Connect platform fees | Sustainable bps revenue | Legal entity + KYC flow |
| Bi-directional POS (vendor-specific) | Order + pay reconciliation | V1.1 read-only stable |
| Venue loyalty earn (non-transferable points) | Retention without e-money | Legal opinion on points vs wallet |
| Cross-venue coalition loyalty | Partner discounts | EMI/partner contracts — high bar |
| Crypto payment rail (optional) | Niche demand | Separate PSP or licensed partner — not Mollie core |
| Recommendation surfaces (opt-in history) | Upsell within venue | GDPR DPIA |
| Self-serve onboarding | Reduce ops headcount | Fraud controls mature |

---

## Table Session State Machine (MVP)

```
                    ┌─────────────┐
         scan QR    │   EMPTY     │  menu + call server only
        ──────────► │  (no bill)  │
                    └──────┬──────┘
                           │ waiter: start session
                           ▼
                    ┌─────────────┐
                    │   SEATED    │  ordering via waiter (off-platform)
                    │  (no bill   │
                    │   visible)  │
                    └──────┬──────┘
                           │ waiter: enter bill + activate payment
                           ▼
                    ┌─────────────┐
                    │  PAYMENT    │  session token issued
                    │  _ACTIVE    │  claims + Mollie checkouts
                    └──────┬──────┘
                           │ remaining = 0 OR waiter force close
                           ▼
                    ┌─────────────┐
                    │   CLOSED    │  audit frozen
                    └─────────────┘
```

**MVP rule:** Scanning QR in `EMPTY` or `SEATED` never shows line items. Only `PAYMENT_ACTIVE` + valid token shows bill.

---

## Do-Not-Build-Yet (Never / Deferred)

Every master-prompt exclusion appears below with tag and one-line rationale.

| Feature | Tag | Rationale | Revisit when |
|---------|-----|-----------|--------------|
| Crypto payments | **Never** (MVP/V1.1) | Separate regulatory rail; Mollie does not replace licensed crypto settlement; distracts from iDEAL PMF | V2 eval with licensed partner; not bundled |
| Cross-restaurant partner rewards marketplace | **Never** (MVP/V1.1) | Requires coalition deals, redemption ops, EMI analysis | V2+ after venue density |
| Restaurant discovery feed | **Never** | Two-sided marketplace cold-start; unrelated to split-pay wedge | Post-25 venues optional |
| ML personalized recommendations | **Never** | Needs history scale + GDPR profiling DPIA; weak pilot signal | Opt-in V2 within-venue only |
| Stored-value wallet / overpay-as-cash-balance | **Never** | E-money (EMI) risk; PSD2 scope creep; accounting complexity | Legal structure clear; never as “cash balance” |
| Full QR phone ordering | **Never** | Conflicts with waiter-controlled positioning; different product category | Never — core differentiation |
| Native iOS/Android apps | **Never** (MVP/V1.1) | Web-first sufficient for scan-to-pay; 2× maintenance | Retention data + PWA limits hit |
| Multi-venue franchise analytics suite | **Never** (MVP/V1.1) | Enterprise sales cycle; pilot is single venue | 50+ venue groups ask |
| Automated chargeback dispute automation | **Never** (MVP/V1.1) | Edge cases need human judgment; low volume initially | >100 disputes/month |
| Deep POS bi-directional order sync | **Never** (MVP/V1.1) | Integration complexity; waiter entry proves value first | V2 per-vendor contracts |
| Gamified rewards farming mechanics | **Never** | Fraud/abuse magnet; regulatory scrutiny | N/A — rejected |
| Public live bill on QR without waiter token | **Never** | Bill hijacking, privacy, fraud | Never — security invariant |

---

## Cross-Reference: Master Prompt Exclusions

| Master prompt “do not build yet” | Row in Do-Not-Build | MVP alternative |
|----------------------------------|---------------------|-----------------|
| Crypto payments | Crypto payments | Mollie only |
| Coalition partner rewards | Cross-restaurant partner rewards | None |
| Discovery + recommendations | Discovery feed + ML recommendations | Menu on empty table only |
| Stored-value wallet / overpay | Stored-value wallet | Tip only; no platform credit |
| Full QR ordering | Full QR phone ordering | Call server signal |
| Native apps | Native iOS/Android | Responsive web |
| Franchise analytics | Multi-venue franchise analytics | Single-venue admin |
| Chargeback automation | Automated chargeback automation | Manual ops queue |
| POS bi-directional sync | Deep POS bi-directional order sync | Manual/CSV bill |
| Gamified rewards | Gamified rewards farming | None |
| Public bill without token | Public live bill on QR | Waiter-activated token |

---

## Risk Register (Scope-Specific)

| Risk | Phase | Mitigation in scope |
|------|-------|---------------------|
| PSD2 / EMI scope creep | MVP | No stored value; funds to merchant Mollie account |
| Bill hijacking via shared QR photo | MVP | Payment token + optional V1.1 geo |
| Double-allocation on concurrent claims | MVP | Optimistic locking + waiter override |
| VAT display errors on splits | MVP | Line-level VAT; round per guest with explicit rule |
| Waiter training burden | MVP | Single “activate payment” affordance; in-app 60s tutorial |
| Mollie settlement T+1/T+2 vs cash expectations | MVP | Set expectation in admin onboarding copy |
| Chargeback on partial group bill | MVP | Manual ops queue; link payment to claim snapshot |
| GDPR over-retention of guest sessions | MVP | TTL delete guest PII 90 days post-close unless account |

---

## Open Questions (Scope Decisions Pending)

| Question | MVP default | Affects tag |
|----------|-------------|-------------|
| Product name final | Use internal codename “TabSettle” in docs | — |
| Pricing: SaaS vs bps | Pilot free; log transaction cost for V1.1 | V1.1 |
| Payment facilitator vs SaaS on merchant Mollie | SaaS on merchant key for pilot | MVP legal |
| Proximity check vs waiter unlock only | Waiter unlock only for MVP | V1.1 geo |
| Tip pass-through vs pool | Venue-configurable; pass-through default | MVP |
| Single Mollie account vs Connect | Single merchant account MVP | V2 Connect |

---

*Slice ownership: Part 4 — MVP vs Post-MVP Scope Boundary. Files: `docs/product/mvp-roadmap.md`, `docs/product/scope-boundary.md`.*
