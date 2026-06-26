# MVP Sprint Plan — 4 Weeks (M1–M4)

**Product:** Rekentafel  
**Duration:** 4 one-week sprints (Weeks 3–6)  
**Team:** ws-1 … ws-4 parallel  
**Parent:** [implementation-roadmap.md](./implementation-roadmap.md)  
**Prerequisite:** M0 exit gate from [sprint-plan-phase0.md](./sprint-plan-phase0.md)

---

## 1. Sprint principles

1. **Disjoint ownership** — each slice lists exclusive paths; violations revert same day
2. **Demo artifact required** — Friday recording or Playwright trace; no "merged but not demoable"
3. **Contract changes** — ws-3 only; announce in `#contracts-changelog` before merge
4. **MSW parity** — update `test-fixtures` same PR as API behavior change
5. **MVP boundary** — reject PRs touching crypto, loyalty wallet, discovery, POS sync scaffolds

---

## 2. Sprint overview

| Sprint | Week | Theme | Critical dependency |
|--------|------|-------|---------------------|
| **M1** | 3 | Session spine + realtime | Phase 0 API stubs |
| **M2** | 4 | Bill entry + claim engine | M1 session + token |
| **M3** | 5 | Mollie + webhooks + partial pay | M2 allocations |
| **M4** | 6 | Admin + overrides + audit + deploy | M3 payments |

---

## 3. M1 — Session spine (Week 3)

**Goal:** QR scan through waiter session control with real API and staff WebSocket.

### 3.1 Slices (disjoint ownership)

| Slice | WS | Scope | Files (exclusive) |
|-------|-----|-------|-------------------|
| **M1-S1** | ws-3 | Guest table context API; call-server; service signals persistence | `apps/api/src/modules/guest/`, `modules/signals/` |
| **M1-S2** | ws-3 | Dining session CRUD; payment activation; token hash storage | `apps/api/src/modules/session/`, `modules/token/` |
| **M1-S3** | ws-3 | Staff auth hardening; floor API; WebSocket desk | `modules/staff/`, `apps/api/src/ws/` |
| **M1-S4** | ws-1 | Guest landing, menu, call-server UX; guest-hooks integration | `apps/guest-web/`, `packages/guest-hooks/` |
| **M1-S5** | ws-2 | Staff login, floor grid, session controls, signals inbox | `apps/staff-web/`, `packages/staff-hooks/` |
| **M1-S6** | ws-4 | SSE guest endpoint hardening; CI e2e job; staging Fly app | `infra/`, `.github/workflows/` |

**No-go files this sprint:** `modules/bill/`, `modules/claim/`, `modules/payment/`, `admin-web/routes/menu/`

### 3.2 Daily breakdown

| Day | ws-3 | ws-1 | ws-2 | ws-4 |
|-----|------|------|------|------|
| Mon | M1-S1 guest routes + DB writes | Landing page + menu fetch | Login form + auth cookie | Staging Fly.toml |
| Tue | M1-S2 session state machine HTTP | Call-server button + toast | Floor grid live data | CI: Playwright install |
| Wed | M1-S3 WS + signals push | QR deep link `#ps=` handling stub | Start session flow | Deploy staging API |
| Thu | Contract tests + MSW sync | Empty vs seated UI states | Activate payment UI (token display) | e2e smoke wired |
| Fri | Bugfix buffer | **Demo:** guest flows A–B | **Demo:** flows C + signals | Staging URL posted |

### 3.3 M1 exit criteria

| Criterion | Verification |
|-----------|--------------|
| QR `https://app.rekentafel.nl/t/de-rekentafel-pilot/t-12` shows menu, table label | Manual + Playwright |
| Empty/seated scan returns **no bill lines** | API assertion test |
| Waiter starts session → state SEATED | Staff UI + DB row |
| Call-server creates signal → staff WS push <2s | Integration test |
| Activate payment → PAYMENT_ACTIVE + token issued | API response includes `join_url` |
| Token without activation → 403 on bill endpoints | Security test |

### 3.4 M1 demo artifact

**Record:** `m1-session-spine-demo.webm`

1. Guest scans QR → menu (Table 12)
2. Guest taps "Call server"
3. Waiter sees signal on floor grid
4. Waiter starts session → activates payment mode
5. Copy join URL — bill endpoint still 403 until guest joins with token (bill empty OK)

**Playwright:** `apps/guest-web/tests/e2e/empty-table.spec.ts`, `call-server.spec.ts`, `apps/staff-web/tests/e2e/session-start.spec.ts`

---

## 4. M2 — Bill entry + claim engine (Week 4)

**Goal:** Waiter enters bill; guests join, claim, split; remaining balance updates via SSE.

### 4.1 Slices

| Slice | WS | Scope | Files |
|-------|-----|-------|-------|
| **M2-S1** | ws-3 | Bill CRUD; VAT validation; bill version lock on payment open | `modules/bill/`, `domain/vat/` |
| **M2-S2** | ws-3 | Allocatable units generation; claim API; optimistic locking | `modules/claim/`, `domain/split-engine/` |
| **M2-S3** | ws-3 | Guest join participant; SSE bill events | `modules/guest/pay/`, `sse/bill-events.ts` |
| **M2-S4** | ws-2 | Bill editor UI; CSV import; payment monitor | `staff-web/.../bill/`, `features/bill-entry/` |
| **M2-S5** | ws-1 | Join lobby; claim UI; equal/custom/shared flows | `guest-web/routes/pay/**` |
| **M2-S6** | ws-4 | `BillLineRow`, `ClaimSheet`, `SplitPreview` in ui-core or guest components | `guest-web/components/`, ui-core review |

### 4.2 Numeric acceptance scenario (mandatory demo)

**Table 12, 4 guests, bill €105.60 ex-VAT display** (from [mvp-roadmap.md](../product/mvp-roadmap.md)):

| Line | Qty | Unit | VAT | Total |
|------|-----|------|-----|-------|
| Burger | 2 | €14.50 | 9% | €29.00 |
| Steak | 1 | €28.00 | 9% | €28.00 |
| House wine | 1 | €32.00 | 21% | €32.00 |
| Cola | 2 | €3.50 | 9% | €7.00 |
| Service charge 10% | — | — | 9% | €9.60 |

**Allocation demo:**

| Guest | Action | Subtotal + VAT share |
|-------|--------|----------------------|
| A | 1 burger + 1 cola | €18.00 + VAT |
| B | Steak + ½ wine (shared) | €42.00 + VAT |
| C, D | Equal split remainder | €30.10 each |

### 4.3 M2 exit criteria

| Criterion | Verification |
|-----------|--------------|
| Bill entry validates VAT sum before payment open | API 422 on mismatch |
| Concurrent claim on same unit → one 409 | Concurrency integration test |
| Shared item split N-way | UI + API |
| Equal split subset (2 of 4) | Demo script |
| Custom € amount split with validation | Cannot exceed unclaimed |
| SSE pushes remaining balance on claim | Guest B sees update <1s |
| Bill hidden pre-token; visible post-join | Regression test |

### 4.4 M2 demo artifact

**Record:** `m2-split-without-pay-demo.webm` + **Playwright:** `claim-concurrent.spec.ts`

**Wednesday integration smoke:** First full stack guest+staff against staging (`VITE_API_MOCK=false`).

---

## 5. M3 — Mollie + webhooks + partial pay (Week 5)

**Goal:** Real money in sandbox; partial table settlement; reconciliation trail.

### 5.1 Slices

| Slice | WS | Scope | Files |
|-------|-----|-------|-------|
| **M3-S1** | ws-3 | Checkout intent; Mollie adapter; payment create | `modules/payment/`, `adapters/mollie/` |
| **M3-S2** | ws-3 | Webhook ingress; reconcile worker; idempotency | `modules/webhooks/`, `apps/worker/queues/webhook-reconcile.ts` |
| **M3-S3** | ws-3 | Partial pay aggregation; settlement state transitions | `domain/split-engine/settlement.ts` HTTP |
| **M3-S4** | ws-1 | Tip UI; Mollie redirect; return handler; trust banner | `routes/pay/tip/`, `features/mollie-redirect/` |
| **M3-S5** | ws-2 | Payment monitor; remaining balance; mark cash (optional) | `features/payment-monitor/` |
| **M3-S6** | ws-4 | Webhook tunnel staging; secrets; payment e2e CI job | `infra/`, CI |

### 5.2 Payment flow sequence (M3 must implement)

```
Guest confirms allocation + tip
  → POST /v1/guest/checkout-intents (Idempotency-Key)
  → payment_intent CREATING → MOLLIE_OPEN
  → redirect Mollie hosted checkout
  → iDEAL sandbox pay
  → webhook POST /v1/webhooks/mollie
  → worker: payment_intent PAID, confirmed_paid_cents +=
  → SSE TablePartiallyPaid
  → guest return URL shows success; remaining bar updated
```

### 5.3 Partial pay scenario (mandatory demo)

Same Table 12 after M2 allocations:

| Guest | Pays | Tip | Mollie status |
|-------|------|-----|---------------|
| A | €21.50 | €2.00 | paid |
| B | — | — | (pays Friday demo) |
| C, D | — | — | remaining visible |

**After A pays:** `remaining_cents` = total − €21.50; table state PARTIALLY_PAID.

### 5.4 M3 exit criteria

| Criterion | Verification |
|-----------|--------------|
| Sandbox iDEAL payment succeeds | `tr_*` in Mollie dashboard |
| Duplicate webhook → single payment row | Replay test |
| Failed payment releases claim lock after 15 min | Job + test |
| Guest return before webhook → UI resolves via poll then SSE | E2E test |
| `confirmed_paid_cents` matches Mollie amount | Reconciliation query |
| Crypto endpoint returns 501 | Route test |

### 5.5 M3 demo artifact

**Record:** `m3-partial-pay-demo.webm`

**Ops artifact:** Screenshot reconciliation mapping `tr_test_xxx` → `participant_id` → allocation snapshot JSON

---

## 6. M4 — Admin + overrides + audit + pilot deploy (Week 6)

**Goal:** Pilot venue operable without engineering; full integration; production deploy.

### 6.1 Slices

| Slice | WS | Scope | Files |
|-------|-----|-------|-------|
| **M4-S1** | ws-2 | Admin: tables, QR PDF, menu CRUD, staff invites | `apps/admin-web/` |
| **M4-S2** | ws-2 | Waiter override flows; force close; dispute UI | `staff-web/.../overrides/` |
| **M4-S3** | ws-3 | Audit log writes; export API; GDPR purge job stub | `modules/audit/`, `worker/gdpr-purge.ts` |
| **M4-S4** | ws-3 | Mollie API key config (encrypted); service charge settings API | `modules/admin/settings/` |
| **M4-S5** | ws-1 | Payment result/receipt; error states; trust copy NL | `routes/pay/result/`, PaymentTrustBanner |
| **M4-S6** | ws-4 | Production deploy; runbook; pilot seed on prod | `infra/`, `deploy-production.yml` |

### 6.2 Integration window (Mon–Wed Week 6)

See [implementation-roadmap.md](./implementation-roadmap.md) §7. All flows I-1 through I-8 must pass on staging.

### 6.3 M4 exit criteria

| Criterion | Verification |
|-----------|--------------|
| Manager generates table QR PDF | Printable PDF with correct slug |
| Menu edit reflects on guest empty-table within 60s | Manual |
| Waiter override reassigns claimed item | Audit entry created |
| Force close with unpaid remainder | Table CLOSED + incident flag |
| Audit export JSON for one session | Download from admin |
| Production deploy successful | `api.rekentafel.nl/health` |
| Pilot venue walkthrough with waiter script | Signed checklist |

### 6.4 M4 demo artifact

**Record:** `m4-pilot-ready-demo.webm` — full flow A→J including override + close

**Playwright suite:** `e2e/pilot-happy-path.spec.ts` (all green on staging)

**Deliverable:** Pilot go-live runbook executed; Mollie **live** keys ready (or scheduled Day 1 pilot)

---

## 7. Cross-sprint dependency table

| Consumer | Depends on | Sprint |
|----------|------------|--------|
| ws-1 guest pay UI | ws-3 payment API | M3 |
| ws-1 claim UI | ws-3 claim API + SSE | M2 |
| ws-2 bill editor | ws-3 bill API | M2 |
| ws-2 payment monitor | ws-3 SSE/WS + payment state | M3 |
| ws-3 Mollie | Pilot Mollie test org | P0 ops |
| All | ws-4 ui-core primitives | P0 |
| All | ws-3 contracts | P0 |

---

## 8. Post-MVP backlog (do not pull into M1–M4)

| Item | Tag | Earliest |
|------|-----|----------|
| Guest accounts + visit history | V1.1 | After M5 |
| POS CSV scheduled import | V1.1 | After M5 |
| Geo proximity join gate | V1.1 | After fraud review |
| Mollie Connect platform fees | V2 | Legal + 10 venues |
| Crypto checkout | V2+ | Legal memo |
| Loyalty earn/burn | V2 | Venue-only points |
| Discovery feed | Never early | — |

---

## 9. Sprint risk flags

| Sprint | Risk | Mitigation |
|--------|------|------------|
| M1 | WebSocket auth leaks token | Short-lived WS ticket; audit |
| M2 | VAT rounding disputes | Show per-guest VAT breakdown |
| M2 | Bill hijacking | Join requires payment token |
| M3 | Webhook ordering | Idempotency store; outbox pattern |
| M3 | Mollie redirect UX on slow 3G | Loading state + poll timeout copy |
| M4 | Admin scope creep | Menu + tables only; no ops dashboard |
| M4 | Pilot waiter training | Rehearsal Thu; 60s tutorial video |

---

## 10. Definition of Done (every slice)

- [ ] Code merged to `main` via PR with CODEOWNERS approval
- [ ] Unit/integration tests added; CI green
- [ ] MSW handlers updated if API changed
- [ ] No edits outside slice file ownership
- [ ] Demo artifact linked in PR description
- [ ] `NEW_REGISTRY_ENTRIES` block if new canonical names added

---

*Slice: Part 18 — MVP sprint plan. Owner: engineering roadmap slice.*
