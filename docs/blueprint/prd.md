# PART 19 — Master PRD (MVP Consolidation)

**Product:** Rekentafel (codename: TabSettle)  
**Version:** MVP Pilot v1.0  
**Market:** Netherlands-first  
**Last updated:** 2026-06-26  
**Status:** Blueprint — execution-ready

This PRD consolidates positioning, MVP scope, flows, and surfaces. **Detailed specs live in linked docs** — this document is the single entry point for engineering, design, and pilot sales.

---

## 1. Product positioning

### Problem

Dutch table-service restaurants lose table turns and guest goodwill to **one-payer-plus-Tikkie** settlement. Full QR ordering fixes payment but removes waiter-led hospitality.

### Solution

Persistent table QR → menu/call-server pre-meal → waiter-activated payment session → collaborative itemized splits → per-guest Mollie checkout → table close at €0 remaining.

### Positioning statement

**For** independent table-service restaurants in the Netherlands **who** lose time to one-payer settlement, **Rekentafel** is a table QR payment session platform **that** lets guests split and pay the open bill via iDEAL **unlike** full QR ordering or post-meal Tikkie **because** waiters stay authoritative on ordering while multi-payer checkout runs in parallel on guest phones.

**Deep dive:** [positioning.md](../product/positioning.md) · [elevator-pitch.md](../product/elevator-pitch.md) · [competitive-matrix.md](../product/competitive-matrix.md)

### Name status

| Candidate | Status |
|-----------|--------|
| **Rekentafel** | Recommended consumer brand (NL-first) |
| TabSettle | Recommended engineering codename |
| SplitTable, BillQR | Alternatives — see [open-questions.md](./open-questions.md) |

---

## 2. Target users and jobs-to-be-done

| Persona | Job to be done | MVP must deliver |
|---------|----------------|------------------|
| **Guest** | Pay only what I consumed, quickly, no Tikkie chase | No forced account; item/equal/custom/shared split; iDEAL |
| **Waiter** | Close tables fast without payment support duty | ≤2 taps to activate payment; progress monitor; override |
| **Owner/GM** | Faster turns without POS rip-and-replace | Table QR setup, menu, Mollie connect, audit |
| **Platform ops** | Reconcile payments, handle incidents | Webhook dashboard, manual refund path, audit export |

**Weak assumption rejected:** Mandatory guest accounts for MVP — conversion drops 40–60% at table; account is opt-in post-payment (V1.1 full history).

---

## 3. MVP scope

### 3.1 In scope (must ship for pilot)

| Domain | Requirements |
|--------|--------------|
| **Table QR** | Persistent QR per table; resolves venue + table; empty-table menu + call server |
| **Session model** | States: `EMPTY → SEATED → PAYMENT_ACTIVE → CLOSED` |
| **Bill source** | Waiter manual entry OR CSV/simple import |
| **Payment gate** | Bill hidden until waiter activates payment + issues session token |
| **Guest join** | Nickname; optional 6-digit PIN; no account required |
| **Split modes** | Item claim, equal split (subset or full), custom € amount, shared-item N-way |
| **Money display** | Line-level VAT (9%/21% NL hospitality); service charge; per-guest tip |
| **Payments** | One Mollie Payment per guest checkout; partial pay; remaining balance |
| **Staff control** | Override claims, force equal, lock session, close table |
| **Admin** | Tables, QR PDF, menu CRUD, staff roles, Mollie OAuth connect |
| **Ops** | Webhook reconciliation, audit logs, manual chargeback queue |
| **Compliance posture** | No stored value; restaurant MoR; GDPR-minimal retention |

### 3.2 Explicitly out of scope (MVP)

| Exclusion | Rationale doc |
|-----------|---------------|
| Full QR phone ordering | [scope-boundary.md](../product/scope-boundary.md) §9 |
| Public live bill on raw QR | Security invariant — [flows-a-o.md](../flows/flows-a-o.md) |
| Crypto payments | [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) |
| Stored-value wallet / overpay credit | [regulatory-framing.md](../domain/loyalty/regulatory-framing.md) |
| Coalition partner rewards | [scope-boundary.md](../product/scope-boundary.md) §2 |
| Discovery / ML recommendations | [scope-boundary.md](../product/scope-boundary.md) §4–5 |
| POS bi-directional sync | [integration-tiers.md](../integrations/integration-tiers.md) |
| Native iOS/Android apps | Web-first — [tech-stack.md](../architecture/tech-stack.md) |
| Automated chargeback automation | Manual ops queue MVP |

**Full feature tags:** [mvp-roadmap.md](../product/mvp-roadmap.md)

### 3.3 MVP success criteria

| Type | Criterion |
|------|-----------|
| Quantitative | ≥70% pilot table closes via split-pay; ≤8% override rate; ≤12 min median pay phase |
| Qualitative | Waiter authority preserved; bill not public by QR alone; partial pay accurate; audit reconstructable |
| Engineering | Table 12 worked example passes in staging with €0,00 remaining |

---

## 4. Core user flows (summary)

Fifteen flows (A–O) are specified in [flows-a-o.md](../flows/flows-a-o.md). MVP-critical subset:

| Flow | Name | MVP | Summary |
|------|------|-----|---------|
| **A** | Empty-table QR scan | Yes | Menu + table context; no bill |
| **B** | Call server / ready to order | Yes | Signal to staff inbox; 60s cooldown |
| **C** | Waiter starts session | Yes | `IDLE → SEATED`; optional covers count |
| **D** | Payment join | Yes | Token/PIN gate; lobby with participants |
| **E** | Item claiming | Yes | Single claimant per allocatable unit; optimistic lock |
| **F** | Equal split | Yes | 2-of-4 or all-N; preview before commit |
| **G** | Custom amount | Yes | Fixed €; validated vs remaining |
| **H** | Shared items | Yes | N-way split on bottle/platter |
| **I** | Tip | Yes | € or % presets; included in Mollie amount |
| **J** | Payment result / partial | Yes | Remaining balance; retry; session expiry |
| **K** | Loyalty accrual | Minimal | Post-pay account link only — no points |
| **L** | Overpay-to-rewards | **Deferred** | No UI |
| **M** | Partner redemption | **Deferred** | No UI |
| **N** | Restaurant onboarding | Yes | Admin: venue, tables, menu, Mollie |
| **O** | Staff daily ops | Yes | Floor grid, signals, bill, pay monitor, close |

**Diagrams:** [docs/flows/diagrams/](../flows/diagrams/)  
**Events:** [event-catalog.md](../flows/event-catalog.md) · [error-state-matrix.md](../flows/error-state-matrix.md)

### Session state machine (MVP)

```
EMPTY ──waiter start──► SEATED ──activate payment──► PAYMENT_ACTIVE ──close──► CLOSED
```

Bill settlement sub-states (`BILL_DRAFT → ALLOCATION_OPEN → PARTIALLY_PAID → FULLY_PAID → CLOSED`): [state-machines.md](../domain/split-engine/state-machines.md)

---

## 5. Product surfaces (summary)

| Surface | Base path | Auth | MVP flows |
|---------|-----------|------|-----------|
| Guest web | `/t/:slug/:tableCode` | Ephemeral guest token | A, B, D–J |
| Staff panel | `/staff` | Staff JWT | B inbox, C, E–J monitor, overrides |
| Restaurant admin | `/admin` | Admin JWT | N, config, Mollie |
| Platform ops | `/ops` | Platform SSO + MFA | Webhooks, audit, incidents |
| Partner dashboard | `/partners` | — | Post-MVP |

**Deep dive:** [surface-map.md](../surfaces/surface-map.md) · [screen-inventory.md](../surfaces/screen-inventory.md) · [rbac-matrix.md](../surfaces/rbac-matrix.md)

---

## 6. Functional requirements by domain

### 6.1 Bill and split engine

| Req ID | Requirement | Spec |
|--------|-------------|------|
| SPL-01 | Item-level claiming with qty units | [rules-spec.md](../domain/split-engine/rules-spec.md) |
| SPL-02 | Equal, custom, shared split modes | [rules-spec.md](../domain/split-engine/rules-spec.md) §3–6 |
| SPL-03 | Service charge allocation proportional to claimed subtotal | [rules-spec.md](../domain/split-engine/rules-spec.md) |
| SPL-04 | VAT visibility per line (9%/21%) | [rules-spec.md](../domain/split-engine/rules-spec.md) |
| SPL-05 | Concurrent claim protection (409 on conflict) | [concurrency.md](../domain/split-engine/concurrency.md) |
| SPL-06 | Unclaimed remainder → waiter force-equal or single payer | [rules-spec.md](../domain/split-engine/rules-spec.md) |
| SPL-07 | Numeric fixtures pass (6 worked examples) | [worked-examples.md](../domain/split-engine/worked-examples.md) |

### 6.2 Payments (Mollie)

| Req ID | Requirement | Spec |
|--------|-------------|------|
| PAY-01 | Create Mollie Payment per guest checkout on restaurant org | [payment-architecture.md](../architecture/payments/payment-architecture.md) |
| PAY-02 | Hosted checkout redirect + return URL handling | [payment-architecture.md](../architecture/payments/payment-architecture.md) §2.2 |
| PAY-03 | Webhook ingress + idempotent `tr_*` reconciliation | [webhook-reconciliation.md](../architecture/payments/webhook-reconciliation.md) |
| PAY-04 | Partial payment aggregation at table session | [payment-architecture.md](../architecture/payments/payment-architecture.md) |
| PAY-05 | Refund initiation logged (manager via Mollie + app audit) | [manual-ops-playbook.md](../integrations/manual-ops-playbook.md) |
| PAY-06 | No crypto endpoints in MVP | [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) §1 |

### 6.3 API and data

| Req ID | Requirement | Spec |
|--------|-------------|------|
| API-01 | REST + OpenAPI 3.1; money as integer cents | [service-map.md](../architecture/api/service-map.md) |
| API-02 | Guest SSE for bill sync; staff WebSocket for floor | [service-map.md](../architecture/api/service-map.md) |
| API-03 | Idempotency-Key on mutating routes | [idempotency-concurrency.md](../architecture/api/idempotency-concurrency.md) |
| API-04 | Entity model: sessions, bills, claims, payment_intents | [entity-dictionary.md](../architecture/data-model/entity-dictionary.md) |
| API-05 | Auth: guest ephemeral token, staff/admin JWT | [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) |
| API-06 | Background jobs: webhook reconcile, session expiry | [background-jobs.md](../architecture/api/background-jobs.md) |

### 6.4 Security and compliance (MVP P0)

| Req ID | Requirement | Spec |
|--------|-------------|------|
| SEC-01 | Payment session token TTL + refresh | [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) |
| SEC-02 | No PAN storage; Mollie hosted checkout only | [mvp-security-checklist.md](../security/mvp-security-checklist.md) |
| SEC-03 | GDPR retention: guest PII 90d post-close | [data-classification.md](../architecture/data-model/data-classification.md) |
| SEC-04 | Audit log for claims, payments, overrides | [threat-register.md](../security/threat-register.md) |

---

## 7. Non-functional requirements

| NFR | MVP target | Reference |
|-----|------------|-----------|
| Guest checkout latency (excl. iDEAL) | p95 < 800ms API | [observability-testing.md](../architecture/observability-testing.md) |
| Concurrent guests per table | 12 joins default | [flows-a-o.md](../flows/flows-a-o.md) Flow D |
| Uptime (pilot) | 99.5% business hours | [infra-diagram.mmd](../architecture/infra-diagram.mmd) |
| Accessibility | 44px touch targets; modal focus trap | [ux-principles.md](../ux/ux-principles.md) |
| Localization | NL primary; EN guest toggle | [positioning.md](../product/positioning.md) |
| Payment trust UX | MoneyDisplay from ui-core only | [payment-trust-patterns.md](../ux/payment-trust-patterns.md) |

---

## 8. Post-MVP roadmap (reference only)

| Phase | Focus | Key additions |
|-------|-------|---------------|
| **V1.1** | 3–10 venues | Guest accounts, POS read-only, payout view, geo optional, in-app refunds |
| **V2** | 25+ venues | Mollie Connect fees, venue loyalty, bi-directional POS (selected), crypto eval |
| **Never (now)** | — | See [scope-boundary.md](../product/scope-boundary.md) |

---

## 9. Engineering delivery

| Artifact | Link |
|----------|------|
| Workstream plan (ws-1–ws-4) | [workstream-plan.md](../engineering/workstream-plan.md) |
| Implementation roadmap (6 weeks) | [implementation-roadmap.md](../engineering/implementation-roadmap.md) |
| Repo structure | [repo-structure.md](../engineering/repo-structure.md) |
| Branching & merge protocol | [branching-and-merge.md](../engineering/branching-and-merge.md) |
| Tech stack | [tech-stack.md](../architecture/tech-stack.md) |

---

## 10. GTM and pilot

| Artifact | Link |
|----------|------|
| GTM plan | [gtm-plan.md](../gtm/gtm-plan.md) |
| Pilot scorecard | [pilot-scorecard.md](../gtm/pilot-scorecard.md) |
| Restaurant value one-pager | [restaurant-value-onepager.md](../business/restaurant-value-onepager.md) |
| Objection playbook | [objection-playbook.md](../gtm/objection-playbook.md) |

---

## 11. Assumption challenges (PRD-level)

| Assumption | Verdict | PRD decision |
|------------|---------|--------------|
| QR alone unlocks bill | Reject | Waiter token required |
| Geo-fence alone stops hijacking | Weak | Waiter unlock primary; geo V1.1 optional |
| Manual bill entry blocks pilot | Acceptable | One venue; ≤2 min entry target |
| Crypto + Mollie same integration | False | Mollie MVP; crypto separate V2+ rail |
| Overpay wallet drives loyalty | Risky | Tips only MVP; no stored balance |
| POS sync required day one | Reject | Manual/CSV MVP; read-only V1.1 |

---

## 12. Related blueprint artifacts

| Document | Purpose |
|----------|---------|
| [executive-summary.md](./executive-summary.md) | Standalone 5-min overview |
| [user-stories.md](./user-stories.md) | MVP stories → ws-1/ws-2/ws-3 |
| [system-architecture-overview.md](./system-architecture-overview.md) | Architecture doc index |
| [open-questions.md](./open-questions.md) | Founder decision log |

---

*Slice ownership: PART 19 — Master PRD Compilation. Source parts: 1–6.*
