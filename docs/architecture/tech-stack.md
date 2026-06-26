# PART 16 — Recommended Tech Stack Decision Record

**Product (working name):** Rekentafel / TabSettle  
**Slice:** Part 16 — Recommended Tech Stack  
**Version:** 1.0  
**Default posture:** TypeScript-first monorepo, Netherlands-first EU hosting, web-first surfaces  
**Cross-references:** [service-map.md](./api/service-map.md), [auth-and-sessions.md](./api/auth-and-sessions.md), [payment-architecture.md](./payments/payment-architecture.md), [crypto-rail-design.md](./payments/crypto-rail-design.md), [surface-map.md](../surfaces/surface-map.md), [idempotency-concurrency.md](./api/idempotency-concurrency.md)

---

## 1. Executive summary

| Layer | MVP decision | Primary rationale |
|-------|--------------|-------------------|
| Monorepo | **pnpm workspaces + Turborepo** | Four parallel Cursor workstreams; shared types without publish cycles |
| Guest / staff / admin UI | **React 19 + Vite 6 + TypeScript 5.6** | One skill pool; mobile-first PWA; no native apps in MVP |
| API | **Node.js 22 LTS + Fastify 5** | Webhook latency, SSE/WS on same process, mature Mollie HTTP integration |
| Database | **PostgreSQL 16 (Neon or Fly Postgres)** | ACID for allocations; row locks; outbox pattern |
| Cache / locks | **Redis 7 (Upstash or Fly Redis)** | Claim locks, idempotency cache, BullMQ backend |
| Realtime | **SSE (guest) + WebSocket (staff)** | Guest one-way bill sync; staff bidirectional signals |
| Auth | **jose JWT + HttpOnly cookies** | Ephemeral guest tokens; staff RBAC; no session store MVP |
| Payments | **Mollie Node SDK + webhook workers** | NL iDEAL; restaurant-owned org model |
| Crypto | **Stub module (`501 NOT_MVP`)** | Separate rail post-MVP; never commingle with Mollie |
| Cloud | **Fly.io (ams primary region)** | EU residency; SSE/WS sticky sessions; low ops for 4-person team |
| Observability | **OpenTelemetry → Grafana Cloud (EU)** | Logs, metrics, traces; payment correlation |
| Testing | **Vitest + Testcontainers + Playwright** | Fast unit; real Postgres integration; guest pay e2e |

**Weak assumption challenged:** A single realtime transport (WebSocket everywhere) adds reconnect complexity on guest mobile Safari and duplicates server fan-out. **SSE for guest bill sync** (server → client only) plus **WebSocket for staff** matches traffic patterns and reduces battery drain.

---

## 2. Monorepo layout (4-workstream compatible)

Four Cursor instances map to **disjoint folder ownership** — no two slices edit the same path in the same sprint.

```
rekentafel/
├── apps/
│   ├── api/                 # Workstream A — backend + workers
│   ├── guest-web/           # Workstream B — guest PWA
│   ├── staff-web/           # Workstream C — floor console
│   └── admin-web/           # Workstream D — restaurant admin + ops (MVP minimal)
├── packages/
│   ├── api-contract/        # Workstream A owns; OpenAPI → Zod + types
│   ├── rbac/                # Workstream D owns; shared permission constants
│   ├── ui/                  # Workstream B/C share; design tokens + primitives
│   ├── split-engine/        # Workstream A owns; pure TS bill math (no I/O)
│   └── config/              # Shared ESLint, TSConfig, Tailwind preset
├── docs/architecture/       # Blueprint slices (this doc)
├── infra/                   # Workstream A — Fly.toml, Docker, CI
└── e2e/                     # Workstream B owns Playwright guest flows
```

| Workstream | Owns | Must not edit (merge via PR) |
|------------|------|------------------------------|
| **A — Backend** | `apps/api/**`, `packages/split-engine/**`, `packages/api-contract/**`, `infra/**` | `apps/*-web/**` |
| **B — Guest web** | `apps/guest-web/**`, `e2e/guest/**`, `packages/ui/**` (guest components) | `apps/api/src/modules/**` |
| **C — Staff web** | `apps/staff-web/**`, `e2e/staff/**` | Admin routes, payment modules |
| **D — Admin / platform** | `apps/admin-web/**`, `packages/rbac/**`, `e2e/admin/**` | Claim engine, webhook workers |

**Package manager:** pnpm 9 (`pnpm-workspace.yaml`). **Task runner:** Turborepo (`turbo.json`) with `build`, `test`, `lint`, `typecheck` pipelines.  
**Branching:** `main` protected; feature branches `ws/{a|b|c|d}/{ticket}-{slug}`; OpenAPI changes require Workstream A review.

**Contract-first rule:** `packages/api-contract/openapi.yaml` is the single REST source of truth. Frontend workstreams consume generated clients only — no hand-written fetch URLs in apps.

---

## 3. Frontend stack

### 3.1 Decision matrix

| Surface | Framework | Router | State / data | Styling | Realtime |
|---------|-----------|--------|--------------|---------|----------|
| Guest web (`app.rekentafel.nl`) | React 19 + Vite 6 | TanStack Router | TanStack Query v5 + URL state | Tailwind CSS 4 + `@rekentafel/ui` | **SSE** on payment session |
| Staff web (`/staff`) | React 19 + Vite 6 | TanStack Router | TanStack Query + Zustand (floor UI) | Tailwind + touch-first components | **WebSocket** |
| Admin web (`/admin`) | React 19 + Vite 6 | TanStack Router | TanStack Query | Tailwind | Poll 30s (config screens) |
| Ops (`ops.rekentafel.nl`) | Same as admin (route split) | — | — | — | Poll + alert banner |

**Rejected for MVP:**

| Alternative | Verdict | Why |
|-------------|---------|-----|
| Next.js App Router | Defer | SSR not needed for token-gated bill views; increases edge complexity for SSE |
| Vue / Svelte | No | Team TS/React depth; four parallel devs need one UI paradigm |
| React Native | **Do not build** | Master prompt excludes native apps; PWA sufficient for pilot |
| tRPC client | No | OpenAPI contract is webhook-first boundary (see service-map §2.3) |

### 3.2 Guest web specifics

| Concern | Choice | Detail |
|---------|--------|--------|
| PWA | `vite-plugin-pwa` | Add-to-home-screen for return visits; **no push in MVP** |
| Money display | `Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' })` | Display only; API uses integer cents |
| Payment redirect | Mollie hosted checkout | Full redirect; return URL polls once then SSE takes over |
| Token in URL | Hash fragment `#ps=...` preferred | Avoids referrer leakage to analytics (see auth doc) |
| i18n | Dutch default, English fallback | `react-i18next`; MVP copy NL-only in production |
| Accessibility | WCAG 2.1 AA target | Focus on claim list, checkout CTA, error states |

### 3.3 Staff web specifics

| Concern | Choice | Detail |
|---------|--------|--------|
| Target device | iPad 10.2" + iPhone (manager) | Min tap target 44px; high-contrast floor mode |
| Offline | **Not supported MVP** | Show banner; queue not implemented |
| Manager PIN | Modal step-up | 15-minute device cache per auth doc |
| WebSocket library | Native `WebSocket` + reconnect backoff | Auth via `?token=` on connect; heartbeats 30s |

### 3.4 Shared UI package (`packages/ui`)

| Export | Purpose |
|--------|---------|
| `Money`, `VatLine`, `TipSelector` | Consistent EUR + BTW display |
| `BillLineRow`, `ClaimChip` | Guest + staff shared bill rendering |
| `Button`, `Input`, `Toast` | Design system primitives |
| Tokens | CSS variables — restaurant white-label post-MVP |

**Build:** `tsup` for dual ESM/CJS; consumed as workspace dependency `"@rekentafel/ui": "workspace:*"`.

---

## 4. Backend stack

### 4.1 Runtime and framework

| Component | Choice | Version pin (MVP) |
|-----------|--------|-------------------|
| Runtime | Node.js | 22 LTS |
| HTTP framework | Fastify | 5.x |
| Validation | Zod (from OpenAPI codegen + hand Refines) | 3.x |
| ORM | **Drizzle ORM** | 0.3x |
| Migrations | `drizzle-kit` | SQL migrations in repo |
| Job queue | **BullMQ** | 5.x on Redis |
| Scheduler | BullMQ repeatable jobs + single `scheduler` process | Singleton on Fly |
| HTTP client | `undici` (Node built-in) | Mollie API calls |

**Why Drizzle over Prisma:** Financial modules need explicit `SELECT FOR UPDATE`, partial indexes, and constraint-first migrations visible in SQL diffs — Drizzle keeps SQL auditable for counsel and ops.

**Why Fastify over NestJS:** Lower cold-start and memory for SSE/WS co-located with REST; fewer decorators for a 4-person team; service-map already assumes Fastify gateway.

### 4.2 Modular monolith structure (`apps/api`)

```
apps/api/src/
├── modules/
│   ├── session/       # Table + payment session lifecycle
│   ├── token/         # Payment session join secrets
│   ├── bill/          # Bill lines, VAT, service charge
│   ├── claim/         # Allocations, concurrent claims
│   ├── payment/       # Checkout intents, Mollie orchestration
│   ├── mollie/        # OAuth + API adapter (thin)
│   ├── webhook/       # Ingress + enqueue
│   ├── ledger/        # Remaining balance aggregates
│   ├── auth/          # Staff + guest JWT
│   ├── notification/  # SSE + WebSocket gateway
│   ├── admin/         # Restaurant config
│   ├── audit/         # Append-only audit helper
│   └── crypto/        # POST-MVP stub only
├── workers/           # BullMQ consumers
├── plugins/           # Fastify plugins (auth, idempotency, otel)
└── index.ts           # API + WS + SSE route registration
```

**Import lint:** ESLint `no-restricted-imports` — modules may not import sibling module internals; only public `index.ts` exports.

### 4.3 API style

| Aspect | Decision |
|--------|----------|
| Style | REST + OpenAPI 3.1 |
| Base URL | `https://api.rekentafel.nl/v1` |
| Errors | RFC 7807 `application/problem+json` |
| Idempotency | `Idempotency-Key` header on all allocation/payment mutations |
| Versioning | URL prefix `/v1` |

Full endpoint ownership: [service-map.md](./api/service-map.md).

---

## 5. Data layer

### 5.1 PostgreSQL

| Aspect | MVP | Post-MVP |
|--------|-----|----------|
| Provider | Neon Serverless Postgres **or** Fly Postgres | Dedicated primary + read replica at 25+ venues |
| Region | `eu-central-1` equivalent (Frankfurt / Amsterdam path) | Same |
| Extensions | `pgcrypto`, `uuid-ossp` (or app-generated UUID v7) | `pg_partman` for audit partitioning |
| Connection | PgBouncer transaction mode via provider pooler | — |
| Backups | Daily PITR, 35-day retention | Cross-region backup V2 |

**Schema ownership:** Single migration chain in `apps/api/drizzle/`. Workstream A exclusively merges migrations.

**Critical constraints (application-enforced + DB):**

```sql
-- Example: no double-allocation on unit
CREATE UNIQUE INDEX uq_allocation_active_unit
  ON allocations (unit_id)
  WHERE status IN ('ACTIVE', 'CHECKOUT_LOCKED') AND split_mode = 'ITEM';
```

### 5.2 Redis

| Use | Key pattern | TTL | Degrade behavior |
|-----|-------------|-----|------------------|
| Claim lock | `lock:unit:{unit_id}` | 5s | Fall back to Postgres row lock |
| Idempotency cache | `idempotency:{endpoint}:{key}` | 24h | Postgres `idempotency_keys` table |
| Rate limit | `rl:{scope}:{id}` | sliding window | In-memory per instance (pilot only) |
| BullMQ | Bull internal prefixes | — | Jobs stall; alert ops |
| SSE cursor | `sse:ps:{payment_session_id}:seq` | 2h | Client full refetch on reconnect |

**Provider:** Upstash Redis (EU) for MVP **or** Fly Redis co-located in `ams`. Prefer co-located Redis when SSE fan-out exceeds 500 concurrent connections per venue night (unlikely in pilot).

### 5.3 Object storage (minimal MVP)

| Asset | Store | MVP |
|-------|-------|-----|
| Menu images | Cloudflare R2 (EU) or S3 `eu-central-1` | Optional — text menu OK for pilot |
| CSV bill import | Presigned upload → temp bucket | 24h lifecycle delete |
| Audit exports | Encrypted S3/R2 | Manager-triggered |

---

## 6. Realtime architecture (collaborative claiming)

### 6.1 Transport decision

| Transport | Used for | Rationale |
|-----------|----------|-----------|
| **Server-Sent Events (SSE)** | Guest payment session bill/claim/balance updates | One-way server push; auto-reconnect with `Last-Event-ID`; works through many mobile proxies; lower battery than WS |
| **WebSocket** | Staff service signals, table list, payment mode alerts | Bidirectional; low latency for floor staff |
| HTTP poll | Admin config, post-checkout receipt status | 30s acceptable |
| **Not used MVP** | Guest WebSocket | Unnecessary duplex; reconnect storms on tab backgrounding |

### 6.2 Guest SSE contract

**Endpoint:** `GET /v1/payment-sessions/{id}/events`  
**Auth:** `payment_participant` JWT (or guest JWT + participant header)  
**Headers:** `Accept: text/event-stream`, optional `Last-Event-ID`

**Event types:**

| Event | Payload fields | Trigger example |
|-------|----------------|-----------------|
| `bill.snapshot` | `bill_version`, `lines[]`, `grand_total_cents` | Waiter edits bill |
| `claim.updated` | `unit_id`, `participant_id`, `amount_cents` | Anna claims €14.50 beer |
| `claim.conflict` | `unit_id`, `reason` | Boris lost race on same unit |
| `ledger.balance` | `remaining_cents`, `confirmed_paid_cents` | Partial pay |
| `participant.joined` | `display_name`, `count` | 3rd guest joins |
| `session.closed` | `reason` | Waiter force-close |

**Numeric example — concurrent claim race:**

| Time | Anna | Boris | Server |
|------|------|-------|--------|
| T+0ms | `POST /claims` unit U1 | — | Redis lock U1 → OK |
| T+15ms | — | `POST /claims` unit U1 | Lock held → 409 `UNIT_ALREADY_CLAIMED` |
| T+20ms | 201 Created | — | SSE `claim.updated` to all participants |
| T+25ms | — | Receives SSE + toast | Boris UI refreshes unit list |

**Reconnect:** Client sends `Last-Event-ID: {seq}`. Server replays from Redis stream buffer (last 200 events per payment session) or returns full `bill.snapshot` if cursor expired.

### 6.3 Staff WebSocket contract

**Endpoint:** `wss://api.rekentafel.nl/v1/ws/staff?restaurant_id={uuid}`  
**Auth:** Staff JWT in subprotocol or first message `auth` frame  
**Messages:** JSON `{ "type": "service_signal.new", "payload": { ... } }`

| Direction | Types |
|-----------|-------|
| Server → client | `service_signal.new`, `table.state_changed`, `payment_session.opened` |
| Client → server | `signal.ack`, `ping` |

**Scale note:** One WS connection per staff device, not per table. MVP pilot ≤ 10 concurrent staff connections per venue.

### 6.4 Realtime fan-out implementation

```
Claim Service (transaction commit)
    → INSERT outbox_events
    → Worker notification.dispatch
        → Redis PUBLISH ps:{id}
        → SSE handler (in-memory subscriber map per Fly machine)
        → WS handler (restaurant channel)
```

**Fly.io constraint:** SSE sticky sessions via `fly-replay` or single API machine per pilot venue night. Post-MVP: Redis pub/sub bridges all API instances.

---

## 7. Auth stack

| Domain | Mechanism | Library | Storage |
|--------|-----------|---------|---------|
| Guest device | HttpOnly cookie `rt_device` | `@fastify/cookie` | Postgres `guest_devices` |
| Guest session | JWT `typ: guest` | `jose` | Stateless |
| Payment join | Raw token / 6-digit PIN | bcrypt hash in Postgres | `payment_session_tokens` |
| Payment participant | JWT `typ: payment_participant` | `jose` | Stateless; 2h TTL |
| Staff / admin | Email + password (pilot) | `@node-rs/bcrypt` | Postgres `staff_users` |
| Staff refresh | HttpOnly refresh token | Rotating refresh family | Postgres `staff_sessions` |
| Platform ops | Google Workspace SSO | OIDC via `@fastify/oauth2` | V1.1 — password OK for MVP internal |

**Staff SSO post-MVP:** WorkOS or Google OIDC for multi-tenant admin; not required for single pilot.

**Guest accounts (V1.1):** Magic link / OTP via Postmark — no passwords in MVP.

Full flows: [auth-and-sessions.md](./api/auth-and-sessions.md).

---

## 8. Mollie integration layer

### 8.1 MVP architecture

| Component | Implementation |
|-----------|----------------|
| SDK | `@mollie/api-client` v3 |
| OAuth | Mollie Connect — per-restaurant refresh token encrypted (AES-256-GCM, key in Fly secrets) |
| Payment create | `POST /v2/payments` with `amount`, `redirectUrl`, `webhookUrl`, `metadata` |
| Webhook | `POST /webhooks/mollie` → 200 in <500ms → BullMQ job |
| Verification | Worker `GET /v2/payments/{id}` before state transition |
| Refunds | Manager-initiated → Mollie Refunds API |
| Idempotency | Platform key in `metadata.idempotency_key` + local unique constraint |

**Account model (MVP):** Restaurant-owned Mollie organization; platform is technical agent — **not** merchant of record. See [payment-architecture.md](./payments/payment-architecture.md).

### 8.2 Module boundary (`apps/api/src/modules/mollie`)

```
mollie/
├── client.ts          # OAuth token refresh, circuit breaker
├── payments.ts        # createPayment, getPayment
├── refunds.ts         # createRefund
├── oauth.ts           # Connect onboarding callback
└── types.ts           # Narrow Mollie response types
```

**No business logic in adapter.** Payment Service owns checkout composition and ledger updates.

### 8.3 Webhook + reconciliation workers

| Worker | Queue | Schedule |
|--------|-------|----------|
| `webhook.process` | `webhooks` | On demand |
| `payment.reconcile.stale` | `reconciliation` | Every 15 min |
| `payment.reconcile.daily` | `reconciliation` | 06:00 CET |

Spec: [webhook-reconciliation.md](./payments/webhook-reconciliation.md).

---

## 9. Crypto integration placeholder

**MVP rule:** Module exists but is **not loaded in production routes**. All `/v1/crypto/*` return:

```json
{
  "type": "https://rekentafel.nl/errors/not-mvp",
  "title": "Crypto payments not available",
  "status": 501
}
```

| Artifact | Purpose |
|----------|---------|
| `apps/api/src/modules/crypto/stub.ts` | Feature-flag guard |
| `packages/api-contract/paths/crypto.yaml` | Documented 501 contract for parallel work |
| `apps/guest-web/src/features/crypto/` | Empty export; tree-shaken |

**Post-MVP direction:** Separate `crypto_payment_intents` table, licensed PSP with EUR settlement, **never** mixed Mollie balance. Full design: [crypto-rail-design.md](./payments/crypto-rail-design.md).

**Legal flag:** Enabling crypto without CASP/MiCA review exposes platform to AFM enforcement — stub prevents accidental ship.

---

## 10. Admin tooling and analytics

### 10.1 Admin / ops tooling (MVP)

| Need | Tool | Owner |
|------|------|-------|
| Restaurant config (tables, menu, staff) | `apps/admin-web` | Workstream D |
| Webhook reconciliation view | `apps/admin-web/ops` routes | Workstream D |
| Pilot provisioning | Platform ops form or SQL seed scripts | Workstream A |
| On-call runbooks | `docs/ops/runbooks/` | All |

**Retool / Forest Admin:** **Not MVP.** Internal React ops pages avoid third-party data processor expansion and GDPR DPA overhead for guest payment metadata.

### 10.2 Product analytics

| Layer | Tool | MVP scope | EU residency |
|-------|------|-----------|--------------|
| Product events | **PostHog Cloud EU** | Funnel: scan → join → claim → pay | Frankfurt |
| Server business events | Postgres `analytics_events` + nightly export | Conversion per venue | Self-hosted data |
| Error tracking | **Sentry** (EU region) | Guest checkout failures | EU |
| Financial reporting | Postgres + Metabase (self-hosted Fly app) | Restaurant payout reconciliation | EU |

**Events to capture (MVP):**

| Event | Properties | PII policy |
|-------|------------|------------|
| `guest.qr_scan` | `restaurant_id`, `table_id`, `session_state` | No device ID in PostHog |
| `guest.session_joined` | `payment_session_id`, `participant_count` | No display names |
| `guest.checkout_started` | `amount_cents`, `method` (from Mollie return) | No |
| `guest.checkout_paid` | `payment_id`, `latency_ms` | No |
| `staff.payment_mode_activated` | `table_id`, `bill_total_cents` | Staff user id hashed |

**Do not send** raw bill lines, guest nicknames, or join PINs to third-party analytics.

---

## 11. Infrastructure and deployment

### 11.1 Cloud provider recommendation

| Option | Verdict | Notes |
|--------|---------|-------|
| **Fly.io (primary)** | **MVP recommended** | `ams` region; WS/SSE support; Postgres + Redis add-ons; team already referenced in service-map |
| Hetzner Cloud + k3s | Cost alternative | Cheaper at scale; higher ops burden for 4 devs |
| AWS ECS (eu-central-1) | Post-MVP at 50+ venues | Enterprise compliance; slower iteration |
| Vercel (frontend only) | Partial | Guest/staff on Vercel + API on Fly adds CORS/cookie complexity for `rt_device` |
| Railway / Render | Acceptable pilot fallback | Fewer EU edge options than Fly |

**Decision:** **Fly.io** for API + workers + optional Metabase; **Cloudflare** for DNS, WAF, static asset CDN in front of Vite builds.

### 11.2 MVP runtime topology

| Process | Fly app | Machines | Resources |
|---------|---------|----------|-----------|
| `api` | `rekentafel-api` | 2 (HA) | shared-cpu-2x, 512MB |
| `worker` | `rekentafel-worker` | 1 | shared-cpu-2x, 512MB |
| `scheduler` | `rekentafel-worker` (leader election) | 1 | Same app, `SCHEDULER=1` |
| Guest/staff/admin static | Cloudflare Pages **or** Fly static | — | Edge cached |
| Postgres | Fly Postgres or Neon | 1 | 10GB pilot |
| Redis | Upstash EU or Fly Redis | 1 | 256MB pilot |

**Secrets:** Fly secrets + Doppler (optional) for Mollie platform credentials. Per-restaurant Mollie tokens in Postgres encrypted column.

**Environments:**

| Env | Purpose | Mollie |
|-----|---------|--------|
| `local` | Docker Compose: Postgres, Redis, MinIO | Test API keys |
| `staging` | Fly `staging` org | Mollie test mode |
| `production` | Fly `production` org | Live keys; single pilot venue |

### 11.3 CI/CD

| Stage | Tool | Gates |
|-------|------|-------|
| Lint / typecheck | GitHub Actions + Turborepo cache | Required |
| Unit + integration | Vitest + Testcontainers Postgres | Required |
| OpenAPI diff | `openapi-diff` vs main | Breaking change review |
| E2E | Playwright on staging | Nightly + pre-release |
| Deploy API | `fly deploy` on merge to `main` | Manual approval prod |
| Deploy web | Cloudflare Pages preview per PR | Auto |

---

## 12. Observability and testing (summary)

Full specification: [observability-testing.md](./observability-testing.md).

| Pillar | MVP stack |
|--------|-----------|
| Logs | Structured JSON (`pino`) → Grafana Loki |
| Metrics | OpenTelemetry → Prometheus → Grafana |
| Traces | OTel auto-instrument Fastify, pg, Redis, BullMQ |
| Dashboards | Payment success rate, webhook lag, claim conflict rate |
| Alerting | PagerDuty or Grafana OnCall — webhook failures, DB pool exhaustion |

---

## 13. Security and compliance hooks (stack-level)

| Risk | Stack mitigation |
|------|------------------|
| PSD2 / EMI scope creep | No platform wallet code paths; Mollie settlement direct to restaurant |
| GDPR | EU hosting; PostHog EU; guest data minimization; 90-day device purge job |
| Bill hijacking via leaked PIN | Short TTL tokens; rate limits; **no crypto fix** — staff training |
| XSS stealing participant JWT | HttpOnly cookie transport option; strict CSP on guest app |
| Webhook spoofing | Always verify via Mollie GET; unknown ID reject |
| Double payment | Idempotency keys + `processed_webhooks` PK |
| VAT display errors | `split-engine` pure module with golden tests; locale formatting separate from math |

Cross-ref: [threat-register.md](../security/threat-register.md), [control-matrix.md](../security/control-matrix.md).

---

## 14. MVP vs post-MVP stack gates

| Capability | MVP | V1.1 | V2 |
|------------|-----|------|-----|
| React PWA guest | ✓ | + push notifications | Native app evaluate |
| SSE guest realtime | ✓ | — | — |
| Staff WebSocket | ✓ | — | — |
| Drizzle + Postgres | ✓ | Read replica | Sharding not needed |
| BullMQ workers | ✓ | Horizontal workers | — |
| PostHog EU | ✓ | — | — |
| Metabase reporting | Basic | Restaurant dashboard | Franchise |
| Mollie Connect OAuth | ✓ | Marketplace split routing | — |
| Crypto module | **501 stub** | — | Licensed PSP integration |
| NestJS / microservices split | — | — | Evaluate at 25+ venues |
| Kubernetes | — | — | If leaving Fly |
| GraphQL / tRPC | — | — | Not planned |

---

## 15. Technology registry (canonical names)

Use these names in PRD, OpenAPI, and slice prompts — do not invent aliases per workstream.

| Registry name | Meaning |
|---------------|---------|
| `@rekentafel/api` | Fastify backend app |
| `@rekentafel/guest-web` | Guest PWA |
| `@rekentafel/staff-web` | Staff floor console |
| `@rekentafel/admin-web` | Restaurant admin + ops |
| `@rekentafel/api-contract` | OpenAPI + generated Zod |
| `@rekentafel/split-engine` | Pure bill calculation library |
| `@rekentafel/ui` | Shared React components |
| `@rekentafel/rbac` | Permission constants |
| `rekentafel-api` | Fly.io API app name |
| `rekentafel-worker` | Fly.io worker app name |

---

## 16. Risks specific to this slice

| Risk | Severity | Mitigation |
|------|----------|------------|
| Four workstreams drift on dependency versions | High | `pnpm catalog` + Renovate bot; Turborepo shared `packages/config` |
| SSE sticky session on multi-machine Fly | Medium | Pilot single region; Redis pub/sub bridge before second venue scale |
| Drizzle learning curve vs Prisma | Low | Workstream A owns patterns; split-engine golden tests |
| OpenTelemetry overhead on webhook path | Low | Sample 10% traces except payment routes (100%) |
| Cloudflare + Fly cookie domain mismatch | Medium | Single parent domain `.rekentafel.nl`; document cookie scope |
| Premature microservices extraction | Medium | Enforce modular monolith import lint through V2 |
| Crypto stub forgotten in prod flag check | High | CI assertion: no `crypto` route registered when `FEATURE_CRYPTO=false` |

---

## 17. Alternatives considered (meaningful only)

| Layer | Alternative | Why not MVP |
|-------|-------------|-------------|
| DB | CockroachDB | Overkill; Postgres row locks sufficient for pilot concurrency |
| Realtime | Supabase Realtime | Couples to Supabase auth/storage; payment logic stays custom |
| Realtime | Pusher / Ably | Extra vendor + GDPR; SSE/WS native adequate |
| Queue | SQS | Adds AWS lock-in; BullMQ + Redis already required for locks |
| ORM | Prisma | Hidden SQL for allocation constraints |
| Frontend | Expo native | Out of MVP scope |
| Payments | Stripe | Weaker NL iDEAL hospitality penetration vs Mollie |
| Hosting | Supabase full stack | Bill split logic non-trivial; not a CRUD app |

---

*Slice ownership: Part 16 — Recommended Tech Stack. Files owned exclusively by this slice: `docs/architecture/tech-stack.md`, `docs/architecture/infra-diagram.mmd`, `docs/architecture/observability-testing.md`.*
