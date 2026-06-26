# Backend Event Catalog — Core Flows A–O

**Product:** Rekentafel (working name)  
**Slice:** Core User Flows  
**Version:** 1.0  
**Transport:** Internal event bus (MVP: Postgres outbox + worker; POST-MVP: Redis/NATS)

---

## Conventions

| Field | Description |
|-------|-------------|
| `event_id` | UUID v7, unique |
| `occurred_at` | ISO-8601 UTC |
| `restaurant_id` | Tenant scope — all events include unless platform-only |
| `correlation_id` | Trace across user session / payment |
| `actor` | `guest` \| `waiter` \| `manager` \| `system` \| `mollie_webhook` |
| `idempotency_key` | Required for payment and claim mutations |

**Delivery guarantees (MVP):** at-least-once; consumers must be idempotent.

---

## Event Index by Domain

| Domain | Events | Primary producers |
|--------|--------|-------------------|
| QR & menu | 3 | Guest API |
| Service signals | 4 | Guest API, Staff API |
| Table & session | 8 | Staff API, Scheduler |
| Bill & claims | 12 | Staff API, Guest API |
| Split logic | 5 | Guest API |
| Payments | 10 | Guest API, Mollie webhook worker |
| Loyalty | 4 | Payment worker, Account API |
| Restaurant ops | 9 | Admin API, Ops console |
| Deferred (L/M) | 4 | — POST-MVP only |

---

## QR & Menu Events

### `qr.scan.resolved`

| | |
|--|--|
| **Producer** | Guest API — `GET /t/{slug}/{table_code}` |
| **Consumers** | Analytics aggregator, rate-limit service |
| **MVP** | Yes |

**Payload:**

```json
{
  "table_id": "uuid",
  "restaurant_id": "uuid",
  "scan_context": "empty_table | payment_join | invalid",
  "has_payment_token": false,
  "guest_device_id": "uuid",
  "user_agent_hash": "sha256"
}
```

---

### `menu.viewed`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Analytics (aggregated only, no PII) |
| **MVP** | Yes |

**Payload:** `table_id`, `category_id`, `guest_device_id`

---

### `menu.item.detail_viewed`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Analytics |
| **MVP** | Optional (pilot can disable) |

---

## Service Signal Events (Flow B)

### `service_signal.created`

| | |
|--|--|
| **Producer** | Guest API — `POST /tables/{id}/service-signals` |
| **Consumers** | Staff notification service, rate-limiter |
| **MVP** | Yes |

**Payload:**

```json
{
  "signal_id": "uuid",
  "table_id": "uuid",
  "type": "ready_to_order | assistance",
  "guest_device_id": "uuid",
  "cooldown_until": "ISO-8601"
}
```

---

### `service_signal.delivered`

| | |
|--|--|
| **Producer** | Notification service |
| **Consumers** | Staff WebSocket gateway |
| **MVP** | Yes |

---

### `service_signal.acknowledged`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Audit log, analytics (response time SLA) |
| **MVP** | Yes |

**Payload:** `signal_id`, `waiter_id`, `ack_at`

---

### `service_signal.expired`

| | |
|--|--|
| **Producer** | Scheduler (TTL 30 min unacked) |
| **Consumers** | Ops alerts |
| **MVP** | Yes |

---

## Table & Session Events (Flow C, O)

### `dining_session.started`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Table state service, audit |
| **MVP** | Yes |

**Payload:** `dining_session_id`, `table_id`, `waiter_id`, `party_size?`

---

### `dining_session.ended`

| | |
|--|--|
| **Producer** | Staff API (cancel before payment) |
| **Consumers** | Table state service |
| **MVP** | Yes |

---

### `payment_session.opened`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Token service, guest poll refresh, audit |
| **MVP** | Yes |

**Payload:** `payment_session_id`, `bill_id`, `expires_at`, `join_pin`

---

### `payment_session.token_issued`

| | |
|--|--|
| **Producer** | Token service (on open + refresh) |
| **Consumers** | Audit, optional SMS/email (post-MVP) |
| **MVP** | Yes |

**Payload:** `token_hash` (never raw token in log), `ttl_seconds`, `rotation_reason`

---

### `payment_session.token_expired`

| | |
|--|--|
| **Producer** | Scheduler |
| **Consumers** | Guest API (invalidate joins), staff alert |
| **MVP** | Yes |

---

### `payment_session.joined`

| | |
|--|--|
| **Producer** | Guest API — `POST /payment-sessions/join` |
| **Consumers** | Presence service, WebSocket fanout |
| **MVP** | Yes |

**Payload:** `participant_id`, `display_name`, `guest_device_id`, `user_id?`

---

### `payment_session.completed`

| | |
|--|--|
| **Producer** | Ledger service (remaining ≈ 0) |
| **Consumers** | Staff notification, loyalty worker |
| **MVP** | Yes |

---

### `table.closed`

| | |
|--|--|
| **Producer** | Staff API (manager/waiter) |
| **Consumers** | Reset service, analytics, loyalty finalize |
| **MVP** | Yes |

**Payload:** `close_reason`, `override_used`, `external_payment?`

---

### `table.reset`

| | |
|--|--|
| **Producer** | Reset service |
| **Consumers** | Cache purge, GDPR retention job schedule |
| **MVP** | Yes |

---

## Bill & Claim Events (Flow C, E, O)

### `bill.created`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Ledger init, audit |
| **MVP** | Yes |

---

### `bill.updated`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Claim recalc service, guest WebSocket |
| **MVP** | Yes |

**Payload:** `bill_version`, `line_changes[]`, `new_total`

---

### `bill.locked`

### `bill.unlocked`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Guest API (block claims during edit) |
| **MVP** | Yes |

---

### `bill.line.shared_flagged`

| | |
|--|--|
| **Producer** | Staff API |
| **Consumers** | Split engine (Flow H) |
| **MVP** | Yes |

---

### `claim.created`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Ledger allocation, WebSocket fanout |
| **MVP** | Yes |

**Payload:**

```json
{
  "claim_id": "uuid",
  "participant_id": "uuid",
  "line_id": "uuid",
  "quantity": 2,
  "allocated_amount_cents": 1400,
  "bill_version": 12
}
```

---

### `claim.updated`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Ledger, WebSocket |
| **MVP** | Yes |

---

### `claim.released`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Ledger, WebSocket |
| **MVP** | Yes |

---

### `claim.conflict_detected`

| | |
|--|--|
| **Producer** | Claim service (optimistic fail) |
| **Consumers** | Metrics, optional guest toast trigger |
| **MVP** | Yes |

---

### `claim.admin_override`

| | |
|--|--|
| **Producer** | Staff API (manager) |
| **Consumers** | Audit, ledger recalc, guest notify |
| **MVP** | Yes |

---

### `ledger.balance.updated`

| | |
|--|--|
| **Producer** | Ledger service |
| **Consumers** | All participant clients, staff monitor |
| **MVP** | Yes |

**Payload:** `remaining_cents`, `paid_cents`, `bill_total_cents`

---

## Split Events (Flow F, G, H)

### `split.equal.created`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Ledger, checkout composer |
| **MVP** | Yes |

**Payload:** `participant_ids[]`, `pool_cents`, `per_head_allocations[]`

---

### `split.equal.recalculated`

| | |
|--|--|
| **Producer** | Split engine (participant join/leave) |
| **Consumers** | Guest UI refresh |
| **MVP** | Yes |

---

### `split.custom.intent_created`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Checkout composer |
| **MVP** | Yes |

**Payload:** `amount_cents`, `participant_id`

---

### `split.shared.calculated`

| | |
|--|--|
| **Producer** | Split engine |
| **Consumers** | Participant totals |
| **MVP** | Yes |

**Payload:** `line_id`, `denominator`, `per_person_cents`

---

### `split.shared.recalculate_requested`

| | |
|--|--|
| **Producer** | Guest API or Staff API |
| **Consumers** | Split engine |
| **MVP** | Yes |

---

## Tip & Checkout Events (Flow I)

### `tip.selected`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Checkout composer, reporting |
| **MVP** | Yes |

**Payload:** `basis_cents`, `tip_cents`, `tip_percent?`

---

### `checkout.created`

| | |
|--|--|
| **Producer** | Guest API |
| **Consumers** | Mollie adapter, audit |
| **MVP** | Yes |

**Payload:** `checkout_id`, `participant_id`, `food_cents`, `tip_cents`, `total_cents`, `mollie_payment_id?`

---

## Payment Events — Mollie (Flow J)

### `payment.mollie.created`

| | |
|--|--|
| **Producer** | Mollie adapter |
| **Consumers** | Audit |
| **MVP** | Yes |

---

### `payment.mollie.redirect_returned`

| | |
|--|--|
| **Producer** | Guest API (return URL handler) |
| **Consumers** | Status poller |
| **MVP** | Yes |

**Note:** Never trust return URL alone — webhook is source of truth.

---

### `payment.mollie.webhook.received`

| | |
|--|--|
| **Producer** | Webhook ingress |
| **Consumers** | Payment state machine |
| **MVP** | Yes |

---

### `payment.mollie.webhook.paid`

| | |
|--|--|
| **Producer** | Payment worker |
| **Consumers** | Ledger, loyalty, staff notify, receipt email |
| **MVP** | Yes |

**Payload:** `mollie_payment_id`, `paid_cents`, `method`, `settlement_reference?`

---

### `payment.mollie.webhook.failed`

| | |
|--|--|
| **Producer** | Payment worker |
| **Consumers** | Guest retry UI, staff timeline |
| **MVP** | Yes |

---

### `payment.mollie.webhook.expired`

| | |
|--|--|
| **Producer** | Payment worker |
| **Consumers** | Release checkout hold |
| **MVP** | Yes |

---

### `payment.mollie.webhook.canceled`

| | |
|--|--|
| **Producer** | Payment worker |
| **Consumers** | Guest UI, audit |
| **MVP** | Yes |

---

### `payment.refund.initiated`

| | |
|--|--|
| **Producer** | Staff/manager API → Mollie refund |
| **Consumers** | Ledger, loyalty reversal |
| **MVP** | Manual only |

---

### `payment.refund.completed`

| | |
|--|--|
| **Producer** | Mollie webhook |
| **Consumers** | Audit, loyalty |
| **MVP** | Manual only |

---

### `payment.external_recorded`

| | |
|--|--|
| **Producer** | Staff API (terminal fallback) |
| **Consumers** | Table close workflow |
| **MVP** | Yes — audit flag only |

---

## Loyalty Events (Flow K — MVP minimal)

### `account.linked`

| | |
|--|--|
| **Producer** | Account API |
| **Consumers** | Loyalty service |
| **MVP** | Yes |

---

### `loyalty.accrued`

| | |
|--|--|
| **Producer** | Payment worker (on `paid`) |
| **Consumers** | Account UI, reporting |
| **MVP** | Yes |

**Payload:** `user_id`, `points`, `payment_id`, `restaurant_id`

---

### `loyalty.reversed`

| | |
|--|--|
| **Producer** | Refund worker |
| **Consumers** | Account UI |
| **MVP** | Yes |

---

### `loyalty.visit_recorded`

| | |
|--|--|
| **Producer** | Table close worker |
| **Consumers** | Account history |
| **MVP** | Yes |

---

## Restaurant & Ops Events (Flow N, O)

### `restaurant.created`

### `restaurant.mollie.connected`

### `restaurant.activated`

### `restaurant.deactivated`

| | |
|--|--|
| **Producer** | Admin API, Ops console |
| **Consumers** | Feature flags, billing |
| **MVP** | Yes |

---

### `tables.batch_created`

| | |
|--|--|
| **Producer** | Admin API |
| **Consumers** | QR PDF generator |
| **MVP** | Yes |

---

### `menu.imported`

| | |
|--|--|
| **Producer** | Admin API |
| **Consumers** | Menu cache, validation service |
| **MVP** | Yes |

---

### `staff.invited`

### `staff.role_changed`

| | |
|--|--|
| **Producer** | Admin API |
| **Consumers** | Auth service, audit |
| **MVP** | Yes |

---

### `shift.summary.generated`

| | |
|--|--|
| **Producer** | Scheduler or manager action |
| **Consumers** | Email/report export |
| **MVP** | Optional pilot |

---

## Deferred Events (Flows L & M — POST-MVP)

> **Do not emit in MVP.** Listed for registry continuity.

| Event | Producer (future) | Consumers (future) |
|-------|-------------------|-------------------|
| `overpay.intent.created` | Guest API | Promo credit service |
| `promo_credit.issued` | Overpay worker | Account UI, compliance log |
| `redemption.requested` | Account API | Partner marketplace |
| `voucher.issued` | Partner service | Account UI, email |
| `voucher.redeemed` | Partner POS/API | Ledger, partner billing |

---

## Consumer Dependency Matrix

| Consumer service | Subscribes to |
|------------------|---------------|
| **Table state** | `dining_session.*`, `payment_session.*`, `table.*` |
| **Token service** | `payment_session.opened`, refresh commands |
| **Staff WebSocket** | `service_signal.*`, `ledger.balance.updated`, `payment.mollie.webhook.*` |
| **Guest WebSocket/poll** | `claim.*`, `ledger.*`, `bill.updated`, `split.*` |
| **Ledger** | `claim.*`, `split.*`, `payment.mollie.webhook.paid`, `payment.refund.*` |
| **Mollie adapter** | `checkout.created` |
| **Payment worker** | `payment.mollie.webhook.*` |
| **Loyalty worker** | `payment.mollie.webhook.paid`, `loyalty.reversed`, `table.closed` |
| **Analytics** | `qr.*`, `menu.*`, `payment_session.completed` (aggregated) |
| **Audit log** | All mutating events |
| **Scheduler** | TTL on signals, tokens, stale sessions |
| **GDPR retention** | `table.reset` |

---

## Webhook External (Inbound)

| Source | Endpoint | Maps to event |
|--------|----------|---------------|
| Mollie | `POST /webhooks/mollie` | `payment.mollie.webhook.*` |

**Verification:** Mollie signature header + fetch payment status API double-check on `paid`.

---

## Crypto Rail (DEFERRED)

No MVP events. Future namespace prefix: `crypto.*` — separate PCI/AML review before catalog merge.

---

## NEW_REGISTRY_ENTRIES

| Canonical name | Type | Description |
|----------------|------|-------------|
| `payment_session_id` | UUID | Short-lived guest payment context |
| `dining_session_id` | UUID | Waiter-started service period |
| `participant_id` | UUID | Guest join entity within payment session |
| `guest_device_id` | UUID | Anonymous device cookie |
| `bill_version` | int | Optimistic concurrency for claims |
| `join_pin` | string(6) | Human-readable payment join code |
| `remaining_cents` | int | Table ledger field |
