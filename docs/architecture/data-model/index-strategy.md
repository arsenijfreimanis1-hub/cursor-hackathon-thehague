# Index Strategy — Hot Paths & Reconciliation

**Slice:** Part 9 — Data Model  
**Database:** PostgreSQL 16+  
**Assumptions:** Row-level tenant isolation via `restaurant_id` / `venue_id`; read-heavy guest API; write-heavy claim + webhook paths.

---

## 1. Design principles

1. **Every hot query has a supporting index** — no sequential scans on guest-facing paths at pilot scale (≤50 concurrent sessions).
2. **Partial indexes** for active rows (`state`, `left_at IS NULL`, non-terminal payment statuses).
3. **Unique constraints double as indexes** — `mollie_payment_id`, `idempotency_key`, `token_hash`.
4. **Denormalize filter columns** — `restaurant_id` on `dining_sessions`, `payment_intents`, `payments` for tenant-scoped admin queries without deep joins.
5. **BRIN on append-only time series** — `audit_log_entries.occurred_at`, `webhook_events.received_at` (post-pilot if volume warrants).

---

## 2. Hot path: table lookup by QR

**Query:** Guest scans QR → resolve venue, table, session state, menu.

```sql
-- GET /t/{public_slug}
SELECT t.*, v.restaurant_id, v.timezone, ds.state AS session_state, ds.id AS dining_session_id
FROM table_qr_codes qr
JOIN tables t ON t.id = qr.table_id AND t.is_active = true
JOIN venues v ON v.id = t.venue_id AND v.is_active = true
LEFT JOIN dining_sessions ds ON ds.id = t.current_dining_session_id
WHERE qr.public_slug = $1;
```

| Index | Table | Definition | Rationale |
|-------|-------|------------|-----------|
| `uq_table_qr_codes_public_slug` | `table_qr_codes` | `UNIQUE (public_slug)` | Primary lookup — O(1) |
| `uq_table_qr_codes_table_id` | `table_qr_codes` | `UNIQUE (table_id)` | 1:1 MVP |
| `idx_tables_venue_code` | `tables` | `UNIQUE (venue_id, table_code)` | Admin table list |
| `idx_tables_current_session` | `tables` | `(current_dining_session_id)` WHERE `current_dining_session_id IS NOT NULL` | Session join |

**Expected latency:** <5 ms at pilot cardinality (<500 tables).

**Cache layer (optional MVP):** Redis `qr:{public_slug}` → `{table_id, venue_id, restaurant_id, session_state}` TTL 30s; invalidate on `dining_session` state change.

---

## 3. Hot path: active session

**Queries:**

- Staff console: list active tables for venue.
- Guest: validate join eligibility.
- Scheduler: expire tokens / stale sessions.

### 3.1 Active dining session per table

```sql
-- Enforce + lookup: one open session per table
CREATE UNIQUE INDEX uq_dining_sessions_active_table
ON dining_sessions (table_id)
WHERE state IN ('SEATED', 'PAYMENT_ACTIVE');
```

### 3.2 Venue active sessions (staff dashboard)

```sql
SELECT ds.*, t.table_code, ps.state AS payment_state, b.remaining_cents
FROM dining_sessions ds
JOIN tables t ON t.id = ds.table_id
LEFT JOIN payment_sessions ps ON ps.id = ds.active_payment_session_id
LEFT JOIN bills b ON b.payment_session_id = ps.id
WHERE ds.venue_id = $1 AND ds.state IN ('SEATED', 'PAYMENT_ACTIVE')
ORDER BY ds.opened_at DESC;
```

| Index | Definition |
|-------|------------|
| `idx_dining_sessions_venue_state` | `(venue_id, state, opened_at DESC)` |
| `idx_dining_sessions_restaurant_opened` | `(restaurant_id, opened_at DESC)` — ops console |

### 3.3 Payment session token validation

```sql
SELECT pst.*, ps.id, ps.claims_frozen, ps.state, b.bill_version
FROM payment_session_tokens pst
JOIN payment_sessions ps ON ps.id = pst.payment_session_id
JOIN bills b ON b.payment_session_id = ps.id
WHERE pst.token_hash = $1
  AND pst.state = 'ISSUED'
  AND pst.expires_at > now();
```

| Index | Definition |
|-------|------------|
| `uq_payment_session_tokens_hash` | `UNIQUE (token_hash)` |
| `idx_payment_session_tokens_session_state` | `(payment_session_id, state)` |
| `idx_payment_session_tokens_expires` | `(expires_at)` WHERE `state = 'ISSUED'` — scheduler TTL job |

### 3.4 Active payment session by dining session

| Index | Definition |
|-------|------------|
| `idx_payment_sessions_dining_session` | `(dining_session_id, state)` |
| `uq_bills_payment_session` | `UNIQUE (payment_session_id)` |

---

## 4. Hot path: claim by bill item (allocations)

**Queries:**

- List bill with claim ownership for guest UI.
- Commit claim with optimistic concurrency.
- Detect double-allocation.

### 4.1 Bill lines + units + allocations (guest bill view)

```sql
SELECT bl.*, au.id AS unit_id, a.participant_id, a.split_mode, a.share_numerator, a.share_denominator, p.display_name
FROM bill_lines bl
JOIN allocatable_units au ON au.bill_line_id = bl.id
LEFT JOIN allocations a ON a.allocatable_unit_id = au.id
  AND a.state IN ('COMMITTED', 'LOCKED_FOR_CHECKOUT')
LEFT JOIN participants p ON p.id = a.participant_id
WHERE bl.bill_id = $1 AND bl.voided_at IS NULL
ORDER BY bl.sort_order, au.unit_index;
```

| Index | Definition |
|-------|------------|
| `idx_bill_lines_bill_sort` | `(bill_id, sort_order)` WHERE `voided_at IS NULL` |
| `idx_allocatable_units_line` | `(bill_line_id, unit_index)` |
| `idx_allocations_bill_active` | `(bill_id, state)` WHERE `state IN ('COMMITTED','LOCKED_FOR_CHECKOUT')` |
| `idx_allocations_unit_active` | `(allocatable_unit_id)` WHERE `state IN ('COMMITTED','LOCKED_FOR_CHECKOUT')` |
| `idx_allocations_participant` | `(participant_id, state)` |

### 4.2 Full-unit claim uniqueness (ITEM mode)

```sql
CREATE UNIQUE INDEX uq_allocations_full_unit
ON allocations (allocatable_unit_id)
WHERE state IN ('COMMITTED', 'LOCKED_FOR_CHECKOUT')
  AND share_numerator = share_denominator;
```

Prevents two guests owning 100% of same discrete unit.

### 4.3 Optimistic allocation update

```sql
UPDATE allocations
SET participant_id = $1, version = version + 1, state = 'COMMITTED', committed_at = now()
WHERE id = $2 AND version = $3 AND state = 'DRAFT';
```

| Index | Definition |
|-------|------------|
| `pk_allocations` | `(id)` includes `version` in WHERE — PK sufficient |

### 4.4 Bill version stale check

```sql
UPDATE bills SET bill_version = bill_version + 1, updated_at = now()
WHERE id = $1 AND bill_version = $2;
```

| Index | Definition |
|-------|------------|
| `pk_bills` | `(id, bill_version)` — PK + version in UPDATE |

---

## 5. Hot path: payment reconciliation

**Queries:**

- Webhook ingress: find intent by Mollie ID.
- Idempotent duplicate detection.
- Nightly reconcile: platform `payments` vs Mollie API.
- Table remaining balance update.

### 5.1 Webhook → payment intent

```sql
SELECT pi.*, ci.participant_id, b.id AS bill_id, b.bill_grand_total_cents, b.confirmed_paid_cents
FROM payment_intents pi
JOIN checkout_intents ci ON ci.id = pi.checkout_intent_id
JOIN bills b ON b.id = ci.bill_id
WHERE pi.mollie_payment_id = $1;
```

| Index | Definition |
|-------|------------|
| `uq_payment_intents_mollie_id` | `UNIQUE (mollie_payment_id)` WHERE `mollie_payment_id IS NOT NULL` |
| `uq_payment_intents_idempotency` | `UNIQUE (idempotency_key)` |
| `idx_payment_intents_session_status` | `(payment_session_id, status)` |
| `idx_payment_intents_participant` | `(participant_id, created_at DESC)` |

### 5.2 Webhook idempotency store

```sql
INSERT INTO webhook_events (source, external_id, idempotency_key, payload_json, ...)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING id;
```

| Index | Definition |
|-------|------------|
| `uq_webhook_events_idempotency` | `UNIQUE (idempotency_key)` |
| `idx_webhook_events_external` | `(source, external_id)` |
| `idx_webhook_events_unprocessed` | `(received_at)` WHERE `processing_status = 'RECEIVED'` |

**Idempotency key format:** `mollie:{tr_id}:{status}:{amount_cents}`.

### 5.3 Confirmed payments ledger

```sql
SELECT COALESCE(SUM(amount_cents), 0) - COALESCE(SUM(r.amount_cents), 0)
FROM payments p
LEFT JOIN payment_refunds r ON r.payment_id = p.id AND r.status = 'COMPLETED'
WHERE p.payment_session_id = $1;
```

| Index | Definition |
|-------|------------|
| `idx_payments_session_paid_at` | `(payment_session_id, paid_at)` |
| `uq_payments_intent` | `UNIQUE (payment_intent_id)` |
| `uq_payments_mollie_id` | `UNIQUE (mollie_payment_id)` |
| `idx_payments_restaurant_paid` | `(restaurant_id, paid_at DESC)` — admin reporting |
| `idx_payment_refunds_payment` | `(payment_id, status)` |

### 5.4 Checkout intent lock

```sql
SELECT * FROM checkout_intents
WHERE participant_id = $1 AND state = 'ACTIVE' AND expires_at > now();
```

| Index | Definition |
|-------|------------|
| `idx_checkout_intents_participant_active` | `UNIQUE (participant_id)` WHERE `state = 'ACTIVE'` |
| `uq_checkout_intents_idempotency` | `UNIQUE (idempotency_key)` |

### 5.5 Daily reconciliation job

```sql
SELECT p.mollie_payment_id, p.amount_cents, p.paid_at
FROM payments p
WHERE p.restaurant_id = $1
  AND p.paid_at >= $2 AND p.paid_at < $3
ORDER BY p.paid_at;
```

Uses `idx_payments_restaurant_paid`. Cross-check against Mollie List Payments API; mismatches → `incidents` row.

---

## 6. Secondary indexes (admin & ops)

| Index | Table | Definition | Query |
|-------|-------|------------|-------|
| `idx_staff_members_restaurant_active` | `staff_members` | `(restaurant_id)` WHERE `is_active` | Staff list |
| `idx_service_signals_table_open` | `service_signals` | `(table_id, created_at DESC)` WHERE `status = 'OPEN'` | Waiter inbox |
| `idx_audit_log_restaurant_time` | `audit_log_entries` | `(restaurant_id, occurred_at DESC)` | Compliance export |
| `idx_audit_log_resource` | `audit_log_entries` | `(resource_type, resource_id, occurred_at DESC)` | Entity history |
| `idx_disputes_restaurant_open` | `disputes` | `(restaurant_id, status)` WHERE `status = 'OPEN'` | Ops queue |
| `idx_participants_session_active` | `participants` | `(payment_session_id)` WHERE `left_at IS NULL` | Presence |
| `idx_rewards_ledger_account_time` | `rewards_ledger_entries` | `(rewards_account_id, created_at DESC)` | Account history V1.1 |

---

## 7. Foreign key index coverage

PostgreSQL does not auto-index FK columns. Required FK indexes:

| FK column | Table |
|-----------|-------|
| `venue_id` | `tables`, `dining_sessions`, `menu_categories` |
| `restaurant_id` | `dining_sessions`, `bills`, `payment_intents`, `payments`, `audit_log_entries` |
| `dining_session_id` | `payment_sessions`, `bills`, `orders` |
| `payment_session_id` | `participants`, `checkout_intents`, `payment_intents`, `payments` |
| `bill_id` | `bill_lines`, `allocations`, `custom_pledges` |
| `bill_line_id` | `allocatable_units` |
| `allocatable_unit_id` | `allocations` |
| `participant_id` | `allocations`, `payment_intents`, `payments` |
| `checkout_intent_id` | `payment_intents`, `tips` |
| `payment_id` | `payment_refunds`, `disputes`, `tips` |

---

## 8. Partitioning (post-MVP, >10M rows)

| Table | Strategy | Trigger |
|-------|----------|---------|
| `audit_log_entries` | RANGE `occurred_at` monthly | >50M rows |
| `webhook_events` | RANGE `received_at` monthly | Webhook volume |
| `bill_state_events` | RANGE `occurred_at` | Long-retention venues |

**MVP:** Single partition; monitor table bloat via `pg_stat_user_tables`.

---

## 9. Query plans to verify in CI

| Test | Assert |
|------|--------|
| QR lookup by slug | Index Scan on `uq_table_qr_codes_public_slug` |
| Token validate | Index Scan on `uq_payment_session_tokens_hash` |
| Full unit claim insert conflict | Unique violation on `uq_allocations_full_unit` |
| Webhook duplicate | `ON CONFLICT DO NOTHING` on webhook idempotency |
| Session remaining balance | Index Scan on `idx_payments_session_paid_at` |

Use `EXPLAIN (ANALYZE, BUFFERS)` in integration tests with seed data: 1 venue, 30 tables, 5 active payment sessions, 200 allocations.

---

## 10. Redis keys (non-PostgreSQL, concurrency slice)

Not indexes but complement hot paths — see [concurrency.md](../../domain/split-engine/concurrency.md):

| Key | TTL | Purpose |
|-----|-----|---------|
| `claim_lock:{allocatable_unit_id}` | 30s | ITEM/SHARED commit mutex |
| `checkout_lock:{participant_id}` | 15m | One checkout in flight |
| `qr:{public_slug}` | 30s | QR resolution cache |

PostgreSQL remains source of truth; Redis failure → fall back to row locks only (higher contention).

---

## 11. MVP vs post-MVP index additions

| Index | When |
|-------|------|
| `idx_orders_pos_external` | V1.1 POS import — `(external_pos_check_id)` |
| `idx_guest_devices_fingerprint` | V1.1 fraud — `(fingerprint_hash)` |
| `idx_payments_settlement_status` | V1.1 payout automation — `(settlement_status, paid_at)` |
| GIN on `audit_log_entries.payload_json` | Ops search — only if needed |

---

*Slice ownership: Part 9 — Data Model. Cross-ref: [entity-dictionary.md](./entity-dictionary.md), [erd.mmd](./erd.mmd).*
