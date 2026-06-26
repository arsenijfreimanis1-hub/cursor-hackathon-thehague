# Auth and Sessions

**Product (working name):** Rekentafel  
**Slice:** Part 10 — API / Backend Design  
**Cross-references:** [service-map.md](./service-map.md), [flows-a-o.md](../../flows/flows-a-o.md), [rules-spec.md](../../domain/split-engine/rules-spec.md) §2

---

## 1. Overview

Three distinct auth domains share one API gateway but **never share tokens**:

| Domain | Token type | Lifetime | Account required |
|--------|------------|----------|------------------|
| Guest (ephemeral) | `GuestSession` JWT + device cookie | 24h device; payment session bound | No (MVP) |
| Staff | `StaffSession` JWT | 8h shift; refresh 7d | Yes |
| Admin / platform | `AdminSession` JWT | 8h; refresh 7d | Yes |

**Security invariant:** Live bill access requires **valid `PaymentSessionToken`** in addition to guest session — scanning table QR alone is insufficient.

---

## 2. Guest ephemeral session model

### 2.1 Identity layers

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: guest_device_id (HttpOnly cookie, 365 days)    │
│         Anonymous device fingerprint — no PII             │
├─────────────────────────────────────────────────────────┤
│ Layer 2: guest_session JWT (24h)                        │
│         Issued on first visit; carries device_id          │
├─────────────────────────────────────────────────────────┤
│ Layer 3: payment_session_token (2h, waiter-issued)      │
│         Required for bill view + claims + pay           │
├─────────────────────────────────────────────────────────┤
│ Layer 4: participant_id (UUID, payment session scope)   │
│         Created on join; nickname display only          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Guest device cookie

| Attribute | Value |
|-----------|-------|
| Name | `rt_device` |
| Format | UUID v7 |
| Flags | `HttpOnly`, `Secure`, `SameSite=Lax` |
| Path | `/` |
| Max-Age | 365 days |
| Storage | `guest_devices` table (hash optional post-MVP) |

**Created:** First `GET /t/{slug}/{table_code}` without existing cookie.

**Purpose:** Rate limiting, service signal dedup, optional account merge (V1.1).

**GDPR:** Device ID alone is not PII; linked to `user_id` only after explicit consent.

### 2.3 Guest session JWT

**Issued:** Same first visit or refresh on each authenticated guest request.

**Claims:**

```json
{
  "sub": "guest_device_id",
  "typ": "guest",
  "iat": 1719408000,
  "exp": 1719494400,
  "jti": "uuid"
}
```

**Header:** `Authorization: Bearer <guest_jwt>`

**Not required for:** Empty-table menu view (`GET /t/...`), service signals (device cookie sufficient).

**Required for:** Payment session join, claims, checkout.

### 2.4 Payment session token (join gate)

Waiter-issued secret; **not** the same as guest JWT.

| Field | Rule |
|-------|------|
| Raw token | 32-byte base64url; shown in staff UI QR overlay |
| `join_pin` | 6 digits; alternative join path |
| TTL | **2 hours** default; refresh +2h (max 6h cumulative) |
| Binding | `payment_session_id`, `restaurant_id`, `table_id`, `bill_id` |
| Revocation | Table close, waiter revoke, expiry |

**Validation flow:**

```
POST /v1/payment-sessions/join
{
  "payment_session_id": "uuid",      // from deep link
  "token": "raw_token_or_pin",       // token OR join_pin
  "token_type": "secret | pin",
  "display_name": "Anna",
  "guest_device_id": "from cookie"
}
```

**Server checks:**
1. `token_hash` matches OR `join_pin` bcrypt verify
2. `expires_at > now()` AND `revoked_at IS NULL`
3. `payment_session.status = OPEN`
4. `TableSessionState = PAYMENT_ACTIVE`
5. `participants.count < max_joins` (default 12)

**Response:** `participant_id`, scoped `payment_session_jwt` (short-lived, 2h, claims include `ps_id`, `participant_id`).

### 2.5 Payment session JWT (scoped)

```json
{
  "sub": "participant_id",
  "typ": "payment_participant",
  "ps_id": "payment_session_id",
  "bill_id": "uuid",
  "restaurant_id": "uuid",
  "table_id": "uuid",
  "exp": 1719415200
}
```

**Required on:** All `/payment-sessions/{id}/claims/*`, `/checkout`, `/participants/me`.

**Invalidated when:** Token revoked, session closed, participant released.

### 2.6 Optional account linking (MVP minimal)

| Step | MVP | V1.1 |
|------|-----|------|
| Pay without account | ✓ | ✓ |
| Email receipt opt-in | ✓ post-checkout | ✓ |
| Link visit to account | Post-payment magic link | Pre-join login |
| Loyalty accrual | Requires link | Auto on login |

**Link flow (MVP):**

```
POST /v1/accounts/link-from-session
Authorization: Bearer <payment_participant_jwt>
{ "email": "guest@example.com" }

→ Sends OTP email
→ POST /v1/accounts/verify-otp { "email", "code" }
→ Sets user_id on participant + guest_device
→ Emits account.linked
```

**No password in MVP.** Magic link / OTP only.

**Regulatory:** Do not store payment credentials; Mollie handles PCI. Account stores email + consent timestamp only.

---

## 3. Staff and admin auth model

### 3.1 Staff roles (restaurant-scoped RBAC)

| Role | Code | Scope |
|------|------|-------|
| Waiter | `waiter` | Assigned tables, session control, bill entry, signals |
| Manager | `manager` | All tables, overrides, refunds, force close, staff view |
| Restaurant admin | `restaurant_admin` | Menu, tables, staff invites, Mollie connect, settings |
| Platform ops | `platform_ops` | Cross-tenant read + pilot provisioning |

**One user may hold one role per restaurant.** Multi-venue staff is post-MVP.

### 3.2 Permission matrix (MVP)

| Action | waiter | manager | restaurant_admin | platform_ops |
|--------|--------|---------|------------------|--------------|
| View table list | ✓ | ✓ | ✓ | ✓ |
| Start dining session | ✓ | ✓ | ✓ | — |
| Enter/edit bill | ✓ | ✓ | ✓ | — |
| Activate payment mode | ✓ | ✓ | ✓ | — |
| Refresh payment token | ✓ | ✓ | ✓ | — |
| Ack service signal | ✓ | ✓ | ✓ | — |
| Override claims | — | ✓ | ✓ | — |
| Force close table | — | ✓ | ✓ | — |
| Initiate refund | — | ✓ | ✓ | — |
| Manage menu/tables | — | — | ✓ | — |
| Invite staff | — | — | ✓ | — |
| Mollie connect | — | — | ✓ | — |
| View audit export | — | ✓ | ✓ | ✓ |
| Provision restaurant | — | — | — | ✓ |

### 3.3 Staff JWT

**Login:** `POST /v1/staff/auth/login` → `{ email, password }` (pilot) or magic link.

**Claims:**

```json
{
  "sub": "staff_user_id",
  "typ": "staff",
  "restaurant_id": "uuid",
  "role": "waiter",
  "permissions": ["session:start", "bill:write", "payment:activate"],
  "iat": 1719408000,
  "exp": 1719436800
}
```

**Refresh:** `POST /v1/staff/auth/refresh` with HttpOnly refresh token.

**Tenant isolation:** Every staff request validates `restaurant_id` in JWT matches resource `restaurant_id`. Cross-tenant access returns `404` (not `403`) to prevent enumeration.

### 3.4 Manager PIN (sensitive actions)

Force close, large refund, bill void require re-entry of **manager PIN** (4–6 digits, bcrypt):

```
Header: X-Manager-PIN: 123456
```

Only valid if JWT role is `manager` or `restaurant_admin`. Logged in audit with `pin_verified: true`.

**UX:** Staff app caches PIN for 15 minutes per device after first entry.

### 3.5 Platform ops JWT

Separate issuer (`iss: rekentafel-platform`), `platform_ops` role, no `restaurant_id` in token — must specify `?restaurant_id=` on cross-tenant reads.

---

## 4. Auth middleware chain

```
Request
  → request-id
  → rate-limit (by IP / device / staff user)
  → authenticate (route-specific):
       public routes → optional guest cookie
       /staff/* → StaffSession JWT
       /admin/* → AdminSession JWT + restaurant scope
       /payment-sessions/{id}/* → PaymentParticipant JWT
       /webhooks/* → Mollie verification (no JWT)
  → authorize (RBAC check)
  → idempotency (mutations)
  → handler
```

### 4.1 Public routes (no auth)

| Route | Notes |
|-------|-------|
| `GET /t/{slug}/{table_code}` | Menu + table context |
| `POST /tables/{id}/service-signals` | Device cookie + rate limit |
| `POST /webhooks/mollie` | Signature verify |
| `GET /health` | — |

### 4.2 Webhook auth (Mollie)

Mollie does not sign webhooks with HMAC in all modes. MVP verification:

1. Accept `POST` with `id=tr_xxx` body
2. Respond `200` immediately
3. Worker fetches payment from Mollie API with restaurant OAuth token
4. Reject if payment ID unknown locally

**Post-MVP:** IP allowlist + optional shared secret header if Mollie enables.

---

## 5. Session state vs auth token

Do not conflate **table session state** with **auth tokens**:

| Concept | Type | Example |
|---------|------|---------|
| `TableSessionState` | Domain enum | `PAYMENT_ACTIVE` |
| `DiningSession` | DB entity | Waiter started at 19:04 |
| `PaymentSession` | DB entity | Opened at 20:45, expires 22:45 |
| `PaymentSessionToken` | Join secret | Waiter-issued |
| `payment_participant_jwt` | Auth credential | Guest Anna's API access |

Guest can hold valid `payment_participant_jwt` while waiter has frozen claims (`ALLOCATION_FROZEN`) — auth succeeds, business rules return `423`.

---

## 6. Token lifecycle state machines

### 6.1 PaymentSessionToken

```
ISSUED ──(TTL)──► EXPIRED
  │                  │
  │ refresh          │ refresh (waiter)
  ▼                  ▼
ISSUED ◄─────────────┘
  │
  │ close / revoke
  ▼
REVOKED (terminal)
```

| State | Join | Claims | Checkout | Webhook honor |
|-------|------|--------|----------|---------------|
| ISSUED | ✓ | ✓ | ✓ | ✓ |
| EXPIRED | View-only stale | ✗ | ✗ (in-flight OK) | ✓ |
| REVOKED | ✗ | ✗ | ✗ | ✓ |

### 6.2 Participant session

```
JOINED → ACTIVE → CHECKOUT → PAID (terminal)
              ↘ RELEASED (left voluntarily)
              ↘ OVERRIDDEN (staff cleared)
```

Participant JWT invalidated on `RELEASED`, `OVERRIDDEN`, or payment session `CLOSED`.

---

## 7. Fraud and abuse controls (auth layer)

| Vector | Control | MVP |
|--------|---------|-----|
| QR scan from home | No bill without token | ✓ |
| Brute-force join PIN | 5 attempts / 15 min / session; lockout 30 min | ✓ |
| Token sharing (social) | Intended — waiter shares with table; audit join count | ✓ |
| Stolen participant JWT | Short TTL; bound to `ps_id`; HttpOnly where possible | ✓ |
| Staff credential stuffing | Rate limit login; optional 2FA V1.1 | ✓ rate limit |
| Cross-table token reuse | Token bound to `payment_session_id` | ✓ |
| Geo hijack | Not in MVP | V1.1 optional |

**Bill hijacking risk:** Anyone with `join_pin` or payment URL can join. Mitigation is **operational** (waiter only shares when guests seated), not cryptographic. Document in staff training.

---

## 8. GDPR and retention

| Data | Retention | Erasure |
|------|-----------|---------|
| `guest_device_id` | 365 days inactive purge | On request if linked to account |
| `display_name` | Payment session + 90 days | Anonymize |
| `participant_id` | 7 years (financial audit trail) | Pseudonymize PII fields |
| Staff email | Account lifetime | Standard HR process |
| JWT `jti` | 24h | Auto-expire |

Guest receipt email: store only if opt-in; basis = consent.

---

## 9. MVP vs post-MVP auth

| Capability | MVP | V1.1 | V2 |
|------------|-----|------|-----|
| Guest pay without account | ✓ | ✓ | ✓ |
| Email OTP accounts | Minimal | Full | Social login |
| Staff password login | ✓ | +2FA option | SSO |
| Manager PIN | ✓ | ✓ | ✓ |
| Geo join gate | — | Optional | — |
| OAuth for guests | — | — | Apple/Google |
| API keys for POS | — | Read-only import | Bi-directional |
| Crypto wallet auth | **Never MVP** | — | Separate rail |

---

## 10. Example auth sequence (numeric)

**Table 12, 4 guests, waiter opens payment at 20:45 CET**

| Time | Actor | Action | Credential used |
|------|-------|--------|-----------------|
| 20:45 | Waiter | `POST .../payment-sessions` | Staff JWT (`waiter`) |
| 20:45 | System | Issues token + PIN `482917` | — |
| 20:46 | Anna | Scans QR + enters PIN | Device cookie → guest JWT |
| 20:46 | Anna | `POST .../join` | PIN → `participant_id` p1, participant JWT |
| 20:47 | Boris | Joins via URL `#ps=...` | Same flow → p2 |
| 20:50 | Anna | `POST .../claims` | Participant JWT (p1) |
| 20:52 | Anna | `POST .../checkout` | Participant JWT + Idempotency-Key |
| 20:53 | Anna | Mollie redirect return | Guest JWT (poll only) |
| 20:53 | Mollie | Webhook | No JWT — async verify |
| 21:10 | Manager | Force close remainder | Staff JWT (`manager`) + PIN |

---

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Payment token in server logs | Bill exposure | Log `token_hash` only |
| Guest JWT in localStorage | XSS theft | Prefer HttpOnly cookie transport for participant JWT |
| Shared PIN at loud venue | Eavesdropping | Rotate PIN on refresh; optional per-guest links V1.1 |
| Staff JWT without step-up on refund | Fraud | Manager PIN + audit |
| Account linking without verification | Wrong history merge | OTP required |

---

*Slice ownership: Part 10 — API / Backend Design.*
