# Background Jobs Catalog

**Product (working name):** Rekentafel  
**Slice:** Part 10 — API / Backend Design  
**Queue:** BullMQ on Redis  
**Outbox:** PostgreSQL `outbox_events` (at-least-once to queue)  
**Cross-references:** [service-map.md](./service-map.md), [event-catalog.md](../../flows/event-catalog.md), [payment-architecture.md](../payments/payment-architecture.md)

---

## 1. Architecture

```
API handler
  → DB transaction (business write + outbox insert)
  → COMMIT
  → Outbox relay (poll 500ms) → BullMQ enqueue
  → Worker consumer (idempotent)
  → Side effects (Mollie, email, SSE fanout, ledger)
```

**Scheduler process:** node-cron singleton triggers periodic jobs (not BullMQ repeatable — simpler ops).

**Failure policy default:** Exponential backoff; max 8 attempts; then dead-letter queue (DLQ) + ops alert.

---

## 2. Job index

| Job name | Trigger | Schedule | Priority | MVP |
|----------|---------|----------|----------|-----|
| `outbox.relay` | Poll | 500ms | Critical | ✓ |
| `webhook.mollie.process` | Queue | On ingest | Critical | ✓ |
| `webhook.mollie.retry` | Queue | Backoff | Critical | ✓ |
| `payment.poll_stale` | Cron | */15 * * * * | High | ✓ |
| `payment.reconcile_daily` | Cron | 0 6 * * * Europe/Amsterdam | High | ✓ |
| `session.expire_payment_tokens` | Cron | */5 * * * * | High | ✓ |
| `session.expire_payment_sessions` | Cron | */5 * * * * | High | ✓ |
| `claim.cleanup_stale_checkouts` | Cron | */2 * * * * | High | ✓ |
| `claim.release_failed_payment_locks` | Cron | */2 * * * * | High | ✓ |
| `signal.expire_unacked` | Cron | */10 * * * * | Medium | ✓ |
| `signal.escalate_unacked` | Cron | */1 * * * * | Medium | ✓ |
| `table.reset_after_close` | Event | On `table.closed` | Medium | ✓ |
| `loyalty.accrue` | Event | On `payment.mollie.webhook.paid` | Low | ✓ minimal |
| `loyalty.reverse` | Event | On refund | Low | ✓ |
| `notification.staff_push` | Event | Various | Medium | ✓ |
| `notification.guest_receipt_email` | Event | On paid (opt-in) | Low | Optional |
| `mollie.oauth_refresh` | Cron | 0 */6 * * * | High | ✓ |
| `idempotency.purge_expired` | Cron | 0 3 * * * | Low | ✓ |
| `audit.archive_cold` | Cron | 0 2 1 * * | Low | Post-MVP |
| `gdpr.guest_device_purge` | Cron | 0 4 * * 0 | Medium | ✓ |
| `analytics.aggregate_daily` | Cron | 30 5 * * * | Low | Optional |
| `crypto.stub_health` | — | — | — | **Not scheduled** |

---

## 3. Critical path jobs

### 3.1 `outbox.relay`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Deliver Postgres outbox rows to BullMQ |
| **Trigger** | Poll every 500ms |
| **Concurrency** | 1 (per scheduler instance) |
| **Idempotency** | `outbox_events.id` marked `published_at` after enqueue |

**Algorithm:**

```sql
SELECT * FROM outbox_events
WHERE published_at IS NULL
ORDER BY created_at
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

For each row → enqueue to `{domain}.{action}` queue → `UPDATE published_at = now()`.

**Failure:** Row stays unpublished; retry next poll. Alert if lag > 30s.

---

### 3.2 `webhook.mollie.process`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Apply Mollie payment status to ledger |
| **Trigger** | Webhook ingress enqueues immediately |
| **Payload** | `{ mollie_payment_id, restaurant_id, raw_body }` |
| **Timeout** | 30s |
| **Concurrency** | 10 per worker |

**Steps:**

1. Load `payment_records` by `mollie_payment_id`
2. Fetch Mollie `GET /v2/payments/{id}` with restaurant OAuth token
3. Verify amount/currency/metadata match local `CheckoutIntent`
4. Insert `processed_webhooks` (idempotent)
5. Transition `payment_records.status`
6. Update `bill_settlements.confirmed_paid_cents`, `remaining_cents`, state
7. Update `participant` state → `PAID` if paid
8. Emit `payment.mollie.webhook.{status}`, `ledger.balance.updated`
9. Enqueue `loyalty.accrue` if paid + account linked

**Failure handling:**

| Error | Action |
|-------|--------|
| Mollie 5xx | Retry backoff 1s, 2s, 4s… max 8 |
| Unknown payment ID | DLQ + ops alert (possible misconfig) |
| Amount mismatch | DLQ + halt auto-settle; ops review |
| OAuth token expired | Enqueue `mollie.oauth_refresh`, retry after 30s |
| DB conflict | Retry once |

**Never:** Return failure to Mollie — ingress already returned 200.

---

### 3.3 `webhook.mollie.retry`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Re-process DLQ webhooks after fix |
| **Trigger** | Manual ops OR auto after OAuth refresh |
| **Schedule** | Every 30 min scans DLQ < 24h old |

---

### 3.4 `payment.poll_stale`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Catch missed webhooks |
| **Schedule** | Every 15 minutes |
| **Query** | `payment_records WHERE status = MOLLIE_OPEN AND created_at < now() - interval '20 minutes'` |

**Action:** Poll Mollie; if terminal status, enqueue `webhook.mollie.process` with synthetic payload.

**Cap:** 50 payments per run per restaurant (avoid rate limit).

---

### 3.5 `payment.reconcile_daily`

| Attribute | Value |
|-----------|-------|
| **Purpose** | Cross-check platform ledger vs Mollie |
| **Schedule** | 06:00 Europe/Amsterdam |
| **Scope** | Previous calendar day per restaurant |

**Checks:**

| Check | Mismatch action |
|-------|-----------------|
| Sum `PAID` payment_records vs Mollie list API | Ops ticket |
| `orphan_payment = true` rows | Summary email to platform ops |
| `remaining_cents < 0` | Page on-call |
| Refund status drift | Log + ticket |

**MVP output:** CSV to ops dashboard; no auto-adjustment.

**Post-MVP:** Mollie Settlements API automation.

---

## 4. Session and token jobs

### 4.1 `session.expire_payment_tokens`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 5 minutes |
| **Query** | `payment_session_tokens WHERE expires_at < now() AND revoked_at IS NULL AND state = ISSUED` |

**Actions:**

1. Set token state → `EXPIRED`
2. Emit `payment_session.token_expired`
3. SSE push to joined guests: `{ type: "token_expired", refresh_required: true }`
4. Do **not** revoke in-flight Mollie payments

---

### 4.2 `session.expire_payment_sessions`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 5 minutes |
| **Query** | `payment_sessions WHERE expires_at < now() AND status = OPEN AND confirmed_paid_cents = 0` |

**Actions:**

1. Close session if no payments started
2. If partial payments exist: extend 30 min + notify staff (do not auto-close)
3. Emit `payment_session.token_expired`

**Configurable:** Venue `payment_session_max_ttl_hours` (default 6).

---

## 5. Claim and checkout cleanup jobs

### 5.1 `claim.cleanup_stale_checkouts`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 2 minutes |
| **Query** | `checkout_intents WHERE status = MOLLIE_OPEN AND created_at < now() - interval '15 minutes'` |

**Actions:**

1. Poll Mollie status
2. If `expired` / `canceled` / `failed`: release checkout Redis lock
3. Set participant → `PAYMENT_FAILED` or `ALLOCATING`
4. Release allocation `LOCKED_FOR_CHECKOUT` → `COMMITTED`
5. Emit `payment.mollie.webhook.expired` equivalent

---

### 5.2 `claim.release_failed_payment_locks`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 2 minutes |
| **Query** | Participants `PAYMENT_FAILED` with checkout lock TTL elapsed |

**Actions:** DEL `checkout:lock:{bill_id}:{participant_id}`; allow retry.

---

### 5.3 `claim.stale_draft_cleanup` (optional MVP)

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 30 minutes |
| **Query** | `ClaimIntent` drafts older than 1h never committed |

**Actions:** Delete draft rows (no ledger impact).

---

## 6. Service signal jobs

### 6.1 `signal.expire_unacked`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 10 minutes |
| **TTL** | 30 minutes unacked |

**Actions:** Set signal status → `expired`; emit `service_signal.expired`.

---

### 6.2 `signal.escalate_unacked`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 1 minute |
| **Threshold** | Unacked > 3 minutes |

**Actions:** Re-push WebSocket; increment escalation counter; after 3 escalations → ops Slack (pilot).

---

## 7. Table lifecycle jobs

### 7.1 `table.reset_after_close`

| Attribute | Value |
|-----------|-------|
| **Trigger** | `table.closed` event |
| **Delay** | 5 minutes (grace for receipt view) |

**Actions:**

1. Verify `TableSessionState = CLOSED`
2. Purge Redis keys: `claim:lock:*`, `checkout:lock:*` for `bill_id`
3. Anonymize participant display names (keep IDs for audit)
4. Schedule `gdpr` retention markers
5. Emit `table.reset`
6. Set table → `EMPTY`

---

## 8. Integration jobs

### 8.1 `mollie.oauth_refresh`

| Attribute | Value |
|-----------|-------|
| **Schedule** | Every 6 hours |
| **Query** | Restaurants with token expiring within 24h |

**Actions:**

1. Refresh OAuth token via Mollie
2. Store encrypted new refresh token
3. On failure: set `restaurant.payments_status = DISCONNECTED`; email admin; disable checkout

**Alert:** Any pilot restaurant disconnected → immediate page.

---

### 8.2 `loyalty.accrue`

| Attribute | Value |
|-----------|-------|
| **Trigger** | `payment.mollie.webhook.paid` |
| **Condition** | `participant.user_id IS NOT NULL` |

**MVP:** Points = `floor(paid_food_cents / 100)` (1 point per euro); display only.

**Emit:** `loyalty.accrued`.

**Post-MVP:** Configurable earn rates; never stored-value wallet.

---

### 8.3 `loyalty.reverse`

| Attribute | Value |
|-----------|-------|
| **Trigger** | Refund webhook / manual refund |

**Actions:** Claw back points; emit `loyalty.reversed`.

---

## 9. Notification jobs

### 9.1 `notification.staff_push`

| Attribute | Value |
|-----------|-------|
| **Trigger** | `service_signal.created`, `payment.mollie.webhook.paid`, `ledger.balance.updated` (fully paid) |
| **Delivery** | WebSocket fanout to connected staff sessions |

**Retry:** 3× if no connected clients (signal stays in inbox DB).

---

### 9.2 `notification.guest_receipt_email`

| Attribute | Value |
|-----------|-------|
| **Trigger** | Paid + guest opted in with email |
| **Provider** | Postmark / SendGrid |
| **Retry** | 5× exponential |

**Content:** Payment amount, venue name, table, date — no full table bill of other guests.

---

## 10. Maintenance jobs

### 10.1 `idempotency.purge_expired`

| Schedule | Daily 03:00 UTC |
|----------|----------------|
| **Action** | `DELETE FROM idempotency_keys WHERE expires_at < now()` |
| **Batch** | 10,000 rows per iteration |

Also purge matching Redis `idempotency:*` keys via SCAN.

---

### 10.2 `gdpr.guest_device_purge`

| Schedule | Weekly Sunday 04:00 UTC |
|----------|-------------------------|
| **Query** | `guest_devices WHERE last_seen_at < now() - interval '365 days' AND user_id IS NULL` |
| **Action** | Delete device row; anonymize linked analytics |

---

### 10.3 `audit.archive_cold` (post-MVP)

Move audit events > 2 years to cold storage (S3/Glacier).

---

## 11. Job configuration defaults

| Parameter | Default |
|-----------|---------|
| Max attempts | 8 |
| Backoff | Exponential, base 1s, max 15 min |
| DLQ retention | 14 days |
| Worker concurrency | 10 (webhook), 5 (general) |
| Job timeout | 30s (webhook), 120s (reconcile) |
| Stalled job check | 30s interval |

**BullMQ queue names:**

```
critical: webhook.mollie.process, outbox.relay
high:     payment.*, session.*, claim.*, mollie.oauth_refresh
medium:   signal.*, table.reset, notification.staff_push
low:      loyalty.*, analytics.*, gdpr.*, idempotency.*
```

---

## 12. Failure handling playbook

| Symptom | Likely cause | Job / action |
|---------|--------------|--------------|
| Guest paid but balance unchanged | Webhook missed | `payment.poll_stale` |
| Duplicate balance credit | Idempotency bug | Halt worker; audit `processed_webhooks` |
| Checkout stuck 15m+ | Missed expiry job | Manual `claim.cleanup_stale_checkouts` |
| All checkouts fail | OAuth expired | `mollie.oauth_refresh` |
| Orphan payment after close | Late webhook | `payment.reconcile_daily` flag |
| Redis down | Infra | Workers continue; claims use DB locks; page infra |
| Outbox lag growing | Worker saturated | Scale workers; check DLQ |

---

## 13. Monitoring

| Metric | Alert |
|--------|-------|
| `bullmq_queue_depth{critical}` | >100 for 5 min |
| `webhook_process_duration_p99` | >10s |
| `outbox_lag_seconds` | >30s |
| `dlq_count` | >0 |
| `stale_payment_count` | >5 per restaurant |
| `oauth_refresh_failures` | >0 |
| `orphan_payment_total` | >0 daily |

---

## 14. MVP vs post-MVP

| Job | MVP | V1.1 | V2 |
|-----|-----|------|-----|
| Webhook process/retry | ✓ | — | — |
| Daily reconcile | Manual CSV | Automated alerts | Settlements API |
| Stale checkout cleanup | ✓ | — | — |
| Loyalty accrue | Minimal | Full config | Coalition |
| Guest receipt email | Optional | ✓ | — |
| POS import sync | — | ✓ cron | Real-time |
| Crypto settlement poll | **Not scheduled** | — | Licensed partner |
| Fraud velocity scan | — | ✓ | ML |

---

## 15. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Webhook worker crash mid-txn | Inconsistent ledger | Single DB transaction; idempotent retry |
| Outbox relay duplicate enqueue | Double notification | Consumer idempotency on `event_id` |
| Aggressive session expiry during slow meal | Guest friction | Extend on partial pay; staff refresh |
| OAuth refresh job failure silent | All payments fail | Disconnect banner + page |
| Reconcile false positive | Ops noise | Tolerance ±€0.01 rounding |
| GDPR purge vs audit retention | Legal conflict | Pseudonymize, don't delete financial records |

---

*Slice ownership: Part 10 — API / Backend Design.*
