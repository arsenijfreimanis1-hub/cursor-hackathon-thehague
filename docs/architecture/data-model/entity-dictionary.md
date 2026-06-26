# PART 9 — Production Entity Dictionary

**Product (working name):** TabSettle / Rekentafel  
**Slice:** Part 9 — Data Model  
**Stack:** PostgreSQL 16+, TypeScript API, Redis (ephemeral locks only)  
**Currency:** EUR; all money stored as **integer cents** (`*_cents`).

**Cross-slice registry alignment:**

| Canonical name | Defined in | DB table |
|----------------|------------|----------|
| `Bill`, `BillLine`, `AllocatableUnit`, `Allocation`, `Claimant` | [rules-spec.md](../../domain/split-engine/rules-spec.md) | `bills`, `bill_lines`, `allocatable_units`, `allocations`, `participants` |
| `PaymentSessionToken`, `TableSessionState` | split-engine | `payment_sessions`, `dining_sessions` |
| `payment_intent`, `CheckoutIntent`, `PaymentRecord` | [payment-architecture.md](../payments/payment-architecture.md) | `payment_intents`, `checkout_intents`, `payments` |
| `payment_session_id`, `dining_session_id`, `participant_id`, `bill_version` | [event-catalog.md](../../flows/event-catalog.md) | same |

**Naming note:** Split-engine docs use `table_session_id` on `PaymentSessionToken`; event catalog uses `dining_session_id`. **DB canonical FK is `dining_session_id`.** API aliases `table_session_id → dining_session_id` until v2 API cleanup.

---

## 1. Entity overview

| Entity | MVP | Purpose |
|--------|-----|---------|
| `users` | Optional accounts | Registered guest / admin login identity |
| `guest_devices` | Yes | Anonymous browser/device before account link |
| `restaurants` | Yes | Tenant (merchant of record for Mollie) |
| `venues` | Yes (1:1 MVP) | Physical location under restaurant org |
| `tables` | Yes | Persistent table identity + QR target |
| `table_qr_codes` | Yes | Persistent QR slug/code mapping |
| `dining_sessions` | Yes | Waiter-started service period (`TableSessionState`) |
| `payment_sessions` | Yes | Waiter-activated split-pay window + token |
| `payment_session_tokens` | Yes | Short-lived join credential (hashed at rest) |
| `participants` | Yes | Guest join row (`Claimant` in split-engine) |
| `orders` | Schema only | Future POS order header; **no MVP writes** |
| `order_items` | Schema only | Future POS lines; **no MVP writes** |
| `bills` | Yes | Open check header + settlement aggregates |
| `bill_lines` | Yes | Itemized bill rows (`BillLine`) |
| `allocatable_units` | Yes | Atomic claim slots derived from lines |
| `allocations` | Yes | Claim/allocation rows (`Allocation` / event `claim`) |
| `checkout_intents` | Yes | Frozen pre-Mollie checkout snapshot |
| `payment_intents` | Yes | Per-guest Mollie attempt lifecycle |
| `payments` | Yes | Confirmed payment ledger (`PaymentRecord`) |
| `tips` | Yes | Tip metadata per checkout (1:1 checkout) |
| `payment_refunds` | Manual MVP | Mollie refund overlay |
| `rewards_accounts` | V1.1 preview | Points balance header — **no spend MVP** |
| `rewards_ledger_entries` | V1.1 preview | Append-only points movements |
| `partner_merchants` | Post-MVP | Coalition redemption partners |
| `redemptions` | Post-MVP | Voucher/partner burn records |
| `staff_members` | Yes | Waiter/manager/admin at venue |
| `staff_devices` | Yes | Staff console device registration |
| `service_signals` | Yes | Call-server / ready-to-order signals |
| `audit_log_entries` | Yes | Immutable ops/compliance trail |
| `webhook_events` | Yes | Inbound Mollie (and future) webhook store |
| `disputes` | Yes (manual queue) | Chargebacks, fraud, ops incidents |
| `incidents` | Yes | Platform/venue operational incidents |
| `mollie_connections` | Yes | OAuth tokens per restaurant |
| `menu_categories` | Yes | Menu structure |
| `menu_items` | Yes | Menu catalog (empty-table view) |

---

## 2. Core tenancy & location

### 2.1 `restaurants`

**Purpose:** Top-level tenant. Owns Mollie merchant connection, staff, venues, billing subscription.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | API: `rest_*` |
| `slug` | `varchar(64)` | UNIQUE, NOT NULL | URL-safe; e.g. `de-rekentafel-ams` |
| `legal_name` | `varchar(255)` | NOT NULL | KVK registration name |
| `trade_name` | `varchar(255)` | NOT NULL | Guest-facing |
| `kvk_number` | `varchar(8)` | NULL | NL Chamber of Commerce |
| `vat_number` | `varchar(14)` | NULL | NL BTW-id |
| `country_code` | `char(2)` | NOT NULL DEFAULT `'NL'` | ISO 3166-1 |
| `default_currency` | `char(3)` | NOT NULL DEFAULT `'EUR'` | MVP: EUR only |
| `status` | `restaurant_status` | NOT NULL | See §2.1.1 |
| `mollie_org_id` | `varchar(32)` | NULL | Set after Connect onboarding |
| `payments_enabled` | `boolean` | NOT NULL DEFAULT false | Gate guest checkout |
| `settings_json` | `jsonb` | NOT NULL DEFAULT `'{}'` | Service charge %, tip policy, VAT defaults |
| `created_at` | `timestamptz` | NOT NULL | |
| `updated_at` | `timestamptz` | NOT NULL | |
| `deleted_at` | `timestamptz` | NULL | Soft delete |

**Enum `restaurant_status`:** `DRAFT`, `ONBOARDING`, `ACTIVE`, `SUSPENDED`, `CHURNED`.

**Relationships:** 1:N `venues`, `staff_members`, `mollie_connections`; 1:1 `rewards_accounts` (platform-level, post-MVP).

**MVP vs post-MVP:** Multi-venue franchise parent org → V2 (`parent_restaurant_id` nullable FK).

---

### 2.2 `venues`

**Purpose:** Physical site. MVP pilot uses **one venue per restaurant**; schema supports multi-site chains.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `restaurant_id` | `uuid` | FK → restaurants, NOT NULL | Tenant scope |
| `name` | `varchar(255)` | NOT NULL | e.g. "Centrum" |
| `timezone` | `varchar(64)` | NOT NULL DEFAULT `'Europe/Amsterdam'` | |
| `address_line1` | `varchar(255)` | NULL | |
| `city` | `varchar(128)` | NULL | |
| `postal_code` | `varchar(16)` | NULL | |
| `geo_lat` | `numeric(9,6)` | NULL | Post-MVP geo gate |
| `geo_lng` | `numeric(9,6)` | NULL | |
| `is_active` | `boolean` | NOT NULL DEFAULT true | |
| `created_at` | `timestamptz` | NOT NULL | |

**Relationships:** 1:N `tables`, `menu_categories`, `dining_sessions`.

---

### 2.3 `tables`

**Purpose:** Persistent table identity. QR resolves to `(venue_id, table_number)`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `venue_id` | `uuid` | FK → venues, NOT NULL | |
| `table_code` | `varchar(16)` | NOT NULL | Guest-visible: `T12` |
| `section` | `varchar(64)` | NULL | e.g. "Terrace" |
| `seats` | `smallint` | NULL | Informational |
| `sort_order` | `int` | NOT NULL DEFAULT 0 | Admin UI |
| `is_active` | `boolean` | NOT NULL DEFAULT true | |
| `current_dining_session_id` | `uuid` | FK → dining_sessions, NULL | Denormalized hot path |
| `created_at` | `timestamptz` | NOT NULL | |

**Unique:** `(venue_id, table_code)`.

**State:** Derived from active `dining_sessions.state` (`EMPTY`, `SEATED`, `PAYMENT_ACTIVE`, `CLOSED`).

---

### 2.4 `table_qr_codes`

**Purpose:** Persistent QR payload. **Never encodes live bill or payment token.**

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `table_id` | `uuid` | FK → tables, UNIQUE, NOT NULL | 1:1 MVP |
| `public_slug` | `varchar(32)` | UNIQUE, NOT NULL | URL segment |
| `qr_payload_url` | `text` | NOT NULL | `https://pay.example.nl/t/{slug}` |
| `version` | `int` | NOT NULL DEFAULT 1 | Bump on QR rotate |
| `rotated_at` | `timestamptz` | NULL | Fraud/compromise |
| `created_at` | `timestamptz` | NOT NULL | |

**Hot path:** `GET /t/{public_slug}` → join lookup index on `public_slug`.

---

## 3. Identity: users, guests, staff, devices

### 3.1 `users`

**Purpose:** Optional registered account (email/OAuth). Links to `participants` and `rewards_accounts`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `email` | `citext` | UNIQUE, NULL | Nullable for staff-only users |
| `email_verified_at` | `timestamptz` | NULL | |
| `phone_e164` | `varchar(16)` | UNIQUE, NULL | V1.1 magic link |
| `display_name` | `varchar(64)` | NULL | |
| `locale` | `varchar(8)` | NOT NULL DEFAULT `'nl-NL'` | |
| `status` | `user_status` | NOT NULL | `ACTIVE`, `SUSPENDED`, `DELETED` |
| `password_hash` | `text` | NULL | Staff/admin; guests OAuth-only V1.1 |
| `created_at` | `timestamptz` | NOT NULL | |
| `deleted_at` | `timestamptz` | NULL | GDPR erasure |

**MVP:** Guest checkout **does not require** `users` row.

---

### 3.2 `guest_devices`

**Purpose:** Anonymous device cookie (`guest_device_id` in event catalog). Rate limits, fraud signals.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | HTTP-only cookie |
| `fingerprint_hash` | `char(64)` | NULL | SHA-256 of UA + stable signals |
| `first_seen_at` | `timestamptz` | NOT NULL | |
| `last_seen_at` | `timestamptz` | NOT NULL | |
| `user_id` | `uuid` | FK → users, NULL | Set on account link |
| `ip_hash` | `char(64)` | NULL | Rotating /24 hash, 90d retention |

---

### 3.3 `staff_members`

**Purpose:** Venue staff with RBAC. Distinct from guest `users`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `restaurant_id` | `uuid` | FK, NOT NULL | |
| `venue_id` | `uuid` | FK, NULL | NULL = all venues |
| `user_id` | `uuid` | FK → users, NOT NULL | Login identity |
| `role` | `staff_role` | NOT NULL | See §3.3.1 |
| `employee_code` | `varchar(32)` | NULL | Internal HR ref |
| `pin_hash` | `text` | NULL | Manager override MVP |
| `is_active` | `boolean` | NOT NULL DEFAULT true | |
| `invited_at` | `timestamptz` | NULL | |
| `last_login_at` | `timestamptz` | NULL | |

**Enum `staff_role`:** `WAITER`, `MANAGER`, `ADMIN`, `PLATFORM_OPS` (platform-only, no FK to restaurant).

**Unique:** `(restaurant_id, user_id)`.

---

### 3.4 `staff_devices`

**Purpose:** Registered staff browsers/tablets for push notifications and session pinning.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `staff_member_id` | `uuid` | FK, NOT NULL | |
| `device_label` | `varchar(64)` | NULL | "iPad bar" |
| `push_token` | `text` | NULL | V1.1 |
| `last_active_at` | `timestamptz` | NOT NULL | |
| `created_at` | `timestamptz` | NOT NULL | |

---

## 4. Sessions

### 4.1 `dining_sessions`

**Purpose:** Waiter-controlled table lifecycle. Implements `TableSessionState` from split-engine.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `dining_session_id` |
| `table_id` | `uuid` | FK, NOT NULL | |
| `venue_id` | `uuid` | FK, NOT NULL | Denormalized tenant filter |
| `restaurant_id` | `uuid` | FK, NOT NULL | Denormalized tenant filter |
| `state` | `dining_session_state` | NOT NULL | §4.1.1 |
| `party_size` | `smallint` | NULL | Optional |
| `opened_by_staff_id` | `uuid` | FK → staff_members | |
| `closed_by_staff_id` | `uuid` | FK, NULL | |
| `opened_at` | `timestamptz` | NOT NULL | |
| `closed_at` | `timestamptz` | NULL | |
| `close_reason` | `close_reason_code` | NULL | `NORMAL`, `FORCE_CASH`, `WALKOUT`, `CANCEL` |
| `active_payment_session_id` | `uuid` | FK → payment_sessions, NULL | At most one active |
| `created_at` | `timestamptz` | NOT NULL | |

**Enum `dining_session_state`:** `EMPTY`, `SEATED`, `PAYMENT_ACTIVE`, `CLOSED`.

**Invariant:** Only one non-`CLOSED` session per `table_id` at a time (partial unique index).

**Example:** Table T12 Saturday 19:00 — `state=SEATED`, `party_size=4`. After activate payment → `PAYMENT_ACTIVE`.

---

### 4.2 `payment_sessions`

**Purpose:** Split-pay window. Parent of participants, bills, allocations, payments.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `payment_session_id` |
| `dining_session_id` | `uuid` | FK, NOT NULL | Alias: `table_session_id` |
| `bill_id` | `uuid` | FK → bills, NOT NULL | Frozen snapshot reference |
| `state` | `payment_session_state` | NOT NULL | §4.2.1 |
| `join_pin` | `char(6)` | NULL | Human backup code |
| `claims_frozen` | `boolean` | NOT NULL DEFAULT false | Waiter `LOCK_CLAIMS` |
| `opened_by_staff_id` | `uuid` | FK, NOT NULL | |
| `opened_at` | `timestamptz` | NOT NULL | |
| `completed_at` | `timestamptz` | NULL | When remaining = 0 |
| `created_at` | `timestamptz` | NOT NULL | |

**Enum `payment_session_state`:** `OPEN`, `PARTIALLY_PAID`, `FULLY_PAID`, `CLOSED`, `DISPUTED`.

**Settlement aggregates** (mirror payment-architecture §8.2) live on `bills`, not duplicated here.

---

### 4.3 `payment_session_tokens`

**Purpose:** `PaymentSessionToken` — join credential. **Raw token never stored**; only `token_hash`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Internal |
| `payment_session_id` | `uuid` | FK, NOT NULL | |
| `token_hash` | `char(64)` | UNIQUE, NOT NULL | SHA-256 of opaque token |
| `state` | `token_state` | NOT NULL | `ISSUED`, `EXPIRED`, `REVOKED` |
| `issued_at` | `timestamptz` | NOT NULL | |
| `expires_at` | `timestamptz` | NOT NULL | Default +2h |
| `revoked_at` | `timestamptz` | NULL | |
| `rotation_reason` | `varchar(32)` | NULL | `INITIAL`, `REFRESH`, `REVOKE` |
| `refresh_count` | `smallint` | NOT NULL DEFAULT 0 | Max 2 refreshes (6h cap) |

**MVP rule:** Bill lines not returned without valid token + `dining_session.state = PAYMENT_ACTIVE`.

---

### 4.4 `participants`

**Purpose:** Guest join entity (`Claimant` / `participant_id`). One row per guest device join.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `participant_id` |
| `payment_session_id` | `uuid` | FK, NOT NULL | |
| `guest_device_id` | `uuid` | FK, NOT NULL | |
| `user_id` | `uuid` | FK → users, NULL | Optional account |
| `display_name` | `varchar(32)` | NOT NULL | Nickname |
| `state` | `participant_state` | NOT NULL | §4.4.1 |
| `joined_at` | `timestamptz` | NOT NULL | |
| `left_at` | `timestamptz` | NULL | |
| `created_at` | `timestamptz` | NOT NULL | |

**Enum `participant_state`:** `JOINED`, `ALLOCATING`, `CHECKOUT_LOCKED`, `PAYMENT_PENDING`, `PAID`, `PAYMENT_FAILED`, `RELEASED`, `OVERRIDDEN`.

**Unique (active):** `(payment_session_id, guest_device_id)` WHERE `left_at IS NULL`.

---

## 5. Menu (empty-table QR)

### 5.1 `menu_categories` / 5.2 `menu_items`

**Purpose:** Static menu for empty-table scan. **Not** order cart.

**`menu_items` key fields:** `id`, `venue_id`, `category_id`, `name`, `description`, `price_display_cents` (informational), `vat_rate_bps`, `allergens_json`, `is_available`, `sort_order`.

**MVP:** Prices on menu may differ from waiter-entered bill lines (manual entry authoritative).

---

## 6. Orders (post-MVP schema)

### 6.1 `orders`

**Purpose:** Future POS/header sync. **No MVP application writes.**

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `dining_session_id` | `uuid` | FK |
| `external_pos_check_id` | `varchar(64)` | POS reference V1.1 |
| `source` | `order_source` | `MANUAL`, `POS_IMPORT`, `CSV` |
| `status` | `order_status` | `OPEN`, `CLOSED`, `VOID` |

### 6.2 `order_items`

**Purpose:** POS line mirror. Links to `bill_lines` via `order_item_id` nullable FK when synced.

---

## 7. Bills & split engine

### 7.1 `bills`

**Purpose:** Open check header + settlement aggregates (`TableBillSettlement`).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `payment_session_id` | `uuid` | FK, UNIQUE, NOT NULL | 1:1 per payment session |
| `dining_session_id` | `uuid` | FK, NOT NULL | |
| `restaurant_id` | `uuid` | FK, NOT NULL | |
| `currency` | `char(3)` | NOT NULL DEFAULT `'EUR'` | |
| `bill_version` | `int` | NOT NULL DEFAULT 1 | Optimistic concurrency |
| `settlement_state` | `bill_settlement_state` | NOT NULL | §7.1.1 |
| `menu_subtotal_cents` | `int` | NOT NULL DEFAULT 0 | Excl. service charge line |
| `service_charge_cents` | `int` | NOT NULL DEFAULT 0 | |
| `discount_cents` | `int` | NOT NULL DEFAULT 0 | Negative lines sum |
| `bill_grand_total_cents` | `int` | NOT NULL | Authoritative total |
| `allocated_cents` | `int` | NOT NULL DEFAULT 0 | Sum committed allocations |
| `confirmed_paid_cents` | `int` | NOT NULL DEFAULT 0 | Sum PAID payment_intents − refunds |
| `remaining_cents` | `int` | GENERATED ALWAYS AS (`bill_grand_total_cents` - `confirmed_paid_cents`) STORED | |
| `unclaimed_cents` | `int` | NOT NULL DEFAULT 0 | Maintained by trigger/job |
| `active_checkout_count` | `int` | NOT NULL DEFAULT 0 | |
| `locked_at` | `timestamptz` | NULL | Set on payment activation |
| `created_at` | `timestamptz` | NOT NULL | |
| `updated_at` | `timestamptz` | NOT NULL | |

**Enum `bill_settlement_state`:** `BILL_DRAFT`, `ALLOCATION_OPEN`, `ALLOCATION_FROZEN`, `CHECKOUT_IN_PROGRESS`, `PARTIALLY_PAID`, `FULLY_PAID`, `CLOSED`, `VOID`.

**Example (€86.40 table):** `bill_grand_total_cents=8640`, after 3 guests pay `confirmed_paid_cents=7190`, `remaining_cents=1450`.

---

### 7.2 `bill_lines`

**Purpose:** `BillLine` — menu/charge rows.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `line_id` |
| `bill_id` | `uuid` | FK, NOT NULL | |
| `line_kind` | `bill_line_kind` | NOT NULL | `MENU_ITEM`, `SERVICE_CHARGE`, `DISCOUNT`, `ROUNDING_ADJ`, `MANUAL_MISC` |
| `name` | `varchar(255)` | NOT NULL | |
| `qty` | `numeric(8,3)` | NOT NULL | Integer MVP except shared |
| `unit_price_inc_vat_cents` | `int` | NOT NULL | |
| `vat_rate_bps` | `int` | NOT NULL | 900 or 2100 NL MVP |
| `line_total_inc_vat_cents` | `int` | NOT NULL | |
| `splittable` | `boolean` | NOT NULL DEFAULT false | SHARED mode |
| `max_shares` | `smallint` | NULL | Default 20 if splittable |
| `menu_item_id` | `uuid` | FK, NULL | Optional link |
| `order_item_id` | `uuid` | FK, NULL | Post-MVP |
| `sort_order` | `int` | NOT NULL DEFAULT 0 | |
| `voided_at` | `timestamptz` | NULL | Soft void |

**Check:** `line_total_inc_vat_cents = round(qty * unit_price_inc_vat_cents)` with remainder policy on units.

---

### 7.3 `allocatable_units`

**Purpose:** `AllocatableUnit` — smallest claim slot.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `bill_line_id` | `uuid` | FK, NOT NULL | |
| `unit_index` | `smallint` | NOT NULL | 0..qty-1 |
| `unit_value_cents` | `int` | NOT NULL | Inc VAT; remainder distributed |
| `max_shares` | `smallint` | NOT NULL DEFAULT 1 | >1 for splittable lines |
| `created_at` | `timestamptz` | NOT NULL | |

**Unique:** `(bill_line_id, unit_index)`.

**Example:** Wine bottle €32.00 splittable → 1 unit, `max_shares=20`, `unit_value_cents=3200`.

---

### 7.4 `allocations`

**Purpose:** Maps unit/share → participant (`Allocation` / event `claim`).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `claim_id` |
| `bill_id` | `uuid` | FK, NOT NULL | |
| `bill_version` | `int` | NOT NULL | Snapshot at commit |
| `allocatable_unit_id` | `uuid` | FK, NOT NULL | |
| `participant_id` | `uuid` | FK → participants, NOT NULL | |
| `split_mode` | `split_mode` | NOT NULL | `ITEM`, `EQUAL`, `CUSTOM`, `SHARED` |
| `share_numerator` | `smallint` | NOT NULL DEFAULT 1 | SHARED: e.g. 5 of 20 |
| `share_denominator` | `smallint` | NOT NULL DEFAULT 1 | |
| `allocated_amount_cents` | `int` | NOT NULL | Inc VAT + SC share at commit |
| `service_charge_share_cents` | `int` | NOT NULL DEFAULT 0 | Pro-rata SC |
| `equal_group_id` | `uuid` | NULL | EQUAL mode grouping |
| `custom_pledge_id` | `uuid` | NULL | CUSTOM mode link |
| `state` | `allocation_state` | NOT NULL | `DRAFT`, `COMMITTED`, `LOCKED_FOR_CHECKOUT`, `RELEASED`, `INVALIDATED` |
| `version` | `int` | NOT NULL DEFAULT 1 | Optimistic lock |
| `committed_at` | `timestamptz` | NULL | |
| `released_at` | `timestamptz` | NULL | |
| `created_at` | `timestamptz` | NOT NULL | |

**Enum `split_mode`:** `ITEM`, `EQUAL`, `CUSTOM`, `SHARED`.

**Concurrency:** Unique partial index on `(allocatable_unit_id)` WHERE `state IN ('COMMITTED','LOCKED_FOR_CHECKOUT')` AND `share_numerator = share_denominator` (full unit claims).

**SHARED constraint:** Sum of `(share_numerator/share_denominator)` per unit ≤ 1 — enforced in transaction.

---

### 7.5 `custom_pledges`

**Purpose:** CUSTOM split fixed-€ pledges without line attachment.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `bill_id` | `uuid` | FK |
| `participant_id` | `uuid` | FK |
| `amount_cents` | `int` | NOT NULL |
| `state` | `pledge_state` | `ACTIVE`, `LOCKED`, `SETTLED`, `CANCELLED` |

---

## 8. Checkout & payments

### 8.1 `checkout_intents`

**Purpose:** `CheckoutIntent` — frozen allocation + tip snapshot before Mollie call.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `payment_session_id` | `uuid` | FK, NOT NULL | |
| `participant_id` | `uuid` | FK, UNIQUE (active) | One active per participant |
| `bill_id` | `uuid` | FK, NOT NULL | |
| `bill_version` | `int` | NOT NULL | |
| `subtotal_cents` | `int` | NOT NULL | Food + SC share |
| `tip_cents` | `int` | NOT NULL DEFAULT 0 | |
| `checkout_total_cents` | `int` | NOT NULL | Mollie amount |
| `allocation_snapshot_json` | `jsonb` | NOT NULL | Dispute reconstruction |
| `idempotency_key` | `varchar(128)` | UNIQUE, NOT NULL | |
| `state` | `checkout_intent_state` | NOT NULL | `ACTIVE`, `CONSUMED`, `EXPIRED`, `CANCELLED` |
| `expires_at` | `timestamptz` | NOT NULL | 15 min TTL |
| `created_at` | `timestamptz` | NOT NULL | |

---

### 8.2 `payment_intents`

**Purpose:** Mollie attempt lifecycle (payment-architecture §8.1).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | API: `pi_*` |
| `checkout_intent_id` | `uuid` | FK, NOT NULL | |
| `payment_session_id` | `uuid` | FK, NOT NULL | |
| `participant_id` | `uuid` | FK, NOT NULL | |
| `restaurant_id` | `uuid` | FK, NOT NULL | |
| `mollie_payment_id` | `varchar(32)` | UNIQUE, NULL | `tr_xxx` after create |
| `status` | `payment_intent_status` | NOT NULL | §8.2.1 |
| `amount_cents` | `int` | NOT NULL | Includes tip |
| `currency` | `char(3)` | NOT NULL | |
| `method` | `varchar(32)` | NULL | `ideal`, `creditcard`, etc. |
| `idempotency_key` | `varchar(128)` | UNIQUE, NOT NULL | |
| `bill_version` | `int` | NOT NULL | Stale checkout detection |
| `metadata_json` | `jsonb` | NOT NULL | Mirrors Mollie metadata |
| `mollie_checkout_url` | `text` | NULL | |
| `failure_reason` | `text` | NULL | |
| `paid_at` | `timestamptz` | NULL | |
| `expires_at` | `timestamptz` | NULL | Mollie open expiry |
| `created_at` | `timestamptz` | NOT NULL | |
| `updated_at` | `timestamptz` | NOT NULL | |

**Enum `payment_intent_status`:** `CREATING`, `MOLLIE_OPEN`, `PAID`, `FAILED`, `CANCELED`, `EXPIRED`, `FAILED_CREATE`, `PARTIALLY_REFUNDED`, `REFUNDED`, `CHARGEBACK`.

---

### 8.3 `payments`

**Purpose:** Immutable confirmed payment ledger (`PaymentRecord`). 1:1 with successful `payment_intents`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Event: `payment_id` |
| `payment_intent_id` | `uuid` | FK, UNIQUE, NOT NULL | |
| `mollie_payment_id` | `varchar(32)` | UNIQUE, NOT NULL | |
| `restaurant_id` | `uuid` | FK, NOT NULL | |
| `payment_session_id` | `uuid` | FK, NOT NULL | |
| `participant_id` | `uuid` | FK, NOT NULL | |
| `amount_cents` | `int` | NOT NULL | |
| `subtotal_share_cents` | `int` | NOT NULL | Excl. tip |
| `tip_cents` | `int` | NOT NULL DEFAULT 0 | |
| `method` | `varchar(32)` | NOT NULL | |
| `paid_at` | `timestamptz` | NOT NULL | Webhook time |
| `settlement_status` | `settlement_status` | NOT NULL | `PENDING`, `AVAILABLE`, `PAID_OUT` |
| `created_at` | `timestamptz` | NOT NULL | |

**Note:** `confirmed_paid_cents` on `bills` derives from this table minus refunds.

---

### 8.4 `tips`

**Purpose:** Tip breakdown for reporting (also embedded in checkout). 1:1 with `checkout_intents`.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `checkout_intent_id` | `uuid` | FK, UNIQUE |
| `payment_id` | `uuid` | FK, NULL until paid |
| `basis_cents` | `int` | Subtotal tip calculated on |
| `tip_cents` | `int` | |
| `tip_percent_bps` | `int` | NULL if fixed € |
| `destination` | `tip_destination` | `PASS_THROUGH`, `VENUE_POOL` |

---

### 8.5 `payment_refunds`

**Purpose:** Mollie refund overlay (MVP manual).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `payment_id` | `uuid` | FK |
| `mollie_refund_id` | `varchar(32)` | UNIQUE |
| `amount_cents` | `int` | |
| `status` | `refund_status` | `PENDING`, `COMPLETED`, `FAILED` |
| `initiated_by_staff_id` | `uuid` | FK |
| `reason` | `text` | |
| `created_at` | `timestamptz` | |

---

### 8.6 `mollie_connections`

**Purpose:** OAuth refresh tokens per restaurant (payment-architecture §3.1).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `restaurant_id` | `uuid` | FK, UNIQUE |
| `mollie_org_id` | `varchar(32)` | |
| `access_token_enc` | `bytea` | Encrypted |
| `refresh_token_enc` | `bytea` | Encrypted |
| `token_expires_at` | `timestamptz` | |
| `onboarding_status` | `varchar(32)` | |
| `scopes` | `text[]` | |
| `connected_at` | `timestamptz` | |

---

## 9. Rewards & partners (mostly post-MVP)

### 9.1 `rewards_accounts`

**Purpose:** Loyalty points header. **MVP: schema + accrual preview only; no spendable balance.**

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `user_id` | `uuid` | FK, UNIQUE |
| `points_balance` | `int` | NOT NULL DEFAULT 0 |
| `lifetime_points` | `int` | NOT NULL DEFAULT 0 |
| `status` | `rewards_account_status` | `ACTIVE`, `FROZEN`, `CLOSED` |

**Legal:** Do **not** implement stored EUR value or overpay credit (EMI risk).

---

### 9.2 `rewards_ledger_entries`

**Purpose:** Append-only points movements.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `rewards_account_id` | `uuid` | FK |
| `entry_type` | `rewards_entry_type` | `ACCRUAL`, `REVERSAL`, `REDEMPTION`, `ADJUSTMENT` |
| `points_delta` | `int` | |
| `payment_id` | `uuid` | FK, NULL |
| `redemption_id` | `uuid` | FK, NULL |
| `idempotency_key` | `varchar(128)` | UNIQUE |
| `created_at` | `timestamptz` | |

---

### 9.3 `partner_merchants` (post-MVP)

Coalition partners for voucher redemption. Fields: `id`, `name`, `slug`, `status`, `settlement_config_json`, `created_at`.

---

### 9.4 `redemptions` (post-MVP)

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `rewards_account_id` | `uuid` | FK |
| `partner_merchant_id` | `uuid` | FK |
| `offer_id` | `uuid` | |
| `points_spent` | `int` | |
| `voucher_code_hash` | `char(64)` | |
| `status` | `redemption_status` | `REQUESTED`, `ISSUED`, `REDEEMED`, `EXPIRED`, `CANCELLED` |
| `created_at` | `timestamptz` | |

---

## 10. Service signals

### 10.1 `service_signals`

**Purpose:** Empty-table "call server" / "ready to order" (Flow B).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `table_id` | `uuid` | FK |
| `guest_device_id` | `uuid` | FK |
| `signal_type` | `service_signal_type` | `READY_TO_ORDER`, `ASSISTANCE` |
| `status` | `signal_status` | `OPEN`, `ACKNOWLEDGED`, `EXPIRED` |
| `cooldown_until` | `timestamptz` | Rate limit |
| `acknowledged_by_staff_id` | `uuid` | FK, NULL |
| `created_at` | `timestamptz` | |

---

## 11. Audit, webhooks, disputes

### 11.1 `audit_log_entries`

**Purpose:** Immutable cross-domain audit (claims, overrides, admin actions).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK (UUID v7 recommended) |
| `restaurant_id` | `uuid` | FK, NULL for platform |
| `occurred_at` | `timestamptz` | NOT NULL |
| `actor_type` | `audit_actor_type` | `GUEST`, `STAFF`, `SYSTEM`, `MOLLIE_WEBHOOK` |
| `actor_id` | `uuid` | NULL |
| `action` | `varchar(64)` | e.g. `claim.admin_override` |
| `resource_type` | `varchar(64)` | |
| `resource_id` | `uuid` | |
| `correlation_id` | `uuid` | |
| `payload_json` | `jsonb` | Redacted PII |
| `ip_hash` | `char(64)` | NULL |

**Retention:** 7 years financial-adjacent; 90 days raw IP for fraud.

---

### 11.2 `webhook_events`

**Purpose:** Raw inbound webhook store before processing (Mollie MVP).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `source` | `webhook_source` | `MOLLIE`, `CRYPTO` (future) |
| `external_id` | `varchar(128)` | Mollie `tr_xxx` or event id |
| `idempotency_key` | `varchar(256)` | UNIQUE — `source:external_id:status` |
| `payload_json` | `jsonb` | NOT NULL |
| `signature_valid` | `boolean` | |
| `processing_status` | `webhook_processing_status` | `RECEIVED`, `PROCESSED`, `FAILED`, `SKIPPED_DUPLICATE` |
| `processed_at` | `timestamptz` | NULL |
| `error_message` | `text` | NULL |
| `received_at` | `timestamptz` | NOT NULL |

---

### 11.3 `disputes`

**Purpose:** Chargebacks, refund disputes, guest complaints tied to payments.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `payment_id` | `uuid` | FK |
| `restaurant_id` | `uuid` | FK |
| `dispute_type` | `dispute_type` | `CHARGEBACK`, `GUEST_COMPLAINT`, `REFUND_REQUEST` |
| `status` | `dispute_status` | `OPEN`, `EVIDENCE_GATHERING`, `WON`, `LOST`, `CLOSED` |
| `mollie_chargeback_id` | `varchar(32)` | NULL |
| `amount_cents` | `int` | |
| `assigned_ops_user_id` | `uuid` | NULL |
| `resolution_notes` | `text` | |
| `opened_at` | `timestamptz` | |
| `closed_at` | `timestamptz` | NULL |

---

### 11.4 `incidents`

**Purpose:** Operational/platform incidents (outages, webhook backlog, fraud spikes).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `uuid` | PK |
| `severity` | `incident_severity` | `SEV1`–`SEV4` |
| `title` | `varchar(255)` | |
| `description` | `text` | |
| `restaurant_id` | `uuid` | FK, NULL if global |
| `status` | `incident_status` | `OPEN`, `MITIGATING`, `RESOLVED` |
| `started_at` | `timestamptz` | |
| `resolved_at` | `timestamptz` | NULL |

---

## 12. Append-only event tables (implementation)

| Table | Purpose |
|-------|---------|
| `bill_state_events` | `TableBillSettlement` transitions (split-engine §9) |
| `dining_session_events` | Session state changes |
| `outbox_events` | Transactional outbox → workers (event catalog) |

**`bill_state_events` columns:** `id`, `bill_id`, `from_state`, `to_state`, `trigger`, `actor_staff_id`, `occurred_at`, `metadata_json`.

---

## 13. State machine reference (quick)

| Entity | States |
|--------|--------|
| `dining_sessions.state` | `EMPTY` → `SEATED` → `PAYMENT_ACTIVE` → `CLOSED` |
| `bills.settlement_state` | `BILL_DRAFT` → `ALLOCATION_OPEN` → … → `CLOSED` / `VOID` |
| `participants.state` | `JOINED` → `ALLOCATING` → `CHECKOUT_LOCKED` → `PAYMENT_PENDING` → `PAID` |
| `payment_intents.status` | `CREATING` → `MOLLIE_OPEN` → `PAID` / terminal failures |
| `payment_session_tokens.state` | `ISSUED` → `EXPIRED` / `REVOKED` |

Full diagrams: [state-machines.md](../../domain/split-engine/state-machines.md), [payment-architecture.md](../payments/payment-architecture.md).

---

## 14. MVP vs post-MVP entity usage

| Entity | MVP writes | Post-MVP |
|--------|------------|----------|
| `orders`, `order_items` | No | POS sync V1.1+ |
| `rewards_*` | Accrual only optional | Full loyalty V2 |
| `partner_merchants`, `redemptions` | No | Coalition marketplace |
| `users` | Optional | Preferred login V1.1 |
| Crypto payment tables | **Do not create** | Separate rail V2 — see payment doc |

---

## 15. Risks specific to this slice

| Risk | Entity impact | Mitigation |
|------|---------------|------------|
| Bill hijacking via QR | `table_qr_codes`, `payment_session_tokens` | Token required; no bill FK from QR alone |
| Double allocation | `allocatable_units`, `allocations` | Partial unique index + Redis lock |
| Stale checkout | `checkout_intents.bill_version`, `payment_intents.bill_version` | Reject if mismatch |
| Webhook duplicate | `webhook_events.idempotency_key`, `payment_intents.mollie_payment_id` UNIQUE | Idempotent worker |
| EMI / stored value | `rewards_accounts` | Points only; no EUR balance column |
| GDPR over-retention | `guest_devices`, `audit_log_entries` | TTL jobs; pseudonymize on `table.reset` |
| VAT audit failure | `bill_lines.vat_rate_bps`, allocation snapshots | Immutable `allocation_snapshot_json` |
| Registry drift | API aliases | Document `table_session_id` = `dining_session_id` |

---

## 16. NEW_REGISTRY_ENTRIES

| Name | Type | Description |
|------|------|-------------|
| `dining_session_id` | UUID | Canonical FK for table service session (replaces informal `table_session_id`) |
| `guest_device_id` | UUID | Anonymous device identity |
| `allocatable_unit_id` | UUID | Atomic claim slot |
| `allocation_id` | UUID | Synonym: `claim_id` in events |
| `checkout_intent_id` | UUID | Pre-Mollie frozen checkout |
| `payment_intent_id` | UUID | Mollie attempt row |
| `settlement_state` | enum | Bill settlement machine on `bills` |
| `public_slug` | string | QR URL lookup key |

---

*Slice ownership: Part 9 — Data Model. Exclusive files: `docs/architecture/data-model/*`.*
