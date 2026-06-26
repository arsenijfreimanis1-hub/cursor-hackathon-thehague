# Screen Inventory & Route Catalog

**Product (working name):** Rekentafel  
**Base URL (production):** `https://app.rekentafel.nl`  
**Ops URL:** `https://ops.rekentafel.nl`  
**Slice:** Role-Based Surfaces — Screen Inventory  
**Status:** Blueprint — execution-ready  
**Last updated:** 2026-06-26  
**Companion:** [surface-map.md](./surface-map.md), [rbac-matrix.md](./rbac-matrix.md), [../flows/flows-a-o.md](../flows/flows-a-o.md)

---

## Route Conventions

| Convention | Rule |
|------------|------|
| `:slug` | Restaurant URL slug (e.g. `de-gouden-schaar`) |
| `:tableCode` | Short table code on QR (e.g. `12`, `A3`) |
| `:tableId` | Internal UUID in staff/admin APIs |
| `:ps` | Payment session join token query param `?ps=` |
| Auth guards | `G` guest, `S` staff, `A` admin, `O` ops, `P` partner |
| MVP tag | **MVP** \| V1.1 \| V2 \| **DEFERRED** |

**QR payload (persistent):**

```
https://app.rekentafel.nl/t/{slug}/{tableCode}
```

**Payment deep link (waiter-issued):**

```
https://app.rekentafel.nl/t/{slug}/{tableCode}/pay/join?ps={token}
```

---

## Flow → Screen Index

| Flow | Screen IDs (this doc) |
|------|------------------------|
| A — Empty-table QR | G-001, G-002, G-003, G-010 |
| B — Call server | G-004, G-005, S-003, S-004 |
| C — Waiter session | S-001, S-005, S-006, S-007 |
| D — Payment join | G-006, G-007, S-008 |
| E — Claims | G-008, G-009, S-010, S-011 |
| F — Equal split | G-012 |
| G — Custom amount | G-013 |
| H — Shared items | G-008 (badge), G-014, S-007 |
| I — Tip | G-015 |
| J — Payment / partial | G-016, G-017, G-018, S-008, S-009, O-006–O-010 |
| K — Loyalty | G-019, G-020, A-012 |
| L — Overpay | **None (DEFERRED)** |
| M — Partner redeem | P-* **(DEFERRED)** |
| N — Onboarding | A-001–A-011, O-003, O-004 |
| O — Daily ops | S-002, S-006–S-012, A-013 |

---

## 1. Guest Web App Routes (`/t/*`)

### 1.1 Public / pre-join

| ID | Route | Screen name | MVP | Flow | Auth | Description |
|----|-------|-------------|-----|------|------|-------------|
| G-001 | `/t/:slug/:tableCode` | Table landing | **MVP** | A | G | Restaurant name, table #, state banner, nav to menu/signal/pay |
| G-002 | `/t/:slug/:tableCode/menu` | Menu categories | **MVP** | A | G | Category grid; read-only |
| G-003 | `/t/:slug/:tableCode/menu/:categoryId` | Menu category items | **MVP** | A | G | Items, allergens, VAT-inclusive note |
| G-004 | `/t/:slug/:tableCode/signal` | Call server | **MVP** | B | G | CTA: "Call server" / "Ready to order" |
| G-005 | `/t/:slug/:tableCode/signal/sent` | Signal confirmation | **MVP** | B | G | "Server notified" + optional ack polling |
| G-010 | `/t/:slug/:tableCode/closed` | Restaurant/table inactive | **MVP** | A | G | Friendly 404/closed states |

### 1.2 Payment session (token-gated)

| ID | Route | Screen name | MVP | Flow | Auth | Description |
|----|-------|-------------|-----|------|------|-------------|
| G-006 | `/t/:slug/:tableCode/pay/join` | Payment join gate | **MVP** | D | G | PIN entry; "Ask server to open bill" if no session |
| G-007 | `/t/:slug/:tableCode/pay/lobby` | Payment lobby | **MVP** | D | G+join | Participants, remaining balance, links to bill/split |
| G-008 | `/t/:slug/:tableCode/pay/bill` | Bill & claims | **MVP** | E, H | G+join | Line items, claim steppers, shared badges |
| G-009 | `/t/:slug/:tableCode/pay/my-share` | My share summary | **MVP** | E | G+join | Running subtotal for participant |
| G-014 | `/t/:slug/:tableCode/pay/shared/:lineId` | Shared item split | **MVP** | H | G+join | Denominator preview, per-person amount |
| G-012 | `/t/:slug/:tableCode/pay/split/equal` | Equal split setup | **MVP** | F | G+join | Participant checkboxes, formula preview |
| G-013 | `/t/:slug/:tableCode/pay/split/custom` | Custom amount | **MVP** | G | G+join | Keypad; min €0.50, max remaining |
| G-015 | `/t/:slug/:tableCode/pay/checkout` | Tip & checkout summary | **MVP** | I | G+join | Tip presets, total, "Pay with iDEAL/card" |
| G-016 | `/t/:slug/:tableCode/pay/redirect` | Mollie redirect shim | **MVP** | J | G+join | Loading state during hosted checkout |
| G-017 | `/t/:slug/:tableCode/pay/result/:paymentId` | Payment result | **MVP** | J | G+join | Success / pending / failed |
| G-018 | `/t/:slug/:tableCode/pay/remaining` | Remaining balance | **MVP** | J | G+join | Post-partial pay; who still owes |
| G-011 | `/t/:slug/:tableCode/pay/closed` | Session closed | **MVP** | J | G | "Bill closed — thank you" |

### 1.3 Guest account (optional, Flow K minimal)

| ID | Route | Screen name | MVP | Flow | Auth | Description |
|----|-------|-------------|-----|------|------|-------------|
| G-019 | `/account/link` | Link account | **MVP** | K | G | Email magic link post-payment |
| G-020 | `/account` | Account home | **MVP** | K | Account | Visits, points, receipts (single venue) |
| G-021 | `/account/visits/:visitId` | Visit receipt | **MVP** | K | Account | Itemized receipt for visit |
| G-022 | `/account/settings` | Account settings | V1.1 | K | Account | Email, marketing consent, delete data |
| G-023 | `/t/:slug/:tableCode/pay/overpay` | Overpay toggle | **DEFERRED** | L | — | **Do not implement** |

### 1.4 Guest global / error

| ID | Route | Screen name | MVP | Flow | Auth | Description |
|----|-------|-------------|-----|------|------|-------------|
| G-ERR | `/error` | Generic error | **MVP** | * | G | API down, retry |
| G-LEGAL | `/privacy`, `/terms` | Legal pages | **MVP** | * | Public | GDPR, processor role |

### Guest navigation shell

```
/t/:slug/:tableCode
├── /menu → /menu/:categoryId
├── /signal → /signal/sent
└── /pay (only if payment session exists OR show join)
    ├── /join
    ├── /lobby
    ├── /bill
    ├── /my-share
    ├── /shared/:lineId
    ├── /split/equal | /split/custom
    ├── /checkout → Mollie
    ├── /result/:paymentId
    ├── /remaining
    └── /closed
```

---

## 2. Staff Panel Routes (`/staff/*`)

Mobile-first; requires staff JWT (`WAITER` | `MANAGER` | `ADMIN`).

| ID | Route | Screen name | MVP | Flow | Min role | Description |
|----|-------|-------------|-----|------|----------|-------------|
| S-001 | `/staff/login` | Staff login | **MVP** | O | — | Email/password; venue picker if multi-venue V1.1 |
| S-002 | `/staff` | Shift dashboard | **MVP** | O | Waiter | Open tables, signals count, payment progress |
| S-003 | `/staff/signals` | Service signals queue | **MVP** | B, O | Waiter | List + ack |
| S-004 | `/staff/signals/:signalId` | Signal detail | **MVP** | B | Waiter | Table, time, message, ack button |
| S-005 | `/staff/floor` | Floor plan | **MVP** | C, O | Waiter | Color-coded tables |
| S-006 | `/staff/tables/:tableId` | Table detail | **MVP** | C, O | Waiter | Status, party size, action buttons |
| S-007 | `/staff/tables/:tableId/bill` | Bill editor | **MVP** | C, H, O | Waiter | Lines, shared flag, service charge |
| S-008 | `/staff/tables/:tableId/payment` | Payment monitor | **MVP** | C, D, J, O | Waiter | Token/PIN display, refresh, remaining, paid list |
| S-009 | `/staff/tables/:tableId/payment/participants` | Participant list | **MVP** | D, J | Waiter | Who joined, paid, failed |
| S-010 | `/staff/tables/:tableId/claims` | Claim overrides | **MVP** | E, O | Shift lead | Reassign, release, freeze |
| S-011 | `/staff/tables/:tableId/claims/freeze` | Freeze claims modal | **MVP** | O | Shift lead | Pause guest edits |
| S-012 | `/staff/tables/:tableId/timeline` | Table audit timeline | **MVP** | O | Shift lead | Events: claims, payments, overrides |
| S-013 | `/staff/tables/:tableId/close` | Close table wizard | **MVP** | J, O | Waiter‡ | Confirm remaining €0 or force-close |
| S-014 | `/staff/tables/:tableId/external-payment` | Record external pay | **MVP** | O | Shift lead | Mollie outage cash/terminal |
| S-015 | `/staff/shift/summary` | Shift summary | **MVP** | O | Shift lead | Export CSV |
| S-016 | `/staff/profile` | Staff profile | **MVP** | O | Waiter | Name, change password |
| S-017 | `/staff/tables/:tableId/import` | Bill CSV import | **MVP** | O | Waiter | Manual import on open session |
| S-018 | `/staff/notifications` | Push inbox | V1.1 | B | Waiter | Signal push history |

‡ Waiter close when remaining €0; force-close shift lead+ only.

### Staff action modal routes (overlays)

| ID | Route pattern | Screen | MVP | Min role |
|----|---------------|--------|-----|----------|
| S-M01 | `modal://confirm-open-payment` | Open payment confirm | **MVP** | Waiter |
| S-M02 | `modal://manager-pin` | Manager PIN entry | **MVP** | Shift lead action |
| S-M03 | `modal://cancel-payment-session` | Cancel payment mode | **MVP** | Shift lead |
| S-M04 | `modal://force-close-table` | Force close + reason | **MVP** | Shift lead |

---

## 3. Restaurant Admin Routes (`/admin/*`)

Requires admin JWT (`ADMIN`; shift lead `MANAGER` has **no** default admin access).

| ID | Route | Screen name | MVP | Flow | Description |
|----|-------|-------------|-----|------|-------------|
| A-001 | `/admin/login` | Admin login | **MVP** | N | Email/password |
| A-002 | `/admin` | Admin dashboard | **MVP** | N | Sessions today, GMV, setup checklist |
| A-003 | `/admin/onboarding` | Onboarding hub | **MVP** | N | Step progress |
| A-004 | `/admin/onboarding/basics` | Venue basics | **MVP** | N | Name, address, KvK, VAT |
| A-005 | `/admin/onboarding/tables` | Tables setup | **MVP** | N | Count, codes |
| A-006 | `/admin/onboarding/menu` | Menu setup | **MVP** | N | Quick add during wizard |
| A-007 | `/admin/onboarding/staff` | Staff invites | **MVP** | N | Initial team |
| A-008 | `/admin/onboarding/payments` | Mollie connect | **MVP** | N | OAuth handoff |
| A-009 | `/admin/onboarding/review` | Review & publish | **MVP** | N | Go-live checklist |
| A-010 | `/admin/tables` | Tables list | **MVP** | N | CRUD tables |
| A-011 | `/admin/tables/:tableId` | Table edit | **MVP** | N | Code, label, QR preview |
| A-012 | `/admin/tables/export` | QR batch export | **MVP** | N | PDF stickers |
| A-013 | `/admin/menu` | Menu manager | **MVP** | N, O | Categories + items |
| A-014 | `/admin/menu/import` | Menu CSV import | **MVP** | N | Validation report |
| A-015 | `/admin/menu/:itemId` | Menu item edit | **MVP** | N | Price, VAT, allergens |
| A-016 | `/admin/staff` | Staff list | **MVP** | N | Roles, status |
| A-017 | `/admin/staff/invite` | Invite staff | **MVP** | N | Email + role |
| A-018 | `/admin/staff/:staffId` | Staff edit | **MVP** | N | Role change, deactivate |
| A-019 | `/admin/payments` | Payments settings | **MVP** | N | Mollie status, test/live |
| A-020 | `/admin/settings` | Venue settings | **MVP** | O | Service charge, tips, hours |
| A-021 | `/admin/settings/tips` | Tip policy | **MVP** | I | pass_through vs retained |
| A-022 | `/admin/reports` | Reports hub | **MVP** | O | Daily/weekly summaries |
| A-023 | `/admin/reports/tips` | Tip export CSV | **MVP** | I | Staff pool export |
| A-024 | `/admin/audit` | Venue audit log | **MVP** | O | Filtered audit |
| A-025 | `/admin/refunds` | Refunds list | **MVP** | J | Initiate + status |
| A-026 | `/admin/refunds/new` | New refund | **MVP** | J | Amount, reason, payment pick |
| A-027 | `/admin/test-mode` | Test mode sandbox | **MVP** | N | Simulate bill/pay |
| A-028 | `/admin/loyalty` | Loyalty rules | V2 | K | Venue stamp config |
| A-029 | `/admin/integrations/pos` | POS settings | V1.1 | — | Read-only import |
| A-030 | `/admin/branding` | Branding | V1.1 | — | Logo, colors |

---

## 4. Platform Ops Routes (`/ops/*`)

Requires ops SSO (`PLATFORM_OPS`). Hosted at `ops.rekentafel.nl`.

### 4.1 MVP-required screens (acceptance criteria)

| ID | Route | Screen name | MVP | Flow | Description |
|----|-------|-------------|-----|------|-------------|
| O-001 | `/ops/login` | Ops SSO login | **MVP** | — | Google Workspace + MFA |
| O-002 | `/ops` | Ops home | **MVP** | — | Incidents, queue depths, pilot KPIs |
| O-005 | `/ops/audit` | **Global audit log** | **MVP** | J, O | Cross-tenant filter, export CSV |
| O-006 | `/ops/webhooks` | **Webhook reconciliation** | **MVP** | J | Ingestion stats, mismatch list |
| O-007 | `/ops/webhooks/:eventId` | Webhook event detail | **MVP** | J | Payload, processing status, replay |
| O-008 | `/ops/webhooks/dlq` | Dead letter queue | **MVP** | J | Failed jobs, retry/discard |
| O-009 | `/ops/reconciliation` | Reconciliation jobs | **MVP** | J | Daily job status, manual run |
| O-010 | `/ops/payments/:intentId` | Payment intent trace | **MVP** | J | End-to-end debugger |

### 4.2 Additional ops screens (MVP)

| ID | Route | Screen name | MVP | Flow | Description |
|----|-------|-------------|-----|------|-------------|
| O-003 | `/ops/restaurants` | Restaurant directory | **MVP** | N | All tenants |
| O-004 | `/ops/restaurants/:id` | Restaurant detail | **MVP** | N | Suspend, flags, contacts |
| O-011 | `/ops/restaurants/:id/flags` | Feature flags | **MVP** | N | `live`, test mode |
| O-012 | `/ops/chargebacks` | Chargeback queue | **MVP** | J | Manual dispute handling |
| O-013 | `/ops/chargebacks/:caseId` | Chargeback detail | **MVP** | J | Claim snapshot, notes |
| O-014 | `/ops/impersonate` | Impersonation launcher | **MVP** | — | Read-only view-as |
| O-015 | `/ops/impersonate/session/:id` | Impersonation session | **MVP** | — | Time-boxed read |
| O-016 | `/ops/health` | System health | **MVP** | — | API, queue, Mollie status |
| O-017 | `/ops/incidents` | Incident log | **MVP** | — | Ops notes |
| O-018 | `/ops/restaurants/new` | Create tenant | **MVP** | N | White-glove onboarding |

### Ops webhook reconciliation view — column spec

| Column | Source | Example |
|--------|--------|---------|
| `received_at` | `webhook_events` | 2026-06-26 21:14:03 |
| `mollie_tr_id` | webhook | `tr_abc123` |
| `restaurant` | `payment_intents` join | De Gouden Schaar |
| `table` | session join | T12 |
| `mollie_status` | GET /v2/payments | `paid` |
| `internal_status` | `payment_intents.status` | `open` |
| `amount_cents` | both | 2024 |
| `match` | computed | ✗ STATUS |
| `actions` | UI | Replay · Force sync · Trace |

### Ops audit log view — filter spec

| Filter | Type | Example |
|--------|------|---------|
| `restaurant_id` | UUID | `550e8400-...` |
| `table_id` | UUID | optional |
| `event_type` | enum multi | `claim.admin_override` |
| `actor_type` | enum | guest, waiter, system, mollie |
| `time_range` | datetime | last 24h |
| `severity` | enum | info, warn, critical |

---

## 5. Partner Dashboard Routes (`/partners/*`) — POST-MVP PLACEHOLDER

> **Not shipped in MVP pilot.** Listed for route reservation and V2 planning (Flow M).

| ID | Route | Screen name | Phase | Flow | Description |
|----|-------|-------------|-------|------|-------------|
| P-001 | `/partners/login` | Partner login | V2 | M | Partner SSO |
| P-002 | `/partners` | Partner home | V2 | M | Redemption KPIs |
| P-003 | `/partners/vouchers` | Voucher catalog | V2 | M | SKU list |
| P-004 | `/partners/vouchers/new` | Create voucher | V2 | M | Discount rules |
| P-005 | `/partners/vouchers/:id` | Edit voucher | V2 | M | |
| P-006 | `/partners/redemptions` | Redemption ledger | V2 | M | Pseudonymized guest refs |
| P-007 | `/partners/settlements` | Settlement reports | V2 | M | Monthly liability |
| P-008 | `/partners/fraud` | Fraud review | V2+ | M | Anomaly queue |
| P-009 | `/partners/developers` | API keys | V2+ | M | Webhook endpoints |
| P-010 | `/partners/settings` | Org settings | V2 | M | Billing contact |

**Guest redemption entry (future, not MVP):**

| ID | Route | Screen | Phase |
|----|-------|--------|-------|
| G-024 | `/account/rewards` | Rewards catalog | V2 |
| G-025 | `/account/rewards/redeem/:voucherId` | Redeem confirm | V2 |

---

## 6. API Routes Referenced by Screens (companion)

Guest/staff screens call REST/WebSocket endpoints — not product routes but listed for dev contract alignment.

| Method | API route | Screens | MVP |
|--------|-----------|---------|-----|
| GET | `/api/v1/tables/resolve/:slug/:tableCode` | G-001 | Yes |
| POST | `/api/v1/tables/:id/service-signals` | G-004 | Yes |
| POST | `/api/v1/payment-sessions/join` | G-006 | Yes |
| GET | `/api/v1/payment-sessions/:id/lobby` | G-007 | Yes |
| GET | `/api/v1/bills/:id` | G-008 | Yes |
| POST | `/api/v1/claims` | G-008 | Yes |
| POST | `/api/v1/splits/equal` | G-012 | Yes |
| POST | `/api/v1/checkout` | G-015 | Yes |
| GET | `/api/v1/staff/floor` | S-005 | Yes |
| POST | `/api/v1/staff/tables/:id/payment-session/open` | S-008 | Yes |
| WS | `/ws/staff/:venueId` | S-002, S-003 | Yes |
| WS | `/ws/payment-sessions/:id` | G-007–G-018 | Yes |
| GET | `/api/v1/ops/audit` | O-005 | Yes |
| POST | `/api/v1/ops/webhooks/:id/replay` | O-007 | Yes |

---

## 7. Screen Count Summary

| Surface | MVP screens | Post-MVP screens | Total defined |
|---------|-------------|------------------|---------------|
| Guest web | 22 | 4 | 26 |
| Staff panel | 18 | 1 | 19 |
| Restaurant admin | 27 | 3 | 30 |
| Platform ops | 18 | 0 | 18 |
| Partner (deferred) | 0 | 10 | 10 |
| **Total** | **85** | **18** | **103** |

---

## 8. Route Guard Matrix

| Route prefix | Unauthenticated | Guest session | Staff | Admin | Ops |
|--------------|-----------------|---------------|-------|-------|-----|
| `/t/*` menu/signal | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/t/*/pay/*` | join only | join+token | — | — | — |
| `/staff/*` | login only | ✗ | ✓ | ✓ | ✗ |
| `/admin/*` | login only | ✗ | ✗ | ✓ | ✗ |
| `/ops/*` | login only | ✗ | ✗ | ✗ | ✓ |
| `/partners/*` | — | — | — | — | — (V2) |

---

## 9. Example Session — Screen Sequence (Table 12, €105.60)

| Step | Actor | Screen ID | Route |
|------|-------|-----------|-------|
| 1 | Guest A | G-001 | `/t/de-gouden-schaar/12` |
| 2 | Guest A | G-004 | `.../signal` → ready to order |
| 3 | Waiter | S-003 | `/staff/signals` → ack |
| 4 | Waiter | S-006 | `/staff/tables/{uuid}` → start session |
| 5 | Waiter | S-007 | `.../bill` → enter lines |
| 6 | Waiter | S-008 | `.../payment` → open payment, PIN `482913` |
| 7 | Guest B | G-006 | `.../pay/join` → enter PIN |
| 8 | Guest B | G-008 | `.../pay/bill` → claim steak |
| 9 | Guest A | G-012 | `.../pay/split/equal` → split remainder |
| 10 | Guest A | G-015 | `.../pay/checkout` → tip 10% |
| 11 | Guest A | G-017 | `.../pay/result/tr_xxx` → success |
| 12 | Guest A | G-018 | `.../pay/remaining` → €42.10 left |
| 13 | Waiter | S-008 | `.../payment` → monitor |
| 14 | Waiter | S-013 | `.../close` → remaining €0 |
| 15 | Ops (if webhook lag) | O-006 | `/ops/webhooks` → replay |
| 16 | All guests | G-011 | `.../pay/closed` |

---

## 10. Screen Inventory Risks

| ID | Risk | Screens | Mitigation |
|----|------|---------|------------|
| SI-1 | Guest deep-links to `/pay/bill` without token | G-008 | Server redirect G-006; never render bill |
| SI-2 | Staff routes on small phone cluttered | S-002 | Bottom nav; max 4 tabs |
| SI-3 | Admin onboarding skipped steps | A-003 | Hard checklist gates on A-009 |
| SI-4 | Ops replay double-charges | O-007 | Idempotent replay button + confirm |
| SI-5 | Partner routes accidentally deployed | P-* | Feature flag `partners.enabled=false` |

---

## Related Artifacts

- [surface-map.md](./surface-map.md)
- [rbac-matrix.md](./rbac-matrix.md)
- [../flows/flows-a-o.md](../flows/flows-a-o.md)
- [../architecture/payments/webhook-reconciliation.md](../architecture/payments/webhook-reconciliation.md)

---

*Slice ownership: Part 3 — Screen Inventory. Files owned exclusively by this slice: `docs/surfaces/*`.*
