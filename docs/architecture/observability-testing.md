# Observability and Testing Strategy

**Product (working name):** Rekentafel / TabSettle  
**Slice:** Part 16 — Recommended Tech Stack  
**Stack context:** Node.js 22, Fastify, PostgreSQL, Redis, BullMQ, Fly.io (ams), OpenTelemetry  
**Cross-references:** [tech-stack.md](./tech-stack.md), [service-map.md](./api/service-map.md), [idempotency-concurrency.md](./api/idempotency-concurrency.md), [webhook-reconciliation.md](./payments/webhook-reconciliation.md)

---

## 1. Observability principles

| Principle | Implementation |
|-----------|----------------|
| Correlate guest → payment → webhook | Single `request_id` (UUID v7) propagated through logs, traces, audit |
| Financial paths are fully traced | 100% trace sample on `/checkout`, `/webhooks/mollie`, claim mutations |
| Never log secrets | No raw payment tokens, join PINs, Mollie access tokens, or full JWT |
| EU data residency | Grafana Cloud EU, Sentry EU, PostHog EU |
| Alert on money inconsistency | `ledger.remaining_cents < 0` invariant monitor |
| Guest PII minimization in logs | Log `participant_id` hashes in debug; full ID in audit table only |

---

## 2. Logging

### 2.1 Logger choice

| Component | Library | Format |
|-----------|---------|--------|
| API + workers | `pino` via `pino-pretty` (local only) | JSON lines |
| HTTP access | `@fastify/request-context` + child loggers | Nested JSON |
| Redaction | `pino.redact` paths | See §2.3 |

**Log level defaults:**

| Environment | API | Worker |
|-------------|-----|--------|
| local | `debug` | `debug` |
| staging | `info` | `info` |
| production | `info` | `warn` (worker info for job lifecycle) |

### 2.2 Required log fields (every request)

| Field | Source | Example |
|-------|--------|---------|
| `request_id` | `X-Request-Id` or generated | `01932a7b-8c4d-7000-8000-000000000001` |
| `timestamp` | ISO-8601 UTC | `2026-06-26T18:45:00.123Z` |
| `service` | Constant | `rekentafel-api` |
| `env` | Fly machine env | `production` |
| `method` | HTTP | `POST` |
| `path` | Route template | `/v1/payment-sessions/:id/claims` |
| `status_code` | Response | `201` |
| `duration_ms` | Timer | `42` |
| `restaurant_id` | Auth context if present | UUID |
| `payment_session_id` | Auth/body if present | UUID |
| `actor_type` | `guest` / `staff` / `system` | `guest` |
| `actor_id` | `participant_id` or `staff_user_id` | UUID |

### 2.3 Redaction paths

```javascript
// pino redact configuration (conceptual)
const redactPaths = [
  'req.headers.authorization',
  'req.headers.cookie',
  'req.body.token',
  'req.body.join_pin',
  'req.body.password',
  'res.headers["set-cookie"]',
  'mollie.access_token',
  'mollie.refresh_token',
];
```

**Webhook logs:** Log `mollie_payment_id` (`tr_xxx`) and job ID only — not full Mollie response bodies in production.

### 2.4 Log shipping

| Stage | Destination | Retention |
|-------|-------------|-----------|
| Fly stdout | Grafana Loki via Alloy / Fly log shipper | 30 days hot |
| Audit mutations | Postgres `audit_events` | 7 years |
| Security events | Separate `security_events` stream | 1 year |

**Query examples (LogQL):**

```logql
# Failed checkouts last hour
{service="rekentafel-api"} | json | path="/v1/payment-sessions/*/checkout" | status_code >= 400

# Webhook processing lag
{service="rekentafel-worker"} | json | msg="webhook.process.complete" | duration_ms > 5000
```

---

## 3. Metrics

### 3.1 Instrumentation

| Layer | Instrumentation |
|-------|-----------------|
| HTTP | `@opentelemetry/instrumentation-fastify` |
| Postgres | `@opentelemetry/instrumentation-pg` |
| Redis | `@opentelemetry/instrumentation-ioredis` |
| BullMQ | Custom span wrapper on job handlers |
| Mollie HTTP | `undici` OTel instrumentation |

**Exporter:** OTLP HTTP → Grafana Cloud Prometheus (EU).

### 3.2 Golden signals (MVP dashboards)

#### API health

| Metric | Type | Labels | Alert threshold |
|--------|------|--------|-----------------|
| `http_server_duration_ms` | Histogram | `route`, `method`, `status` | p99 > 2000ms for 5m |
| `http_requests_total` | Counter | `route`, `status` | 5xx rate > 1% for 5m |
| `active_sse_connections` | Gauge | `fly_region` | > 800 per machine |
| `active_ws_connections` | Gauge | `restaurant_id` | informational |

#### Payment / money

| Metric | Type | Labels | Alert threshold |
|--------|------|--------|-----------------|
| `checkout_created_total` | Counter | `restaurant_id` | — |
| `checkout_paid_total` | Counter | `restaurant_id`, `method` | — |
| `checkout_failed_total` | Counter | `reason` | > 10/hour pilot venue |
| `webhook_received_total` | Counter | `status` | — |
| `webhook_processing_lag_ms` | Histogram | — | p99 > 30000ms |
| `webhook_verification_failures_total` | Counter | — | > 0 sustained 5m |
| `ledger_remaining_cents` | Gauge | `payment_session_id` | < 0 **page immediately** |
| `mollie_api_errors_total` | Counter | `operation` | circuit open |

#### Claims / concurrency

| Metric | Type | Labels | Alert threshold |
|--------|------|--------|-----------------|
| `claim_created_total` | Counter | `restaurant_id` | — |
| `claim_conflict_total` | Counter | `reason` | > 50/hour (possible abuse) |
| `claim_lock_redis_miss_total` | Counter | — | Postgres fallback rate |
| `idempotency_cache_hit_total` | Counter | — | informational |

#### Workers

| Metric | Type | Labels | Alert threshold |
|--------|------|--------|-----------------|
| `bullmq_job_duration_ms` | Histogram | `queue`, `job_name` | p99 > 60000ms |
| `bullmq_job_failed_total` | Counter | `queue`, `job_name` | > 3 same job in 10m |
| `bullmq_queue_waiting` | Gauge | `queue` | > 100 for 5m |

### 3.3 SLIs (MVP pilot)

| SLI | Target | Measurement window |
|-----|--------|-------------------|
| Guest API availability | 99.5% | 30 days |
| Checkout initiation success | 99.0% | 7 days |
| Webhook → ledger update | 99.9% within 60s | 7 days |
| SSE delivery (claim update) | 95% within 2s of commit | 7 days |

**Error budget:** 0.5% monthly downtime ≈ 3.6 hours — acceptable for pilot; post-MVP tighten to 99.9%.

---

## 4. Distributed tracing

### 4.1 Trace context propagation

```
Guest POST /claims
  trace_id: abc123
  span: api.claim.create
    span: pg.transaction
    span: redis.lock.acquire
    span: outbox.insert
  (async) worker.notification.dispatch
    span: redis.publish
    span: sse.push
```

| Header | Purpose |
|--------|---------|
| `traceparent` | W3C trace context (OTel default) |
| `X-Request-Id` | Business correlation (also in audit) |

**Sample rates:**

| Route class | Sample rate |
|-------------|-------------|
| `/checkout`, `/webhooks/*`, claim mutations | **100%** |
| SSE connect | 10% |
| Menu read `/t/*` | 1% |
| Admin config | 5% |

### 4.2 Critical spans to inspect in incidents

| Incident | Trace query |
|----------|-------------|
| Guest paid but balance unchanged | Find `mollie_payment_id` → webhook span → ledger update span |
| Double claim | Two `claim.create` spans same `unit_id` — second should show `409` |
| Slow checkout | `mollie.createPayment` child span duration |

---

## 5. Alerting and on-call

### 5.1 Alert routing (MVP)

| Severity | Channel | Response |
|----------|---------|----------|
| P1 — money wrong | PagerDuty / phone | 15 min |
| P1 — API down | PagerDuty | 15 min |
| P2 — webhook backlog | Slack `#ops` | 1 hour |
| P3 — elevated 409 claims | Slack | Next business day |

### 5.2 Alert rules (concrete)

| Alert name | Condition | Severity |
|------------|-----------|----------|
| `LedgerNegativeRemaining` | `ledger_remaining_cents < 0` | P1 |
| `WebhookLagCritical` | p99 processing > 60s for 5m | P1 |
| `MollieCircuitOpen` | circuit breaker open > 2m | P1 |
| `ApiErrorRate` | 5xx > 1% for 5m | P1 |
| `PostgresPoolExhausted` | waiting connections > 10 for 2m | P2 |
| `RedisUnavailable` | Redis errors > 10/min | P2 |
| `ClaimConflictSpike` | > 50 conflicts/hour/venue | P3 |

### 5.3 Runbook links (stub paths)

| Alert | Runbook |
|-------|---------|
| Webhook lag | `docs/ops/runbooks/webhook-backlog.md` |
| Ledger mismatch | `docs/ops/runbooks/ledger-reconciliation.md` |
| Mollie outage | `docs/ops/runbooks/mollie-degraded.md` |

---

## 6. Testing strategy — pyramid

```
                    ┌─────────────┐
                    │  E2E (few)  │  Playwright — guest pay, staff activate
                   ┌┴─────────────┴┐
                   │ Integration    │  Testcontainers PG + Redis + API boot
                  ┌┴───────────────┴┐
                  │ Unit (many)      │  split-engine, VAT, idempotency, Zod
                  └──────────────────┘
```

| Layer | Tool | Count target (MVP) | CI time budget |
|-------|------|-------------------|----------------|
| Unit | Vitest | 200+ tests | < 30s |
| Integration | Vitest + Testcontainers | 40+ tests | < 3 min |
| Contract | OpenAPI + Dredd or schemathesis | All `/v1` paths | < 2 min |
| E2E | Playwright | 12–18 scenarios | < 8 min (nightly full) |
| Load (pilot gate) | k6 | 1 script | Pre-pilot manual |

---

## 7. Unit testing

### 7.1 Framework and layout

| Setting | Value |
|---------|-------|
| Runner | Vitest 2.x |
| Location | Colocated `*.test.ts` + `packages/split-engine/__tests__/` |
| Coverage target | 90% on `split-engine`, 80% on payment/claim modules |
| Mocking | MSW for Mollie HTTP; no DB in pure unit tests |

### 7.2 Mandatory unit test suites

| Module | Example test cases |
|--------|-------------------|
| `split-engine` | Equal split 3 ways on €86.40; remainder cent to first claimant |
| `split-engine` | Shared item 50/50; rejects 60/50 |
| `split-engine` | Service charge pro-rata after partial claims |
| `claim` | Quantity split: 2 beers, 1 claimed → half unit remains |
| `idempotency` | Same key + same body → cached response |
| `idempotency` | Same key + different body → 422 |
| `payment` | Checkout amount = allocation + tip; rejects float amounts |
| `token` | Expired token rejected; refresh extends TTL within cap |
| `mollie adapter` | Maps Mollie `paid` → internal `PAID` enum |

**Numeric golden test (from rules-spec):**

```
Bill total: 8640 cents (€86.40)
4 guests equal split → [2160, 2160, 2160, 2160]
3 guests equal split → [2880, 2880, 2880]
7 guests equal split on 8640 → [1235, 1235, 1235, 1235, 1235, 1235, 1230]  # remainder to last
```

---

## 8. Integration testing

### 8.1 Infrastructure

| Component | Approach |
|-----------|----------|
| PostgreSQL | `@testcontainers/postgresql` — fresh DB per suite |
| Redis | `@testcontainers/redis` |
| Migrations | `drizzle-kit migrate` before suite |
| API | `fastify.inject()` for HTTP; supertest optional |
| BullMQ | Real Redis container; workers in-process test mode |

### 8.2 Required integration scenarios

| # | Scenario | Assert |
|---|----------|--------|
| I1 | Waiter opens payment session → guest joins with PIN | `participant_id` issued; SSE channel registered |
| I2 | Two concurrent claims on same unit | One 201, one 409; DB single active allocation |
| I3 | Guest checkout → webhook worker | `confirmed_paid_cents` increments; ledger event emitted |
| I4 | Duplicate webhook delivery | Idempotent — single ledger credit |
| I5 | Bill edit after partial pay | Unpaid allocations invalidated; paid rows locked |
| I6 | Idempotency replay on checkout | Same Mollie payment ID not duplicated |
| I7 | Force close with remainder | Table `CLOSED`; unpaid flagged |
| I8 | Mollie API timeout on create | Payment intent `FAILED`; allocation unlocked |

### 8.3 Concurrency torture test (pre-pilot gate)

**Tool:** Vitest concurrent + `Promise.all`  
**Target:** 50 parallel `POST /claims` on 10 units — **zero** double allocations  
**Reference:** [idempotency-concurrency.md](./api/idempotency-concurrency.md) §1

---

## 9. Contract testing

| Artifact | Role |
|----------|------|
| `packages/api-contract/openapi.yaml` | Source of truth |
| CI `openapi-diff` | Block breaking changes without version bump |
| Schemathesis or Dredd | Fuzz public `/v1` routes against running staging |
| Generated Zod | Request validation matches spec |

**Parallel dev rule:** Workstreams B/C/D must not merge if `pnpm generate:contract` diff fails against their client usage.

---

## 10. End-to-end testing (Playwright)

### 10.1 Configuration

| Setting | Value |
|---------|-------|
| Location | `e2e/` |
| Browsers | Chromium mobile (Pixel 5) + iPad staff viewport |
| Base URL | `https://staging.rekentafel.nl` |
| Mollie | Test mode + mock redirect handler in staging |
| Auth | Staff seed script; guest flows use test PIN |

### 10.2 MVP E2E scenarios (must pass before pilot)

| ID | Flow | Steps | Assert |
|----|------|-------|--------|
| E1 | Empty table QR | Scan `/t/{slug}/{code}` | Menu visible; no bill |
| E2 | Call server | Tap call waiter | Staff WS receives signal |
| E3 | Payment activation | Staff opens payment mode | Guest sees join screen |
| E4 | Join + item claim | 2 guests join; each claims items | Totals match; SSE updates both |
| E5 | Equal split | 4 guests equal split €86.40 | Each shows €21.60 |
| E6 | Shared item | 2 guests 50/50 on shared plate | Amounts sum to line |
| E7 | Tip + checkout | Guest adds 10% tip; Mollie test pay | Redirect success; balance updates |
| E8 | Partial table pay | 2 of 4 pay | Remaining balance visible |
| E9 | Claim conflict UI | Simultaneous click same item | One succeeds; other sees error |
| E10 | Manager override | Manager reassigns claim | Guest UI updates via SSE |
| E11 | Force close | Manager closes unpaid remainder | Session closed message |
| E12 | VAT display | Bill with 9% and 21% lines | Correct BTW labels (NL) |

### 10.3 Playwright example structure

```
e2e/
├── guest/
│   ├── join-and-claim.spec.ts
│   ├── checkout-mollie.spec.ts
│   └── partial-pay.spec.ts
├── staff/
│   ├── activate-payment.spec.ts
│   └── service-signal.spec.ts
├── fixtures/
│   ├── seed-restaurant.ts
│   └── mollie-mock.ts
└── playwright.config.ts
```

**Stability rules:**
- Use `data-testid` on claim buttons and balance — not CSS classes
- Wait for SSE event or API poll, not fixed `sleep`
- Isolate test restaurants via seed IDs

---

## 11. Load and performance testing (pre-pilot)

### 11.1 k6 script scope

| Scenario | VUs | Duration | Pass criteria |
|----------|-----|----------|---------------|
| Menu scan | 50 | 2 min | p95 < 500ms |
| Payment session join | 20 | 5 min | p95 < 800ms |
| Concurrent claims | 30 | 1 min | 0 double allocations |
| SSE connections | 40 | 10 min | No machine OOM |

**Run manually** before first Friday night pilot service — not every CI build.

### 11.2 Performance budgets (guest web)

| Metric | Budget |
|--------|--------|
| LCP (4G) | < 2.5s on join screen |
| TTI | < 3.5s |
| SSE update render | < 500ms from event |
| Mollie redirect | < 1s to hosted checkout |

---

## 12. Test data and environments

| Env | Postgres | Mollie | Playwright |
|-----|----------|--------|------------|
| local | Docker | Test keys | Optional |
| CI | Testcontainers | MSW mock | Chromium only |
| staging | Neon branch | Mollie test | Full suite nightly |
| production | Fly Postgres | Live | **No automated write tests** |

**Seed data:** `scripts/seed-pilot-restaurant.ts` — 12 tables, 40 menu items, 3 staff users, Mollie test org.

---

## 13. CI pipeline (GitHub Actions)

```yaml
# Conceptual — see infra/ci.yml at implementation
jobs:
  lint-typecheck:
    runs: turbo lint typecheck

  unit:
    runs: turbo test:unit

  integration:
    runs: turbo test:integration
    services: docker

  contract:
    runs: pnpm test:contract
    needs: integration

  e2e:
    runs: pnpm test:e2e
    if: github.event_name == 'schedule' || contains(github.ref, 'release')
    environment: staging

  deploy-staging:
    needs: [unit, integration, contract]
    if: github.ref == 'refs/heads/main'
```

**Merge gate:** Unit + integration + contract required on every PR. E2E required for release tags.

---

## 14. MVP vs post-MVP observability and testing

| Capability | MVP | V1.1 | V2 |
|------------|-----|------|-----|
| Grafana dashboards | Payment + webhook + API | Per-restaurant view | Franchise rollup |
| PagerDuty | Founders on-call | Rotation | — |
| Playwright E2E | 12 scenarios | + admin flows | + POS import |
| k6 load tests | Pre-pilot manual | Weekly staging | Continuous |
| Chaos testing | — | Redis failure drill | — |
| Synthetic monitoring | Pingdom `/health` | Guest journey synthetics | — |
| Visual regression | — | Percy optional | — |
| Security scanning | `npm audit`, Semgrep | SAST in CI | Pen test |

---

## 15. Risks specific to this slice

| Risk | Impact | Mitigation |
|------|--------|------------|
| E2E flakiness on SSE | False confidence | Event-based waits; retry only on network |
| Testcontainers CI slowness | Devs skip integration | Turbo cache; parallel shards |
| Logging PII in debug | GDPR breach | Redact list + CI grep for `join_pin` |
| Alert fatigue | Miss real P1 | Start with 6 alerts only; tune after pilot |
| No load test before busy night | SSE machine OOM | k6 gate + `active_sse_connections` alert |
| Mollie test ≠ prod behavior | Checkout surprises | One live €0.01 internal test weekly |

---

*Slice ownership: Part 16 — Recommended Tech Stack. Companion files: [tech-stack.md](./tech-stack.md), [infra-diagram.mmd](./infra-diagram.mmd).*
