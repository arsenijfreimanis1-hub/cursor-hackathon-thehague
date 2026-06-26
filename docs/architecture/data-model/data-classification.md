# Data Classification — PII & Payment Sensitivity

**Slice:** Part 9 — Data Model  
**Framework:** Four-tier tags applied per entity and field  
**Regulatory context:** GDPR (EU), PSD2/EMI boundaries (NL), PCI DSS (hosted checkout — platform out of card scope)

---

## 1. Classification tiers

| Tier | Label | Definition | Access | Encryption | Retention (default) |
|------|-------|------------|--------|------------|---------------------|
| **L0** | `public` | Safe to expose without auth (menu, table codes) | Unauthenticated guest API | TLS in transit | Indefinite |
| **L1** | `internal` | Business operational; no direct guest PII | Staff RBAC + tenant scope | TLS + DB at rest | Contract lifetime + 1y |
| **L2** | `confidential` | PII, pseudonymous identifiers, session tokens | Need-to-know; audit logged | TLS + at rest + field-level for secrets | GDPR-minimized; see §4 |
| **L3** | `restricted` | Payment credentials, OAuth tokens, full token hashes, financial audit | Platform ops + break-glass; no bulk export | AES-256 field encryption + KMS | 7y financial / PCI policy |

**Payment sensitivity** (orthogonal flag): `payment` = subject to PSD2 audit, 7-year retention, and Mollie reconciliation. Does not imply L3 unless credentials involved.

---

## 2. Entity-level classification summary

| Entity | Default tier | Payment flag | MVP | Notes |
|--------|--------------|--------------|-----|-------|
| `restaurants` | L1 | — | Yes | KVK/BTW = L2 fields |
| `venues` | L1 | — | Yes | Address = L2 |
| `tables` | L0 | — | Yes | `table_code` public in venue |
| `table_qr_codes` | L0 | — | Yes | `public_slug` is public by design |
| `menu_categories` | L0 | — | Yes | |
| `menu_items` | L0 | — | Yes | |
| `users` | L2 | — | Optional | Email, phone |
| `guest_devices` | L2 | — | Yes | Pseudonymous tracking |
| `staff_members` | L2 | — | Yes | Links to `users` |
| `staff_devices` | L2 | — | Yes | Push tokens L2 |
| `dining_sessions` | L1 | — | Yes | Operational |
| `payment_sessions` | L1 | payment | Yes | Join PIN = L2 |
| `payment_session_tokens` | L3 | payment | Yes | **Hash only**; raw token never stored |
| `participants` | L2 | payment | Yes | Nickname + device link |
| `bills` | L1 | payment | Yes | Amounts L1 in staff context |
| `bill_lines` | L1 | payment | Yes | |
| `allocatable_units` | L1 | payment | Yes | |
| `allocations` | L1 | payment | Yes | |
| `custom_pledges` | L1 | payment | Yes | |
| `checkout_intents` | L2 | payment | Yes | Snapshot may include nicknames |
| `payment_intents` | L2 | payment | Yes | Mollie IDs = L2 |
| `payments` | L2 | payment | Yes | 7y retention |
| `tips` | L1 | payment | Yes | |
| `payment_refunds` | L2 | payment | Manual MVP | |
| `mollie_connections` | L3 | payment | Yes | OAuth tokens encrypted |
| `rewards_accounts` | L2 | — | V1.1 | Points not EUR |
| `rewards_ledger_entries` | L2 | — | V1.1 | |
| `partner_merchants` | L1 | — | Post-MVP | |
| `redemptions` | L2 | — | Post-MVP | Voucher hashes L3 |
| `service_signals` | L2 | — | Yes | Device + table |
| `orders` / `order_items` | L1 | — | Schema only | |
| `audit_log_entries` | L2 | mixed | Yes | Payload redaction rules §3 |
| `webhook_events` | L2 | payment | Yes | Mollie payload |
| `disputes` | L2 | payment | Yes | |
| `incidents` | L1 | — | Yes | |
| `bill_state_events` | L1 | payment | Yes | Append-only |

---

## 3. Field-level classification (critical fields)

### 3.1 Identity & contact

| Entity.field | Tier | PII type | MVP retention |
|--------------|------|----------|---------------|
| `users.email` | L2 | Direct identifier | Until deletion request + 30d |
| `users.phone_e164` | L2 | Direct identifier | V1.1 |
| `users.display_name` | L2 | Personal | Same as account |
| `participants.display_name` | L2 | Pseudonymous | 90d after `table.reset` |
| `guest_devices.id` | L2 | Pseudonymous | 90d inactive purge |
| `guest_devices.fingerprint_hash` | L2 | Pseudonymous | 90d |
| `guest_devices.ip_hash` | L2 | Pseudonymous | 90d |
| `staff_members.pin_hash` | L3 | Auth secret | Until staff deactivated |

### 3.2 Session & access

| Entity.field | Tier | Notes |
|--------------|------|-------|
| `payment_session_tokens.token_hash` | L3 | SHA-256; treat as credential |
| `payment_sessions.join_pin` | L2 | 6-digit; rate-limit verify |
| `checkout_intents.idempotency_key` | L1 | No PII |
| `checkout_intents.allocation_snapshot_json` | L2 | Contains nicknames; redact in exports |

### 3.3 Payment & Mollie

| Entity.field | Tier | Payment | Retention |
|--------------|------|---------|-----------|
| `payment_intents.mollie_payment_id` | L2 | Yes | 7 years |
| `payment_intents.amount_cents` | L1 | Yes | 7 years |
| `payment_intents.metadata_json` | L2 | Yes | 7 years; no PAN |
| `payments.method` | L1 | Yes | 7 years (`ideal`, `creditcard`) |
| `mollie_connections.access_token_enc` | L3 | Yes | Until disconnect |
| `mollie_connections.refresh_token_enc` | L3 | Yes | Until disconnect |
| `webhook_events.payload_json` | L2 | Yes | 90d raw; 7y summarized in `payments` |
| `payment_refunds.mollie_refund_id` | L2 | Yes | 7 years |

**PCI note:** Platform uses Mollie hosted checkout — **no PAN, CVV, or card storage**. `method` type only = L1.

### 3.4 Restaurant legal

| Entity.field | Tier | Notes |
|--------------|------|-------|
| `restaurants.kvk_number` | L2 | Business identifier |
| `restaurants.vat_number` | L2 | Business identifier |
| `venues.address_line1` | L2 | Business address |

### 3.5 Audit & ops

| Entity.field | Tier | Redaction rule |
|--------------|------|----------------|
| `audit_log_entries.payload_json` | L2 | Strip email, phone, raw token, IP |
| `audit_log_entries.ip_hash` | L2 | Optional; 90d |
| `disputes.resolution_notes` | L2 | Staff-only |

---

## 4. Retention schedule

| Data class | Trigger | Action | MVP |
|------------|---------|--------|-----|
| Guest session artifacts | `table.reset` event | Pseudonymize `participants.display_name`; delete inactive `allocations` drafts | Yes |
| `guest_devices` | 90d no activity | Hard delete or anonymize | Yes |
| `service_signals` | 30d | Archive delete | Yes |
| `webhook_events.payload_json` | 90d | Delete payload; keep processing metadata | Yes |
| `payment_*`, `payments`, `bills` (closed) | 7 years | Legal hold; no early delete | Yes |
| `audit_log_entries` (financial) | 7 years | Immutable | Yes |
| `users` erasure request | GDPR Art. 17 | Delete PII; retain payment refs pseudonymized | V1.1 process |

**Event:** `table.reset` (event catalog) schedules GDPR retention job per `dining_session_id`.

---

## 5. Access control matrix

| Role | L0 | L1 | L2 | L3 |
|------|----|----|----|-----|
| Guest (valid token) | Read menu, own participant | Own bill slice, own checkout | Own nickname | — |
| Guest (no token) | Menu, table label | — | — | — |
| Waiter | — | Venue sessions, bills, signals | Participant nicknames | — |
| Manager | — | + refunds initiate | + audit read | — |
| Restaurant admin | — | + Mollie status (not tokens) | Staff PII | — |
| Platform ops | — | Cross-tenant incidents | Support with ticket | Break-glass OAuth rotate |

**Tenant isolation:** Every L1+ query MUST filter `restaurant_id` or `venue_id` from JWT/session — no cross-tenant joins.

---

## 6. Data flow & external sharing

| Destination | Data sent | Tier max | MVP |
|-------------|-----------|----------|-----|
| Mollie Payments API | Amount, description, metadata IDs | L1 | Yes |
| Mollie (response) | `tr_xxx`, status, method | L2 | Yes |
| Notion (screen observer) | **No raw payment data** | — | N/A this product |
| Restaurant Mollie Dashboard | Full payment (merchant) | L2 | Merchant-owned |
| Partner merchants | — | — | Post-MVP only |

**Metadata rule (payment-architecture):** Mollie `metadata` contains IDs only (`restaurant_id`, `payment_session_id`, `participant_id`) — no email, no nicknames.

---

## 7. Pseudonymization & hashing standards

| Field | Algorithm | Salt |
|-------|-----------|------|
| `payment_session_tokens.token_hash` | SHA-256 | Application pepper (KMS) |
| `guest_devices.fingerprint_hash` | SHA-256 | Per-deployment salt |
| `guest_devices.ip_hash` | SHA-256(/24 + daily salt) | Rotating |
| `staff_members.pin_hash` | Argon2id | Per-user salt |
| `redemptions.voucher_code_hash` | SHA-256 | Post-MVP |

**Never log:** raw payment session token, join PIN in plaintext, OAuth tokens, full credit card numbers (N/A).

---

## 8. GDPR lawful basis (by processing)

| Processing | Basis | Entity fields |
|------------|-------|---------------|
| Guest split-pay | Contract (meal payment) | `participants`, `payments`, `allocations` |
| Optional account | Consent | `users.email` |
| Fraud prevention | Legitimate interest | `guest_devices`, `ip_hash` |
| Financial record | Legal obligation | `payments`, `audit_log_entries` |
| Analytics (aggregated) | Legitimate interest | Counts only — no L2 export |
| Loyalty accrual | Consent / contract | `rewards_*` V1.1 |

**Profiling:** No recommendation/discovery profiling in MVP — no lawful basis required.

---

## 9. PSD2 / EMI boundary (payment classification)

| Stored data | EMI risk if mishandled | MVP policy |
|-------------|------------------------|------------|
| `payments.amount_cents` at restaurant Mollie | Low — merchant of record | Allowed |
| `rewards_accounts.points_balance` | Low if non-monetary | Accrual only |
| Hypothetical EUR wallet balance | **High — EMI** | **No column** |
| Platform pooled tips | Medium — money transmission | Pass-through metadata only |
| `mollie_connections` OAuth | L3 safeguarding | Encrypt; restaurant-scoped |

---

## 10. Breach impact by tier

| Tier | Example breach | Severity | Notification |
|------|----------------|----------|--------------|
| L0 | Menu scrape | Low | None |
| L1 | Bill totals leak for active table | Medium | Venue + guests if identifiable |
| L2 | Email + payment history | High | GDPR 72h assessment |
| L3 | OAuth token exfil | Critical | Revoke all tokens; DPA with Mollie |

---

## 11. MVP vs post-MVP classification changes

| Feature | New fields | Tier |
|---------|------------|------|
| Guest accounts V1.1 | `users` expansion | L2 |
| Geo join gate | `guest_devices.geo_attestation` | L2 |
| Crypto rail V2 | `crypto_payment_intents` (separate table) | L3 |
| Partner redemption | `redemptions.voucher_code_hash` | L3 |
| POS sync | `orders.external_pos_check_id` | L1 |

**Crypto (post-MVP):** Separate table namespace; not merged into `payment_intents` until AML review. Classification L3 for wallet addresses.

---

## 12. Export & DSR (Data Subject Request) checklist

| Request | Include | Exclude |
|---------|---------|---------|
| Access | User profile, rewards ledger, linked payments (amounts, dates) | Other guests' nicknames |
| Erasure | `users`, `guest_devices` link | Retain pseudonymous payment records 7y |
| Portability | JSON export L2 fields | L3 tokens, webhook raw payloads |

---

## 13. Field tagging convention (engineering)

Add SQL comments or codegen metadata:

```sql
COMMENT ON COLUMN payment_session_tokens.token_hash IS 'classification:L3 payment:credential';
COMMENT ON COLUMN participants.display_name IS 'classification:L2 payment:pseudonymous';
COMMENT ON COLUMN menu_items.name IS 'classification:L0';
```

API OpenAPI extension: `x-classification: confidential`.

---

*Slice ownership: Part 9 — Data Model. Cross-ref: [entity-dictionary.md](./entity-dictionary.md), [payment-architecture.md](../payments/payment-architecture.md).*
