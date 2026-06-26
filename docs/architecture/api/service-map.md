# PART 10 — API Service Map

**Product (working name):** Rekentafel / TabSettle  
**Slice:** API Surface, Services, and Background Jobs  
**Version:** 1.0  
**Stack:** TypeScript (Node.js), PostgreSQL, Redis, BullMQ workers  
**Cross-references:** [rules-spec.md](../../domain/split-engine/rules-spec.md), [state-machines.md](../../domain/split-engine/state-machines.md), [event-catalog.md](../../flows/event-catalog.md), [payment-architecture.md](../payments/payment-architecture.md)

---

## 1. Executive summary

The backend is a **modular monolith** (single deployable API + worker processes) with domain-bounded service modules. External boundaries:

| Surface | Protocol | Auth |
|---------|----------|------|
| Guest web | REST + SSE | Ephemeral guest token |
| Staff web | REST + WebSocket | JWT (staff RBAC) |
| Restaurant admin | REST | JWT (admin RBAC) |
| Platform ops | REST | JWT (platform RBAC) |
| Mollie | Webhook POST | Signature + async verify |

**MVP excludes:** GraphQL, tRPC, gRPC between services, crypto endpoints, public partner API.

---

## 2. API style recommendation

### 2.1 Decision: REST + OpenAPI (MVP)

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **REST + OpenAPI 3.1** | **MVP default** | Webhook-friendly; contract-first parallel dev; guest mobile web needs simple fetch; Mollie integration is HTTP-native; ops tooling (Postman, codegen) mature |
| tRPC | Defer | Strong TS end-to-end typing but poor fit for Mollie webhooks, third-party POS (V1.1), and non-TS clients; couples guest + staff to same TS package |
| GraphQL | Defer | Bill/claim/payment graphs are write-heavy with strict concurrency — mutations need idempotency headers, not GraphQL conventions; N+1 and cache invalidation add complexity for real-time split UI |
| gRPC internal | Post-MVP | Only if monolith splits into separate services at 25+ venues |

### 2.2 REST conventions

| Convention | Rule |
|------------|------|
| Base URL | `https://api.rekentafel.nl/v1` |
| Resource IDs | UUID v7 in paths; opaque slugs for public QR (`/t/{restaurant_slug}/{table_code}`) |
| Money | Integer cents in JSON (`amount_cents`); never floats |
| Timestamps | ISO-8601 UTC |
| Errors | RFC 7807 `application/problem+json` |
| Pagination | Cursor-based: `?cursor=&limit=` |
| Real-time | SSE for guest bill sync (MVP); WebSocket for staff queue (MVP) |
| Versioning | URL prefix `/v1`; breaking changes → `/v2` |

### 2.3 Why not tRPC for internal-only?

Even staff + guest sharing a TS monorepo, **external ingress is webhook-first**. OpenAPI generates:
- Zod validators (via `@anatine/zod-openapi` or similar)
- Guest client (optional React Query hooks)
- Staff client
- Contract tests for parallel Cursor instances

tRPC can be evaluated V1.1 **inside** staff dashboard only if team velocity justifies dual contract maintenance — not recommended for MVP.

---

## 3. Service module map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Gateway (Fastify)                           │
│  rate-limit │ CORS │ request-id │ auth middleware │ idempotency        │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬───────────┘
       │          │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Session  │ │ Bill     │ │ Claim    │ │ Payment  │ │ Auth     │ │ Webhook  │
│ Service  │ │ Service  │ │ Service  │ │ Service  │ │ Service  │ │ Ingress  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Token    │ │ Split    │ │ Ledger   │ │ Mollie   │ │ Notifi-  │ │ Recon-   │
│ Service  │ │ Engine   │ │ Service  │ │ Adapter  │ │ cation   │ │ ciliation│
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
       │            │            │            │
       └────────────┴────────────┴────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ PostgreSQL + Redis │
                    │ Outbox → Workers   │
                    └───────────────────┘
```

---

## 4. Module boundaries

### 4.1 Session Service

**Owns:** `TableSessionState`, `DiningSession`, `PaymentSession`, table lifecycle.

| Responsibility | In scope | Out of scope |
|----------------|----------|--------------|
| Table state machine | `EMPTY → SEATED → PAYMENT_ACTIVE → CLOSED` | Bill line math |
| Dining session CRUD | Start, cancel, party size | Menu content |
| Payment session open/close | Issue token, TTL, refresh, revoke | Mollie calls |
| Table reset | Post-close purge triggers | GDPR job execution |
| Guest join roster | `participant_id` registration | Claim allocation |

**Key entities:** `restaurant_id`, `table_id`, `dining_session_id`, `payment_session_id`, `participant_id`, `TableSessionState`.

**Public endpoints:** See OpenAPI — `/tables/{id}/dining-sessions`, `/payment-sessions/*`, `/t/{slug}/{code}`.

**Events emitted:** `dining_session.*`, `payment_session.*`, `table.closed`, `table.reset`.

**Dependencies:** Auth (staff), Token Service, Bill Service (on payment activate).

---

### 4.2 Token Service

**Owns:** `PaymentSessionToken` lifecycle, `join_pin` generation.

| Field | Storage |
|-------|---------|
| Raw token | Never persisted — returned once to staff UI |
| `token_hash` | SHA-256 in DB |
| `join_pin` | 6-digit numeric, bcrypt hash |
| `expires_at`, `revoked_at` | Timestamps |

**States:** `ISSUED → EXPIRED → REVOKED` (see [state-machines.md](../../domain/split-engine/state-machines.md)).

**Security:** Token in URL fragment `#ps=...` preferred over query string (referrer leakage). MVP accepts query param with short TTL.

**Dependencies:** Session Service only.

---

### 4.3 Bill Service

**Owns:** `Bill`, `BillLine`, `AllocatableUnit`, `TableBillSettlement` state, manual entry, CSV import.

| Responsibility | MVP | Post-MVP |
|----------------|-----|----------|
| Bill CRUD (staff) | Manual lines, VAT, service charge | POS import V1.1 |
| Bill lock on payment activate | `bill_version = 1` snapshot | — |
| Bill version bump | Waiter override invalidates unpaid allocations | POS sync V2 |
| Lock/unlock claims | `ALLOCATION_FROZEN` toggle | — |
| AllocatableUnit derivation | From BillLine qty / splittable flag | — |

**Key entities:** `bill_id`, `bill_version`, `BillLine`, `AllocatableUnit`, `TableBillSettlement`.

**Events:** `bill.created`, `bill.updated`, `bill.locked`, `bill.unlocked`, `bill.line.shared_flagged`.

**Dependencies:** Session Service (payment activate), Split Engine (recalc on edit).

---

### 4.4 Claim Service

**Owns:** `Claimant`, `Allocation`, `ClaimIntent`, claim CRUD, participant presence.

| Responsibility | Detail |
|----------------|--------|
| Guest join | Creates `Claimant` (= `participant_id` in event catalog) |
| Item claims | `SplitMode.ITEM` on `AllocatableUnit` |
| Shared claims | Fractional shares, sum ≤ 100% |
| Release / leave | Frees units to `UnclaimedPool` |
| Admin override | Manager reassign, clear (bypasses Redis guest locks) |

**Key entities:** `participant_id`, `Claimant`, `Allocation`, `AllocatableUnit`, `SplitMode`, `UnclaimedPool`.

**Claimant states:** `JOINED → ALLOCATING → CHECKOUT_LOCKED → PAYMENT_PENDING → PAID` (see state machines).

**Events:** `claim.*`, `payment_session.joined`.

**Dependencies:** Split Engine, Ledger Service, Redis locks, Bill Service (version check).

---

### 4.5 Split Engine (library module, not HTTP)

**Owns:** Pure calculation — equal split, custom pledge, service charge pro-rata, remainder cents.

| Input | Output |
|-------|--------|
| Bill snapshot + allocations | Per-claimant `amount_cents` breakdown |
| Equal split request | Batch `Allocation` rows with `equal_group_id` |
| Custom pledge | `CUSTOM_PLEDGE` ledger entry |
| Tip selection | Added to `CheckoutIntent` only |

**No HTTP surface.** Invoked by Claim Service and Payment Service.

**Cross-ref:** [rules-spec.md](../../domain/split-engine/rules-spec.md) §4–§6.

---

### 4.6 Ledger Service

**Owns:** `RemainingBalance`, `confirmed_paid_cents`, `remaining_cents`, `unclaimed_cents`, settlement aggregates.

| Metric | Formula |
|--------|---------|
| `remaining_cents` | `bill_grand_total_cents - confirmed_paid_cents` |
| `unclaimed_cents` | Grand total minus sum active allocation amounts |
| `outstanding_allocated` | Allocated but not yet paid |

**Single writer:** Webhook worker increments `confirmed_paid_cents`; Claim Service updates allocation sums.

**Events:** `ledger.balance.updated`, `payment_session.completed`.

**Invariants:** `confirmed_paid_cents ≤ bill_grand_total_cents` always.

---

### 4.7 Payment Service

**Owns:** `CheckoutIntent`, `PaymentRecord`, checkout initiation, return URL handler.

| Responsibility | MVP |
|----------------|-----|
| Compose checkout amount | food share + tip (service charge in share) |
| Create Mollie payment | Via Mollie Adapter |
| Return URL poll | One-shot status fetch (not source of truth) |
| External/cash record | Staff marks remainder paid off-platform |
| Refund initiation | Manager → Mollie Refunds API |

**Key entities:** `CheckoutIntent`, `PaymentRecord`, `mollie_payment_id`, `idempotency_key`.

**Payment intent states:** `CREATING → MOLLIE_OPEN → PAID | FAILED | CANCELED | EXPIRED`.

**Events:** `checkout.created`, `payment.mollie.*`, `tip.selected`.

**Dependencies:** Mollie Adapter, Ledger, Claim Service (checkout lock), Split Engine.

**Crypto:** All `/crypto/*` routes return `501 NOT_MVP`. No module loaded in MVP.

---

### 4.8 Mollie Adapter

**Owns:** OAuth token refresh, Mollie API client, payment/refund creation.

| Concern | MVP model |
|---------|-----------|
| Account | Restaurant-owned org + platform OAuth agent (Model A) |
| Token storage | Encrypted refresh token per `restaurant_id` |
| Scopes | `payments.write`, `payments.read`, `profiles.read` |
| Idempotency | Platform `idempotency_key` in metadata + local unique constraint |

**No business logic.** Thin HTTP wrapper with circuit breaker.

**Post-MVP:** Marketplace split routing (`routing[]`) behind feature flag `payments.model`.

---

### 4.9 Webhook Ingress

**Owns:** Mollie webhook receipt, signature validation, enqueue.

| Rule | Detail |
|------|--------|
| Response time | `200 OK` within 500ms |
| Processing | Async via BullMQ `webhook.process` job |
| Verification | Fetch `GET /v2/payments/{id}` before state transition |
| Idempotency | `processed_webhooks` table |

**Endpoint:** `POST /webhooks/mollie` (no auth header — Mollie IP allowlist + payment ID lookup).

**Events:** `payment.mollie.webhook.received`, `payment.mollie.webhook.paid`, etc.

---

### 4.10 Reconciliation Service

**Owns:** Payment intent ↔ Mollie status alignment, orphan detection, ops alerts.

| Job | Schedule |
|-----|----------|
| Stale open payments | Every 15 min — poll Mollie for `open` > 20 min |
| Daily settlement cross-check | 06:00 CET — compare ledger vs Mollie list API |
| Orphan payment flag | On webhook after table `CLOSED` |

**MVP:** Manual ops dashboard; no Settlements API automation.

---

### 4.11 Auth Service

**Owns:** Staff/admin JWT, guest ephemeral tokens, optional account linking, RBAC.

See [auth-and-sessions.md](./auth-and-sessions.md).

**Surfaces:**
- Staff: email + password or magic link (pilot)
- Guest: device cookie + payment session token
- Account (V1.1): email OTP merge to `user_id`

---

### 4.12 Notification Service

**Owns:** Staff WebSocket gateway, guest SSE, service signal delivery.

| Channel | MVP | Transport |
|---------|-----|-----------|
| Staff signals | Yes | WebSocket `/ws/staff` |
| Bill updates | Yes | SSE `/payment-sessions/{id}/events` |
| Email receipts | Optional pilot | Postmark/SendGrid |
| Push (PWA) | V1.1 | — |

**Events consumed:** `service_signal.*`, `claim.*`, `ledger.balance.updated`, `payment.mollie.webhook.*`.

---

### 4.13 Audit Service

**Owns:** Append-only `audit_events` table, correlation IDs.

| Captured | Retention |
|----------|-----------|
| All mutating API calls | 7 years (financial) |
| Staff overrides | Permanent until GDPR erasure request |
| Guest IP hash | 90 days |

**Fields:** `request_id`, `actor`, `restaurant_id`, `resource_type`, `resource_id`, `action`, `before`, `after`, `idempotency_key`.

Every service writes via shared `audit.log()` helper — no separate HTTP module.

---

### 4.14 Restaurant Admin Service

**Owns:** Venue config, tables, menu, staff invites, Mollie connect status.

**RBAC scope:** `restaurant_admin`, `manager`, `waiter` (see auth doc).

**Endpoints:** `/admin/restaurants/*`, `/admin/tables/*`, `/admin/menu/*`, `/admin/staff/*`.

---

### 4.15 Platform Ops Service (MVP minimal)

**Owns:** Pilot provisioning, webhook reconciliation dashboard, dispute queue status.

**RBAC:** `platform_ops` role only.

**Post-MVP:** Self-serve onboarding, feature flags per venue.

---

## 5. Inter-service call matrix

| Caller → callee | Sync (HTTP/internal) | Async (outbox/event) |
|-----------------|----------------------|----------------------|
| Session → Bill | Activate payment: lock bill | `payment_session.opened` |
| Session → Token | Issue token | `payment_session.token_issued` |
| Claim → Split Engine | Calculate amounts | — |
| Claim → Ledger | Read balances | `claim.created` |
| Payment → Mollie Adapter | Create payment | `checkout.created` |
| Webhook worker → Ledger | Increment paid | `payment.mollie.webhook.paid` |
| Webhook worker → Loyalty | — | `loyalty.accrued` (minimal MVP) |
| Bill → Notification | — | `bill.updated` |
| Any mutator → Audit | Sync write | — |

**Rule:** No circular sync calls. Payment webhook never calls Claim Service synchronously — updates ledger then emits event.

---

## 6. Data store ownership

| Store | Owner modules | Notes |
|-------|---------------|-------|
| `restaurants`, `tables` | Admin | Tenant root |
| `dining_sessions`, `payment_sessions` | Session | |
| `payment_session_tokens` | Token | Hash only |
| `bills`, `bill_lines`, `allocatable_units` | Bill | |
| `participants`, `allocations` | Claim | `participant_id` = Claimant |
| `checkout_intents`, `payment_records` | Payment | |
| `bill_settlements` | Ledger | Denormalized aggregates |
| `processed_webhooks`, `idempotency_keys` | Webhook / API middleware | |
| `audit_events` | Audit | Append-only |
| `outbox_events` | All producers | Postgres outbox pattern |

**Redis keys:** See [idempotency-concurrency.md](./idempotency-concurrency.md).

---

## 7. Deployment topology (MVP)

| Process | Count | Responsibility |
|---------|-------|----------------|
| `api` | 2+ (Fly.io/Render) | REST + SSE + WS |
| `worker` | 1+ | BullMQ consumers |
| `scheduler` | 1 | Cron triggers (singleton) |
| PostgreSQL | 1 primary | Source of truth |
| Redis | 1 | Locks, idempotency cache, BullMQ |

---

## 8. MVP vs post-MVP module gates

| Module / capability | MVP | V1.1 | V2 |
|---------------------|-----|------|-----|
| REST `/v1` | ✓ | — | — |
| Guest SSE | ✓ | — | — |
| Staff WebSocket | ✓ | — | — |
| Account linking API | Minimal (link after pay) | Full accounts | — |
| Loyalty accrual worker | Points preview only | Full | Coalition |
| POS import adapter | — | CSV/read-only | Bi-directional |
| Crypto adapter module | **501 stub** | — | Licensed partner |
| GraphQL / tRPC | — | Evaluate | — |
| Public partner API | — | — | OAuth2 partners |

---

## 9. Risks specific to this slice

| Risk | Severity | Mitigation |
|------|----------|------------|
| Monolith module boundary erosion | Medium | Enforce import lint rules per module folder |
| OpenAPI drift from implementation | High | CI contract test; codegen from YAML |
| Webhook + API race on same payment | High | Ledger single-writer; idempotency keys |
| Guest token leakage via referrer | Medium | Fragment URL; short TTL; no bill in SSR HTML |
| Staff JWT in localStorage XSS | Medium | HttpOnly cookie option; CSP strict |
| SSE reconnect storm after partial pay | Low | Last-Event-ID cursor; debounce |
| Parallel Cursor instances editing same OpenAPI | Medium | This slice owns `docs/architecture/api/*` exclusively |

---

## 10. Folder ownership (parallel dev)

| Path | Owner slice |
|------|-------------|
| `docs/architecture/api/*` | **Part 10 (this slice)** |
| `docs/domain/split-engine/*` | Part 5 |
| `docs/architecture/payments/*` | Part 6 |
| `docs/flows/*` | Part 2 |
| `apps/api/src/modules/session/*` | Backend session squad |
| `apps/api/src/modules/claim/*` | Backend claim squad |

---

## 11. Entity dictionary cross-reference

Canonical names used across API schemas (must match exactly):

| Entity | API type name | Primary key | Notes |
|--------|---------------|-------------|-------|
| Restaurant | `Restaurant` | `restaurant_id` | Tenant |
| Table | `Table` | `table_id` | Persistent QR |
| DiningSession | `DiningSession` | `dining_session_id` | Waiter-started |
| PaymentSession | `PaymentSession` | `payment_session_id` | Short-lived pay context |
| PaymentSessionToken | *(not exposed raw)* | `token_id` | Hash stored server-side |
| Participant / Claimant | `Participant` | `participant_id` | Guest in payment session |
| GuestDevice | *(cookie only)* | `guest_device_id` | Anonymous |
| Bill | `Bill` | `bill_id` | |
| BillLine | `BillLine` | `line_id` | |
| AllocatableUnit | `AllocatableUnit` | `unit_id` | |
| Allocation | `Allocation` | `allocation_id` | |
| CheckoutIntent | `CheckoutIntent` | `checkout_id` | |
| PaymentRecord | `Payment` | `payment_id` | Maps to Mollie `tr_*` |
| BillSettlement | `BillSettlement` | `bill_id` | Aggregate state |
| ServiceSignal | `ServiceSignal` | `signal_id` | Call server |

---

*Slice ownership: Part 10 — API / Backend Design.*
