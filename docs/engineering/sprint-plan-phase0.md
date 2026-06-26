# Phase 0 Sprint Plan — Architecture Sprint (Weeks 1–2)

**Product:** Rekentafel  
**Duration:** 10 working days (2 calendar weeks)  
**Team:** 4 developers on ws-1 … ws-4  
**Parent:** [implementation-roadmap.md](./implementation-roadmap.md)  
**Exit gate:** M0 — no MVP sprint work starts until checklist §10 is green

---

## 1. Objectives

Phase 0 produces **executable contracts**, not slides:

1. **OpenAPI v1** — guest, staff, admin, webhook routes stubbed with request/response schemas
2. **ERD → Prisma schema v0** — all MVP entities from [entity-dictionary.md](../architecture/data-model/entity-dictionary.md)
3. **State machines in code** — pure TS with tests matching [state-machines.md](../domain/split-engine/state-machines.md)
4. **MSW mock server** — frontends navigable without API
5. **Monorepo + CI + ui-core v0** — parallel M1 start unblocked

**Challenge:** Teams that skip mock parity will lose 3–5 days in M4 integration. MSW handlers **must import Zod schemas from `@rekentafel/contracts`**, not duplicate JSON.

---

## 2. Roles and ownership

| Person | WS | Phase 0 focus |
|--------|-----|---------------|
| Dev A | ws-4 | Monorepo, CI, Docker, ui-core, Storybook |
| Dev B | ws-3 | Contracts, DB, split-engine, mock fixtures, API shell |
| Dev C | ws-2 | Staff + admin app shells, staff-hooks codegen |
| Dev D | ws-1 | Guest app shell, guest-hooks codegen, MSW consumer |

**Platform lead** (may be Dev B): owns contract approval, state machine parity sign-off, daily 15-min standup.

**Ops parallel track (non-dev):** Initiate pilot restaurant Mollie test account KYC — lead time 3–10 business days.

---

## 3. Week 1 — Contracts, ERD, foundations

### 3.1 Week 1 overview

| Day | Theme | Primary WS |
|-----|-------|------------|
| Mon | Monorepo boot + CI skeleton | ws-4 |
| Tue | OpenAPI route inventory + money/auth primitives | ws-3 |
| Wed | Prisma schema v0 + first migration | ws-3 |
| Thu | State machines + split-engine module | ws-3 |
| Fri | App shells + ui-core primitives batch 1 | ws-1, ws-2, ws-4 |

### 3.2 Day-by-day tasks

#### Monday (Day 1)

| ID | Task | Owner | Files (exclusive) | Done when |
|----|------|-------|-------------------|-----------|
| W1-D1-01 | Init pnpm workspace, Turborepo, root `package.json` | ws-4 | `pnpm-workspace.yaml`, `turbo.json`, `package.json`, `tsconfig.base.json` | `pnpm install` succeeds |
| W1-D1-02 | Docker Compose: Postgres 16 + Redis 7 | ws-4 | `infra/docker/docker-compose.dev.yml` | `docker compose up -d` healthy |
| W1-D1-03 | ESLint + Prettier + TS shared config | ws-4 | `packages/config/**` | `pnpm lint` runs (empty pass) |
| W1-D1-04 | CI workflow: install, lint, typecheck | ws-4 | `.github/workflows/ci.yml` | PR checks run on push |
| W1-D1-05 | Fastify app shell + health route | ws-3 | `apps/api/src/server.ts`, `modules/health/` | `GET /health` → 200 |
| W1-D1-06 | OpenAPI file scaffold + Spectral config | ws-3 | `packages/contracts/openapi/rekentafel.v1.yaml`, `scripts/lint-openapi.ts` | Spectral lint passes on stub |

**Demo artifact (EOD):** CI green on `main`; health check curl screenshot in Slack.

#### Tuesday (Day 2)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W1-D2-01 | Define `money.ts`, `problem.ts`, pagination Zod | ws-3 | `packages/contracts/src/schemas/common/` | Unit test: reject float amounts |
| W1-D2-02 | Guest routes: `GET /t/{slug}/{tableCode}`, signals, join session | ws-3 | `openapi/` guest section | Paths documented with 200/404 schemas |
| W1-D2-03 | Staff routes: login, floor, session CRUD, signals inbox | ws-3 | `openapi/` staff section | RBAC notes in description fields |
| W1-D2-04 | Admin routes: tables, menu, staff CRUD (stubs) | ws-3 | `openapi/` admin section | — |
| W1-D2-05 | Webhook route: `POST /webhooks/mollie` | ws-3 | `openapi/` webhooks | Idempotency-Key documented |
| W1-D2-06 | ui-core tokens + Button, Input, Skeleton | ws-4 | `packages/ui-core/src/tokens/`, primitives | Storybook story renders |
| W1-D2-07 | Guest app Vite shell + router placeholders | ws-1 | `apps/guest-web/src/app/router.tsx` | Dev server on :5173 |
| W1-D2-08 | Staff app Vite shell + router placeholders | ws-2 | `apps/staff-web/src/app/router.tsx` | Dev server on :5174 |

**Demo artifact:** OpenAPI preview (Swagger UI) showing ≥20 paths.

#### Wednesday (Day 3)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W1-D3-01 | Prisma schema: tenancy (`restaurants`, `venues`, `tables`, `table_qr_codes`) | ws-3 | `packages/db/prisma/schema.prisma` | `prisma validate` pass |
| W1-D3-02 | Prisma schema: sessions (`dining_sessions`, `payment_sessions`, `payment_session_tokens`) | ws-3 | same | FK graph matches entity dictionary |
| W1-D3-03 | Prisma schema: bill domain (`bills`, `bill_lines`, `allocatable_units`, `allocations`, `participants`) | ws-3 | same | — |
| W1-D3-04 | Prisma schema: payments (`checkout_intents`, `payment_intents`, `payments`, `tips`, `webhook_events`) | ws-3 | same | — |
| W1-D3-05 | Prisma schema: staff, menu, audit, signals | ws-3 | same | — |
| W1-D3-06 | Migration `0001_init` + seed pilot venue | ws-3 | `migrations/`, `seed/pilot-venue.ts` | 20 tables, 30 menu items seeded |
| W1-D3-07 | `pnpm --filter @rekentafel/db prisma migrate dev` in README | ws-4 | `docs/engineering` cross-ref in root README | New dev bootstrap ≤15 min |
| W1-D3-08 | Admin app shell (separate deploy target) | ws-2 | `apps/admin-web/` | :5175 boots |

**Demo artifact:** ERD diagram export from Prisma Studio; seed venue `de-rekentafel-pilot` queryable.

#### Thursday (Day 4)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W1-D4-01 | `TableSessionState` enum + transition function | ws-3 | `apps/api/src/domain/session/state.ts` | 100% transition table covered |
| W1-D4-02 | `TableBillSettlement` state machine + guards | ws-3 | `apps/api/src/domain/split-engine/settlement.ts` | Guards match doc §3.4 |
| W1-D4-03 | `Claimant` state machine | ws-3 | `apps/api/src/domain/split-engine/claimant.ts` | — |
| W1-D4-04 | VAT allocation (NL 9%/21%) pure functions | ws-3 | `apps/api/src/domain/vat/` | Test: €126.40 example splits |
| W1-D4-05 | Split-engine: item, equal, custom, shared modes | ws-3 | `apps/api/src/domain/split-engine/` | 6 worked examples pass |
| W1-D4-06 | Concurrency test harness (50 parallel claims) | ws-3 | `apps/api/tests/split-engine/concurrency.test.ts` | Zero double-allocation |
| W1-D4-07 | ui-core: MoneyDisplay, Modal, Toast, Badge | ws-4 | `packages/ui-core/` | Storybook updated |
| W1-D4-08 | CODEOWNERS + PR template | ws-4 | `.github/CODEOWNERS`, `pull_request_template.md` | Path ownership enforced |

**Demo artifact:** Test report — `pnpm --filter @rekentafel/api test split-engine` all green.

#### Friday (Day 5)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W1-D5-01 | Event payload schemas (dining, payment, claim) | ws-3 | `packages/contracts/src/events/` | Align with [event-catalog.md](../flows/event-catalog.md) |
| W1-D5-02 | OpenAPI ↔ Zod generation pipeline | ws-3 | `packages/contracts/scripts/` | `pnpm generate:schemas` idempotent |
| W1-D5-03 | Hook codegen script (openapi-typescript) | ws-3 + ws-4 | `infra/scripts/generate-clients.ts` | Stub hooks compile |
| W1-D5-04 | guest-hooks + staff-hooks packages init | ws-1, ws-2 | `packages/guest-hooks/`, `staff-hooks/` | Import in apps without error |
| W1-D5-05 | Guest routes wired to placeholder pages | ws-1 | `apps/guest-web/src/routes/` | Navigate all MVP routes (empty UI) |
| W1-D5-06 | Staff routes wired (login, floor, table) | ws-2 | `apps/staff-web/src/routes/` | — |
| W1-D5-07 | Week 1 demo recording | All | — | 5-min Loom: repo boot → Storybook → OpenAPI → tests |

**Week 1 exit criteria:**

- [ ] OpenAPI ≥20 paths, Spectral 0 errors
- [ ] DB migration applies clean on empty Postgres
- [ ] Split-engine numeric tests pass
- [ ] 3 apps boot with shared ui-core

---

## 4. Week 2 — Mock server, API stubs, Phase 0 completion

### 4.1 Week 2 overview

| Day | Theme | Primary WS |
|-----|-------|------------|
| Mon | MSW handlers from Zod — guest flows A–D | ws-3 + ws-1 |
| Tue | MSW handlers — staff flows C, signals | ws-3 + ws-2 |
| Wed | API route stubs returning fixture data | ws-3 |
| Thu | Auth middleware + token issuance stubs | ws-3 |
| Fri | M0 exit gate + Phase 0 demo | All |

### 4.2 Day-by-day tasks

#### Monday (Day 6)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W2-D6-01 | `test-fixtures` factory builders (venue, table, bill) | ws-3 | `packages/test-fixtures/src/factories/` | Factories typed from Zod |
| W2-D6-02 | MSW: `GET /t/{slug}/{tableCode}` empty + seated states | ws-3 | `packages/test-fixtures/src/handlers/guest/` | Returns menu; no bill lines |
| W2-D6-03 | MSW: call-server POST | ws-3 | same | 201 + signal id |
| W2-D6-04 | MSW: join payment session (token required) | ws-3 | same | 401 without token; 200 with |
| W2-D6-05 | Guest MSW bootstrap in app | ws-1 | `apps/guest-web/src/mocks/` | `VITE_API_MOCK=true` loads handlers |
| W2-D6-06 | Landing + menu pages with real layout | ws-1 | `routes/landing/`, `routes/menu/` | Mobile 375px screenshot |

**Demo artifact:** Guest scan QR → menu → call server (mock).

#### Tuesday (Day 7)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W2-D7-01 | MSW: staff login + JWT cookie | ws-3 | `handlers/staff/auth.ts` | Sets HttpOnly cookie in browser |
| W2-D7-02 | MSW: floor table grid + session states | ws-3 | `handlers/staff/floor.ts` | 20 tables from seed |
| W2-D7-03 | MSW: start session, activate payment (issues token) | ws-3 | `handlers/staff/session.ts` | State → PAYMENT_ACTIVE |
| W2-D7-04 | MSW: signals inbox | ws-3 | `handlers/staff/signals.ts` | Call-server appears after guest action |
| W2-D7-05 | Staff MSW bootstrap | ws-2 | `apps/staff-web/src/mocks/` | Mock mode works |
| W2-D7-06 | Floor grid UI (read-only mock data) | ws-2 | `components/TableTile/` | Color by session state |

**Demo artifact:** Staff login → start session Table 5 → activate payment → token displayed.

#### Wednesday (Day 8)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W2-D8-01 | API implements `GET /t/{slug}/{tableCode}` against DB | ws-3 | `apps/api/src/modules/guest/` | Matches MSW shape (contract test) |
| W2-D8-02 | API: staff auth login (bcrypt seed user) | ws-3 | `modules/staff/auth.ts` | Contract test pass |
| W2-D8-03 | API: `POST /staff/sessions` start dining session | ws-3 | `modules/session/` | State EMPTY→SEATED |
| W2-D8-04 | API: `POST /staff/sessions/{id}/payment/activate` | ws-3 | same | Issues payment token; bill still draft OK |
| W2-D8-05 | Contract snapshot tests (MSW vs API) | ws-3 | `apps/api/tests/contract/` | Guest table context responses identical |
| W2-D8-06 | ui-core remaining primitives (FormField, PageShell, EmptyState) | ws-4 | `packages/ui-core/` | 12 primitives complete per repo-structure |
| W2-D8-07 | Admin shell: tables list placeholder | ws-2 | `apps/admin-web/routes/tables/` | — |

**Demo artifact:** Same guest flow on `VITE_API_MOCK=false` against local API.

#### Thursday (Day 9)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W2-D9-01 | Guest ephemeral token middleware | ws-3 | `apps/api/src/plugins/auth.ts` | Validates join token |
| W2-D9-02 | Staff JWT middleware + RBAC constants | ws-3 | same + `packages/contracts/src/rbac.ts` | Waiter vs manager roles |
| W2-D9-03 | SSE stub endpoint `/guest/sessions/{id}/events` | ws-3 | `apps/api/src/sse/bill-events.ts` | Returns heartbeat + mock event |
| W2-D9-04 | WebSocket stub `/staff/ws` | ws-3 | `apps/api/src/ws/staff-desk.ts` | Signal push on call-server |
| W2-D9-05 | Mollie sandbox: manual test payment + ngrok webhook | ws-3 + ws-4 | runbook in PR description | One `tr_test_*` webhook logged |
| W2-D9-06 | Worker shell + BullMQ connection | ws-3 | `apps/worker/src/index.ts` | Worker connects Redis; no jobs yet |
| W2-D9-07 | Playwright project scaffold | ws-4 | `apps/guest-web/tests/e2e/` | One smoke test runs |

**Demo artifact:** Webhook received and stored in `webhook_events` table.

#### Friday (Day 10)

| ID | Task | Owner | Files | Done when |
|----|------|-------|-------|-----------|
| W2-D10-01 | OpenAPI breaking-change CI gate | ws-3 | `packages/contracts/scripts/diff-breaking.ts` | CI fails on removed field |
| W2-D10-02 | `pnpm generate:hooks` in CI post-contract merge | ws-4 | `.github/workflows/ci.yml` | Automated codegen job |
| W2-D10-03 | Phase 0 documentation review | Platform lead | — | State machine parity checklist signed |
| W2-D10-04 | M0 demo: full mock E2E | All | — | Record: QR → session → payment token (mock bill next sprint) |
| W2-D10-05 | M1 sprint kickoff — slice assignments confirmed | All | — | [sprint-plan-mvp.md](./sprint-plan-mvp.md) §M1 acknowledged |

---

## 5. Phase 0 deliverable matrix

| Artifact | Path | Owner | Verification |
|----------|------|-------|--------------|
| OpenAPI v1 | `packages/contracts/openapi/rekentafel.v1.yaml` | ws-3 | Spectral + breaking diff CI |
| Zod schemas | `packages/contracts/src/schemas/` | ws-3 | Snapshot tests |
| Prisma schema | `packages/db/prisma/schema.prisma` | ws-3 | Migrate + seed |
| Split-engine | `apps/api/src/domain/split-engine/` | ws-3 | Unit + concurrency tests |
| State machines | `apps/api/src/domain/session/`, `split-engine/` | ws-3 | Transition table 100% |
| MSW handlers | `packages/test-fixtures/src/handlers/` | ws-3 | Guest + staff flows A–D |
| ui-core v0 | `packages/ui-core/` | ws-4 | Storybook 12 primitives |
| CI pipeline | `.github/workflows/ci.yml` | ws-4 | Green on main |
| Guest shell | `apps/guest-web/` | ws-1 | MSW + real API toggle |
| Staff shell | `apps/staff-web/`, `apps/admin-web/` | ws-2 | MSW + real API toggle |
| API stubs | `apps/api/` | ws-3 | Contract tests vs MSW |

---

## 6. State machine implementation checklist

Map each transition to a test case name (Phase 0 minimum — HTTP wiring in M1–M3).

### 6.1 TableSessionState

| Transition | Test name | Phase 0 |
|------------|-----------|---------|
| EMPTY → SEATED | `session_start_from_empty` | ✅ unit |
| SEATED → PAYMENT_ACTIVE | `payment_activate_issues_token` | ✅ unit |
| PAYMENT_ACTIVE → CLOSED | `close_table_terminal` | ✅ unit |
| SEATED → EMPTY | `cancel_session` | ✅ unit |
| PAYMENT_ACTIVE → SEATED | `revoke_payment` | ✅ unit |

### 6.2 TableBillSettlement

| Transition | Test name | Phase 0 |
|------------|-----------|---------|
| BILL_DRAFT → ALLOCATION_OPEN | `activate_locks_bill_v1` | ✅ unit |
| ALLOCATION_OPEN → PARTIALLY_PAID | `partial_settlement` | ✅ unit |
| PARTIALLY_PAID → FULLY_PAID | `final_payment_zeros_remaining` | ✅ unit |
| * → VOID | `void_bill_pre_payment` | ✅ unit |

### 6.3 Claimant

| Transition | Test name | Phase 0 |
|------------|-----------|---------|
| JOINED → ALLOCATING | `claim_items` | ✅ unit |
| ALLOCATING → CHECKOUT_PENDING | `start_checkout` | ✅ unit |
| CHECKOUT_PENDING → PAID | `webhook_paid` | ✅ unit (mock) |

---

## 7. Mock server coverage matrix

| Flow | MSW | API stub (W2) | Real logic (MVP) |
|------|-----|---------------|------------------|
| A. Empty-table QR scan | W2-D6 | W2-D8-01 | M1 |
| B. Call server | W2-D6 | W2-D8-01 | M1 |
| C. Waiter start session | W2-D7 | W2-D8-03 | M1 |
| D. Join payment session | W2-D6 | W2-D8-04 | M1 |
| E. Item claiming | — | — | M2 |
| F–H. Split modes | — | — | M2 |
| I. Tip | — | — | M3 |
| J. Mollie checkout | — | — | M3 |

---

## 8. Risks and mitigations (Phase 0)

| Risk | Mitigation |
|------|------------|
| OpenAPI scope creep (loyalty/crypto routes) | Platform lead rejects paths not in MVP checklist |
| Prisma vs Drizzle debate | **Locked:** Prisma per [repo-structure.md](./repo-structure.md); revisit post-pilot only |
| MSW diverges from API | Contract snapshot tests on W2-D8-05 |
| Week 1 ui-core blocks apps | ws-4 delivers Button/Input/MoneyDisplay by Tue EOD |
| Mollie KYC not ready by M3 | Ops track starts Day 1; sandbox keys sufficient until M3 |

---

## 9. Daily sync agenda (15 min)

| Day | Question |
|-----|----------|
| Mon–Fri | Any cross-ws file edit needed? → ticket for owning ws |
| Wed | Migration ready for team? → ws-3 announces in `#dev` |
| Fri | Demo artifact link posted? → gate next week |

---

## 10. M0 exit gate checklist

**All must be checked before M1 Day 1:**

- [ ] `pnpm install && pnpm build && pnpm test` green on `main`
- [ ] Docker Compose Postgres + Redis documented in README
- [ ] OpenAPI v1 Spectral lint 0 errors
- [ ] `packages/db` migration + seed idempotent
- [ ] Split-engine: 6 worked examples + concurrency test pass
- [ ] State machine unit tests cover 100% documented transitions
- [ ] MSW: guest flows A–D navigable with mock
- [ ] MSW: staff session start + payment activate navigable
- [ ] API contract tests: guest table + staff session match MSW
- [ ] ui-core: 12 primitives in Storybook
- [ ] Guest + staff + admin apps boot (3 ports)
- [ ] CODEOWNERS matches ws-1–ws-4 map
- [ ] One Mollie test webhook received locally
- [ ] Platform lead sign-off on registry names vs entity dictionary

**Failure protocol:** Slip M1 start by 2 business days max; cut admin shell scope (tables CRUD moves to M2) before cutting contract quality.

---

*Slice: Part 18 — Phase 0 sprint plan. Owner: engineering roadmap slice.*
