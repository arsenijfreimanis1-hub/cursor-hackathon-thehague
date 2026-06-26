# Bill-Splitting Concurrency Strategy

**Slice:** Part 5 — Bill-Splitting Logic  
**Stack assumption:** TypeScript API, PostgreSQL (source of truth), Redis (ephemeral locks)  
**Related:** [rules-spec.md](./rules-spec.md), [state-machines.md](./state-machines.md)

---

## 1. Problem statement

Multiple guests join the same `PaymentSessionToken` session and concurrently:

- Claim the same `AllocatableUnit` (ITEM mode)
- Add shares on the same SHARED line (sum must stay ≤ 100%)
- Start checkout while others edit claims
- Receive duplicate Mollie webhooks

**Failure mode without locking:** Double-allocation → `sum(allocations) > bill_total` → merchant and guest financial discrepancy.

**MVP target:** Zero double-allocation in concurrent integration tests (≥50 parallel claim attempts on 1 unit).

---

## 2. Architecture overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Guest client│────►│ Split API        │────►│ PostgreSQL  │
└─────────────┘     │ (optimistic +    │     │ allocations │
                    │  Redis lock)     │     │ bill_version│
                    └────────┬─────────┘     └─────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Redis            │
                    │ claim_lock:{unit}│
                    │ checkout_lock    │
                    └──────────────────┘
                             ▲
                    ┌────────┴─────────┐
                    │ Mollie webhooks  │
                    │ (idempotent)     │
                    └──────────────────┘
```

**Principle:** PostgreSQL row versioning is authoritative; Redis provides short TTL mutual exclusion for hot units.

---

## 3. Optimistic locking (bill snapshot)

### 3.1 Bill version

Every bill mutation increments `bill_version`. Allocation rows store `(bill_id, bill_version)`.

| Operation | Check |
|-----------|-------|
| Create allocation | `client.bill_version == server.bill_version` |
| Start checkout | Same + allocation rows still owned by claimant |
| Waiter `BUMP_BILL_VERSION` | Deletes/invalidates allocations where `payment_status ≠ PAID` |

**SQL pattern:**

```sql
UPDATE bills
SET bill_version = bill_version + 1, updated_at = now()
WHERE id = $bill_id AND bill_version = $expected_version;
-- if rows_affected = 0 → 409 BILL_VERSION_STALE
```

### 3.2 Allocation row versioning

Each `allocation` has `version` (integer). Updates use:

```sql
UPDATE allocations
SET claimant_id = $new, version = version + 1
WHERE id = $id AND version = $expected AND released_at IS NULL;
```

---

## 4. Redis claim locks

### 4.1 Key schema

| Key | Value | TTL |
|-----|-------|-----|
| `claim:lock:{bill_id}:{unit_id}` | `{claimant_id}:{session_id}` | **30 seconds** |
| `checkout:lock:{bill_id}:{claimant_id}` | `{checkout_intent_id}` | **15 minutes** |
| `idempotency:{key}` | response payload hash | **24 hours** |

### 4.2 Claim algorithm (ITEM / SHARED)

```
function claimUnit(billId, unitId, claimantId, sessionId, idempotencyKey):

  1. IDEMPOTENCY: if idempotency:{key} exists → return cached response

  2. ACQUIRE Redis SET claim:lock:{billId}:{unitId} NX EX 30
     - if FAIL → read holder; return 409 UNIT_LOCKED (retry_after_ms)

  3. BEGIN DB transaction

  4. SELECT allocation FOR unitId WHERE released_at IS NULL
     - if exists AND owner ≠ claimantId → ROLLBACK; release Redis; 409 UNIT_UNAVAILABLE

  5. INSERT or UPDATE allocation (validate share sum ≤ 1 for SHARED)

  6. COMMIT

  7. RELEASE Redis lock (Lua: delete if value matches)

  8. CACHE idempotency response 24h

  9. RETURN 200 + allocation
```

**Lua unlock (prevent stealing):**

```lua
if redis.call("get", KEYS[1]) == ARGV[1] then
  return redis.call("del", KEYS[1])
else
  return 0
end
```

### 4.3 TTL rationale

| TTL | Reason |
|-----|--------|
| 30s claim | Covers slow mobile; auto-release on crash |
| 15m checkout | Mollie iDEAL redirect + bank auth; matches payment retry window |

**Post-MVP:** Configurable per venue (V1.1).

---

## 5. Idempotency keys

### 5.1 Client-supplied keys (required on mutating endpoints)

| Endpoint | Idempotency-Key header |
|----------|------------------------|
| `POST /claims` | Required |
| `POST /checkout` | Required |
| `DELETE /claims/{id}` | Required |
| `POST /equal-split` | Required |

**Format:** UUID v4; one key per user action (not per retry of same action).

### 5.2 Server-generated keys (webhooks)

| Event | Key |
|-------|-----|
| Mollie `paid` | `mollie:payment:{payment_id}:paid` |
| Mollie `failed` | `mollie:payment:{payment_id}:failed` |

Store in `processed_webhooks(idempotency_key PRIMARY KEY)`.

### 5.3 Checkout idempotency namespace

Composite: `{claimant_id}:{allocation_snapshot_hash}:{checkout_attempt}`

- `allocation_snapshot_hash` = SHA256 of sorted allocation IDs + amounts at lock time
- Within 15m window, same key returns same Mollie payment URL (if still `open`)

**Prevents:** Double Mollie payment creation on double-tap "Pay".

---

## 6. Conflict resolution matrix

| Scenario | Detection | HTTP | Client UX |
|----------|-----------|------|-----------|
| Same unit, two claimants | Redis + DB unique `(unit_id) WHERE active` | 409 | "Taken by {nickname}" |
| SHARED over 100% | DB constraint `sum(shares) ≤ 1` | 422 | Show available % |
| Stale bill_version | Optimistic check | 409 | Refresh bill |
| Claim during checkout lock | `claimant.state = CHECKOUT_LOCKED` | 423 | "Complete or cancel payment" |
| Edit during `ALLOCATION_FROZEN` | Bill state | 423 | "Waiter paused splitting" |
| Duplicate idempotency | Redis/DB cache | 200 | Same result (no double) |
| Webhook retry | `processed_webhooks` | — | No-op |

**Waiter override:** Bypasses Redis claim lock via `staff_override=true` flag; acquires `bill:admin:lock:{bill_id}` (60s TTL) to serialize admin ops.

---

## 7. SHARED line concurrency

Shared lines use **fractional share rows** with constraint:

```sql
CHECK (share_numerator > 0 AND share_denominator <= 20);
-- aggregate: sum(numerator::float / denominator) <= 1.0 per unit
```

**Commit order:** Transaction serializable isolation **or** row lock on `allocatable_units` parent:

```sql
SELECT * FROM allocatable_units WHERE id = $unit FOR UPDATE;
```

Then validate sum before insert.

**Race:** Two guests add 60% + 50% → second transaction fails `422 SHARE_OVERFLOW`.

---

## 8. Equal split concurrency

`POST /equal-split` is a **batch operation**:

1. Acquire `bill:split:lock:{bill_id}` Redis NX EX 10s
2. Verify no overlapping `CHECKOUT_LOCKED` claimants in target set
3. Compute shares in single transaction
4. Insert allocations with shared `equal_group_id`
5. Release lock

Only one equal-split operation per bill at a time (10s lock).

---

## 9. Checkout + payment race conditions

### 9.1 Checkout start

```
1. Verify claimant not CHECKOUT_LOCKED (or same intent retry)
2. SET checkout:lock:{billId}:{claimantId} NX EX 900
3. Snapshot allocations → CheckoutIntent (immutable)
4. Create Mollie payment
5. On Mollie API failure → DEL checkout lock; state PAYMENT_FAILED
```

### 9.2 Webhook vs claim edit

While `PAYMENT_PENDING`:
- Allocations for that claimant are **immutable**
- Other claimants may still claim unclaimed units (unless `ALLOCATION_FROZEN`)

### 9.3 Webhook vs webhook

`processed_webhooks` PK prevents double increment of `confirmed_paid_cents`.

```sql
INSERT INTO processed_webhooks (idempotency_key, payload)
VALUES ($key, $payload)
ON CONFLICT DO NOTHING
RETURNING id;
-- if no row returned → already processed → 200 OK no-op
```

### 9.4 Late webhook after force close

If table `CLOSED` but webhook `paid` arrives:
- Still record payment (funds received)
- Flag `orphan_payment` for ops reconciliation
- Do **not** reopen bill automatically (MVP)

---

## 10. Remaining balance updates

**Atomic increment:**

```sql
UPDATE bill_settlements
SET confirmed_paid_cents = confirmed_paid_cents + $amount,
    remaining_cents = bill_grand_total_cents - (confirmed_paid_cents + $amount),
    state = CASE
      WHEN bill_grand_total_cents - (confirmed_paid_cents + $amount) = 0 THEN 'FULLY_PAID'
      ELSE 'PARTIALLY_PAID'
    END
WHERE bill_id = $id;
```

Use single transaction with webhook idempotency insert.

---

## 11. Unclaimed pool consistency

Materialized view or computed:

```
unclaimed_cents = bill_grand_total_cents
  - SUM(active_allocations.amount_cents)
```

**Not** `grand_total - confirmed_paid` — those differ when guests allocated but not paid.

| Metric | Formula |
|--------|---------|
| `unclaimed_cents` | Allocations not committed |
| `remaining_cents` | Unpaid portion of bill |
| `outstanding_allocated` | Allocated but not paid |

Close gate uses `remaining_cents`, not `unclaimed_cents`.

---

## 12. Waiter override serialization

| Lock | TTL | Purpose |
|------|-----|---------|
| `bill:admin:lock:{bill_id}` | 60s | Single writer for override batch |
| Bypass guest claim locks | — | Staff role flag |

Override transaction:
1. Acquire admin lock
2. Release affected guest checkout locks in Redis
3. Update allocations + audit log
4. Notify clients via SSE/WebSocket `bill_updated`

---

## 13. Testing requirements (MVP)

| Test | Method | Pass criteria |
|------|--------|---------------|
| 50 concurrent claims, 1 unit | k6 / Jest parallel | Exactly 1 success, 49 × 409 |
| Duplicate idempotency key | Repeat POST | Same body, 1 DB row |
| Webhook double delivery | Replay payload | `confirmed_paid_cents` increments once |
| Checkout double-tap | Parallel checkout | 1 Mollie payment_id |
| Equal split + claim race | Parallel ops | One wins, other 409/423 |
| Redis unavailable | Fallback | DB `FOR UPDATE` only; log degrade |

---

## 14. Observability

| Metric | Alert |
|--------|-------|
| `claim_conflict_rate` | >15% → UX review |
| `409_rate` per session | Spike → possible hijack attempt |
| `orphan_payment_count` | >0 → ops queue |
| `redis_lock_wait_ms` p99 | >500ms → scale Redis |
| `idempotency_replay_count` | baseline |

Audit log fields: `request_id`, `idempotency_key`, `bill_version`, `unit_id`, `outcome`.

---

## 15. MVP vs post-MVP

| Capability | MVP | V1.1+ |
|------------|-----|-------|
| Redis claim lock 30s | ✓ | Configurable |
| Serializable SHARED txs | ✓ (`FOR UPDATE`) | — |
| Real-time SSE bill sync | Best effort | Guaranteed |
| Distributed lock Redlock | Single Redis | Multi-node V2 |
| Fraud velocity (IP) | — | Rate limit joins |
| Geo proximity lock | — | Optional |

---

## 16. Risk summary

| Risk | Mitigation |
|------|------------|
| Redis split-brain / down | DB pessimistic fallback on `FOR UPDATE` |
| Lost lock without release | 30s TTL auto-expire |
| Idempotency cache loss | DB unique on `(endpoint, idempotency_key)` |
| Override during active iDEAL | Override cancels checkout intent + Mollie cancel API if open |
| Clock skew on TTL | Redis TTL only; no wall-clock trust client |

---

*Slice ownership: Part 5 — Bill-Splitting Logic.*
