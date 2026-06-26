# Idempotency and Concurrency

**Product (working name):** Rekentafel  
**Slice:** Part 10 — API / Backend Design  
**Stack:** PostgreSQL (authoritative), Redis (ephemeral locks + idempotency cache)  
**Cross-references:** [domain/split-engine/concurrency.md](../../domain/split-engine/concurrency.md), [service-map.md](./service-map.md), [auth-and-sessions.md](./auth-and-sessions.md)

---

## 1. Design principles

| Principle | Implementation |
|-----------|----------------|
| PostgreSQL is source of truth | Row versioning, constraints, transactions |
| Redis is optimization | Short TTL locks; safe degradation to `SELECT FOR UPDATE` |
| All payment mutations idempotent | Client header + server webhook keys |
| At-least-once delivery | Outbox + webhook retry; consumers dedupe |
| Fail closed on conflict | `409` / `422` / `423` — never silent merge |

**MVP target:** Zero double-allocation under 50 concurrent claim attempts on one `AllocatableUnit`.

---

## 2. Idempotency key specification

### 2.1 Client-supplied (`Idempotency-Key` header)

**Required on all mutating guest and staff endpoints that create financial or allocation state.**

| Endpoint | Required | Scope |
|----------|----------|-------|
| `POST /payment-sessions/join` | Recommended | Per device |
| `POST /payment-sessions/{id}/claims` | **Required** | Per user action |
| `PATCH /payment-sessions/{id}/claims/{id}` | **Required** | Per user action |
| `DELETE /payment-sessions/{id}/claims/{id}` | **Required** | Per user action |
| `POST /payment-sessions/{id}/splits/equal` | **Required** | Per user action |
| `POST /payment-sessions/{id}/splits/custom` | **Required** | Per user action |
| `POST /payment-sessions/{id}/checkout` | **Required** | Per user action |
| `POST /payment-sessions/{id}/tips` | **Required** | Per user action |
| `POST /staff/.../bills` | **Required** | Per staff action |
| `POST /staff/.../overrides` | **Required** | Per staff action |
| `POST /staff/.../payment-sessions` | **Required** | Per staff action |

**Format:** UUID v4 (36 chars). **One key per intentional user action** — not rotated on network retry of same action.

**Storage:**

```sql
CREATE TABLE idempotency_keys (
  idempotency_key   TEXT NOT NULL,
  endpoint          TEXT NOT NULL,
  request_hash      TEXT NOT NULL,  -- SHA256 of normalized body
  response_status   INT NOT NULL,
  response_body     JSONB NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at        TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (idempotency_key, endpoint)
);
CREATE INDEX idx_idempotency_expires ON idempotency_keys (expires_at);
```

**TTL:** 24 hours.

**Behavior:**

| Case | HTTP | Body |
|------|------|------|
| New key | Process normally | 2xx/4xx result |
| Same key + same body hash | Return cached | Same as first |
| Same key + different body hash | Reject | `422 IDEMPOTENCY_KEY_REUSED` |

**Redis fast path:** `idempotency:{endpoint}:{key}` → cached response JSON, TTL 24h. DB is durable fallback.

### 2.2 Server-generated keys (webhooks / workers)

| Event | Key format | Storage |
|-------|------------|---------|
| Mollie paid | `mollie:payment:{mollie_payment_id}:paid` | `processed_webhooks` PK |
| Mollie failed | `mollie:payment:{mollie_payment_id}:failed` | PK |
| Mollie expired | `mollie:payment:{mollie_payment_id}:expired` | PK |
| Mollie canceled | `mollie:payment:{mollie_payment_id}:canceled` | PK |
| Refund completed | `mollie:refund:{refund_id}:completed` | PK |
| Outbox delivery | `outbox:{event_id}` | Consumer offset |

```sql
CREATE TABLE processed_webhooks (
  idempotency_key   TEXT PRIMARY KEY,
  mollie_payment_id TEXT,
  payload           JSONB NOT NULL,
  processed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Webhook handler pattern:**

```sql
INSERT INTO processed_webhooks (idempotency_key, mollie_payment_id, payload)
VALUES ($key, $id, $payload)
ON CONFLICT DO NOTHING
RETURNING idempotency_key;
-- 0 rows → already processed → return 200 no-op
```

### 2.3 Checkout composite key (internal)

Prevents double Mollie payment on double-tap:

```
checkout_idempotency = SHA256(
  participant_id + ":" +
  allocation_snapshot_hash + ":" +
  tip_cents + ":" +
  checkout_attempt
)
```

- `allocation_snapshot_hash` = sorted allocation IDs + amounts at lock time
- Within 15-minute checkout lock window, same composite returns same Mollie `checkout_url` if status still `MOLLIE_OPEN`

**Also stored in Mollie metadata:** `idempotency_key: pi_abc_v1`

---

## 3. Redis lock catalog

### 3.1 Key schema

| Key pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `claim:lock:{bill_id}:{unit_id}` | `{participant_id}:{payment_session_id}` | **30s** | Serialize unit claim |
| `checkout:lock:{bill_id}:{participant_id}` | `{checkout_id}` | **15m** | One active checkout per guest |
| `bill:split:lock:{bill_id}` | `{request_id}` | **10s** | Equal-split batch |
| `bill:admin:lock:{bill_id}` | `{staff_user_id}` | **60s** | Waiter override batch |
| `idempotency:{endpoint}:{key}` | response JSON | **24h** | Fast idempotency cache |
| `join:pin_attempts:{payment_session_id}` | counter | **15m** | Brute-force PIN limit |
| `signal:cooldown:{table_id}:{device_id}` | `1` | **60s** | Service signal rate limit |

### 3.2 Claim lock algorithm

```
claimUnit(bill_id, unit_id, participant_id, payment_session_id, idempotency_key):

  1. Check idempotency cache → return if hit

  2. SET claim:lock:{bill_id}:{unit_id} {participant_id}:{ps_id} NX EX 30
     → FAIL: return 409 UNIT_LOCKED { retry_after_ms: 500 }

  3. BEGIN TRANSACTION

  4. Verify bill_version unchanged (optimistic)

  5. Verify TableBillSettlement.state IN (ALLOCATION_OPEN)
     → else 423 CLAIMS_FROZEN

  6. Verify participant not CHECKOUT_LOCKED
     → else 423 CHECKOUT_IN_PROGRESS

  7. SELECT allocation FOR unit WHERE released_at IS NULL
     → if owned by other: ROLLBACK, release lock, 409 UNIT_UNAVAILABLE

  8. INSERT/UPDATE allocation; validate SHARED sum ≤ 1.0

  9. COMMIT

  10. DEL claim lock (Lua compare-and-delete)

  11. Cache idempotency response

  12. Emit claim.created
```

**Lua unlock (prevent lock stealing):**

```lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
else
  return 0
end
```

### 3.3 Redis degradation

If Redis unavailable:

| Operation | Fallback |
|-----------|----------|
| Claim lock | `SELECT ... FROM allocatable_units WHERE id = $1 FOR UPDATE` |
| Idempotency | DB-only `idempotency_keys` table |
| Checkout lock | DB unique partial index on `(bill_id, participant_id) WHERE checkout_active` |
| Rate limit | In-memory per instance (weaker) + log alert |

**Alert:** `redis_unavailable` → page if > 60s.

---

## 4. Optimistic locking (PostgreSQL)

### 4.1 Bill version

Every bill mutation increments `bill_version`. Allocations store `(bill_id, bill_version_at_claim)`.

```sql
UPDATE bills
SET bill_version = bill_version + 1,
    updated_at = now()
WHERE id = $bill_id AND bill_version = $expected_version;
-- rows_affected = 0 → 409 BILL_VERSION_STALE
```

**Client must send:** `If-Match: "bill_version:12"` or body field `bill_version: 12`.

**Waiter `BUMP_BILL_VERSION`:** Invalidates all allocations where claimant not `PAID`.

### 4.2 Allocation row version

```sql
UPDATE allocations
SET amount_cents = $amount,
    version = version + 1,
    updated_at = now()
WHERE id = $id
  AND version = $expected_version
  AND released_at IS NULL;
```

### 4.3 DB constraints (hard invariants)

```sql
-- One active owner per discrete unit (ITEM mode)
CREATE UNIQUE INDEX idx_allocation_unit_active
  ON allocations (unit_id)
  WHERE released_at IS NULL AND split_mode = 'ITEM';

-- Payment record uniqueness
CREATE UNIQUE INDEX idx_payment_mollie_id
  ON payment_records (mollie_payment_id)
  WHERE mollie_payment_id IS NOT NULL;

CREATE UNIQUE INDEX idx_payment_idempotency
  ON payment_records (idempotency_key);
```

**SHARED mode:** No unique on unit — enforce `sum(shares) ≤ 1.0` in transaction with `FOR UPDATE` on parent unit row.

---

## 5. Conflict resolution matrix

| Scenario | Detection | HTTP | Error code | Client UX |
|----------|-----------|------|------------|-----------|
| Same unit, two claimants | Redis + DB unique | 409 | `UNIT_UNAVAILABLE` | "Taken by {nickname}" |
| SHARED over 100% | Transaction check | 422 | `SHARE_OVERFLOW` | Show available % |
| Stale `bill_version` | Optimistic check | 409 | `BILL_VERSION_STALE` | Refresh bill |
| Claim during checkout lock | Claimant state | 423 | `CHECKOUT_IN_PROGRESS` | "Complete or cancel payment" |
| Claims while frozen | Bill state | 423 | `CLAIMS_FROZEN` | "Waiter paused splitting" |
| Duplicate idempotency key | Cache/DB | 200 | — | Same result |
| Duplicate webhook | `processed_webhooks` | 200 | — | No-op |
| Equal split + active checkout | Pre-check | 423 | `CHECKOUT_BLOCKS_SPLIT` | List blocking participants |
| Custom pledge overflow | Sum validation | 422 | `PLEDGE_EXCEEDS_REMAINING` | Show max |
| Join PIN brute force | Redis counter | 429 | `PIN_LOCKED` | Wait 30 min |
| Staff override during iDEAL | Admin lock + cancel | — | — | Cancel open Mollie payment |

---

## 6. Checkout and payment races

### 6.1 Checkout start sequence

```
1. Verify participant state ∈ {JOINED, ALLOCATING, PAYMENT_FAILED}
2. SET checkout:lock:{bill_id}:{participant_id} NX EX 900
3. Snapshot allocations → immutable CheckoutIntent
4. Compute amount_cents (share + tip) via Split Engine
5. INSERT payment_record status=CREATING
6. POST Mollie /v2/payments (OAuth restaurant token)
7. UPDATE payment_record status=MOLLIE_OPEN, store tr_xxx
8. UPDATE participant state → PAYMENT_PENDING
9. On Mollie 5xx: DEL checkout lock, status=FAILED_CREATE, retry same idempotency key
```

### 6.2 Webhook vs concurrent claim

| Phase | Other guests can claim? |
|-------|-------------------------|
| Claimant `PAYMENT_PENDING` | Yes — unclaimed units only |
| `ALLOCATION_FROZEN` | No |
| Claimant's own allocations | Immutable until fail/expire |

### 6.3 Webhook vs webhook

`processed_webhooks` PK ensures `confirmed_paid_cents` increments once:

```sql
-- Single transaction:
INSERT processed_webhooks ... ON CONFLICT DO NOTHING RETURNING ...;
UPDATE bill_settlements
SET confirmed_paid_cents = confirmed_paid_cents + $amount,
    remaining_cents = bill_grand_total_cents - (confirmed_paid_cents + $amount),
    state = CASE WHEN ... THEN 'FULLY_PAID' ELSE 'PARTIALLY_PAID' END
WHERE bill_id = $id;
UPDATE payment_records SET status = 'PAID' WHERE mollie_payment_id = $id;
UPDATE participants SET state = 'PAID' WHERE id = $participant_id;
```

### 6.4 Late webhook after force close

Table `CLOSED` but webhook `paid` arrives:

1. Record payment (funds received — legal obligation)
2. Set `payment_records.orphan_payment = true`
3. Do **not** reopen bill automatically (MVP)
4. Emit ops alert → reconciliation queue

### 6.5 Return URL vs webhook race

Guest hits `redirectUrl` before webhook:

```
GET /v1/checkout/{checkout_id}/status
→ Poll Mollie once if local status = MOLLIE_OPEN
→ Return current status; UI shows "Confirming..."
→ Webhook remains source of truth for ledger
```

Never double-fulfill: status transition guarded by `payment_records.status = MOLLIE_OPEN`.

---

## 7. Waiter override serialization

```
1. Verify staff role ≥ manager OR override code authorized for waiter
2. SET bill:admin:lock:{bill_id} NX EX 60
3. For each affected participant with checkout lock:
   a. Cancel Mollie payment if status=open (API call)
   b. DEL checkout:lock:{bill_id}:{participant_id}
4. Apply allocation changes in single transaction
5. BUMP bill_version if line edits included
6. INSERT audit_events (reason_code, staff_id)
7. DEL admin lock
8. Push bill_updated via SSE/WebSocket
```

**Bypass:** Staff override ignores guest `claim:lock:*` keys.

---

## 8. Remaining balance atomicity

| Metric | Update trigger | Lock |
|--------|----------------|------|
| `allocated_cents` | Claim commit | Bill row `FOR UPDATE` optional |
| `confirmed_paid_cents` | Webhook only | Settlement row + idempotency |
| `remaining_cents` | Derived in same webhook txn | — |
| `unclaimed_cents` | Claim release/create | Computed or materialized view refresh |

**Close gate uses `remaining_cents`**, not `unclaimed_cents`. Table can have unclaimed items but zero remaining if waiter marked cash.

---

## 9. Numeric example — concurrent claim

**Bill line:** 2× Burger @ €14.50 = €29.00 → 2 `AllocatableUnit`s (u1, u2)

| Time | Guest | Action | Result |
|------|-------|--------|--------|
| T+0ms | Anna | Claim u1 | 200 OK |
| T+5ms | Boris | Claim u1 | 409 `UNIT_UNAVAILABLE` (Anna) |
| T+10ms | Boris | Claim u2 | 200 OK |
| T+15ms | Carla | Claim u1 (retry) | 409 |
| T+20ms | Carla | Claim u2 | 409 (Boris) |

**Result:** Exactly one owner per unit; 49/50 failures in load test acceptable.

---

## 10. Audit logging (concurrency-relevant fields)

Every mutating request logs:

| Field | Example |
|-------|---------|
| `request_id` | `req_01J...` |
| `idempotency_key` | `550e8400-...` |
| `bill_version` | `12` |
| `unit_id` | `uuid` |
| `outcome` | `success \| conflict \| stale` |
| `lock_wait_ms` | `23` |
| `redis_fallback` | `false` |

Retention: 7 years for payment-adjacent; indexed by `(restaurant_id, payment_session_id, occurred_at)`.

---

## 11. Testing requirements (MVP gate)

| Test | Method | Pass |
|------|--------|------|
| 50 concurrent claims, 1 unit | k6 / Jest | 1× 200, 49× 409 |
| Duplicate idempotency key | Repeat POST | Same body, 1 DB row |
| Webhook double delivery | Replay payload | `confirmed_paid_cents` +1 once |
| Checkout double-tap | Parallel POST | 1 Mollie `tr_*` |
| Equal split + claim race | Parallel | One wins |
| Redis down | Disable Redis | Claims still safe via DB |
| Stale bill_version mid-checkout | Bump during checkout | 409 at pay click |

---

## 12. Observability and alerts

| Metric | Threshold | Action |
|--------|-----------|--------|
| `claim_conflict_rate` | >15% per session | UX review |
| `409_rate` spike | 3× baseline | Possible hijack / confusion |
| `orphan_payment_count` | >0 | Ops queue |
| `redis_lock_wait_ms` p99 | >500ms | Scale Redis |
| `idempotency_replay_count` | — | Baseline tracking |
| `webhook_lag_seconds` | >120s | Worker scaling |

---

## 13. MVP vs post-MVP

| Capability | MVP | V1.1+ |
|------------|-----|-------|
| Redis claim lock 30s | ✓ | Configurable per venue |
| Serializable SHARED txs | ✓ (`FOR UPDATE`) | — |
| SSE bill sync | Best effort | Guaranteed ordering |
| Redlock multi-node | Single Redis | V2 cluster |
| Fraud velocity (IP) | Basic rate limit | Geo heuristics |
| Geo proximity lock | — | Optional join gate |
| Automatic bill reopen on orphan | — | Manager tool |

---

## 14. Risks

| Risk | Mitigation |
|------|------------|
| Redis split-brain | TTL auto-expire; DB fallback |
| Lost lock without release | 30s TTL |
| Idempotency cache eviction | DB unique constraint |
| Override during active iDEAL | Cancel Mollie + release lock |
| Clock skew | Server-side TTL only |
| EMI via idempotency replay crediting | Keys bound to exact amount in hash |

---

*Slice ownership: Part 10 — API / Backend Design.*
