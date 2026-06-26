# PART 11 — Security Control Matrix

**Product (working name):** Rekentafel  
**Slice:** Part 11 — Security / Fraud / Abuse  
**Cross-references:** [threat-register.md](./threat-register.md), [concurrency.md](../domain/split-engine/concurrency.md), [auth-and-sessions.md](../architecture/api/auth-and-sessions.md)

**Purpose:** Map each threat to concrete controls with implementation notes. Every mitigation in [threat-register.md](./threat-register.md) appears here with a control ID. Tags: **MVP** = required for pilot launch; **Later** = post-pilot or feature-gated.

---

## 1. Control catalog

| Control ID | Control name | Type | MVP | Description |
|------------|--------------|------|-----|-------------|
| C-01 | Public menu surface isolation | Preventive | ✓ | Empty-table QR returns menu/signals only; no bill fields in API |
| C-02 | PaymentSessionToken join gate | Preventive | ✓ | Waiter-issued 32-byte secret + optional 6-digit PIN; 2h TTL |
| C-03 | Token hash-at-rest | Preventive | ✓ | SHA-256 + pepper; raw token shown once in staff UI |
| C-04 | Payment session binding | Preventive | ✓ | Token scoped to `(restaurant_id, table_id, bill_id, payment_session_id)` |
| C-05 | Token lifecycle state machine | Preventive | ✓ | ISSUED → EXPIRED / REVOKED; join blocked when not ISSUED |
| C-06 | Participant JWT scoping | Preventive | ✓ | RS256 JWT with `ps_id`, `participant_id`, 2h TTL |
| C-07 | Join PIN brute-force limit | Detective + Preventive | ✓ | 5 fails / 15 min / session; 30 min lockout |
| C-08 | Redis claim lock | Preventive | ✓ | `claim:lock:{bill_id}:{unit_id}` NX EX 30s |
| C-09 | DB allocation uniqueness | Preventive | ✓ | One active allocation per `AllocatableUnit` |
| C-10 | Bill version optimistic lock | Preventive | ✓ | `bill_version` increment; stale → 409 |
| C-11 | Idempotency keys (mutations) | Preventive | ✓ | Required on claims, checkout, splits; 24h cache |
| C-12 | Checkout lock | Preventive | ✓ | `checkout:lock:{bill_id}:{claimant_id}` NX EX 900s |
| C-13 | SHARED share sum constraint | Preventive | ✓ | `sum(shares) ≤ 1.0`; serializable / FOR UPDATE |
| C-14 | Equal-split bill lock | Preventive | ✓ | `bill:split:lock:{bill_id}` NX EX 10s |
| C-15 | Waiter admin lock + override | Corrective | ✓ | `bill:admin:lock:{bill_id}` 60s; manager PIN |
| C-16 | ALLOCATION_FROZEN gate | Preventive | ✓ | Staff can pause claims during dispute |
| C-17 | Mollie webhook fetch-verify | Preventive | ✓ | Async GET payment; never trust POST body alone |
| C-18 | Webhook idempotency store | Preventive | ✓ | `processed_webhooks` PK prevents double credit |
| C-19 | Server-side tax/total calc | Preventive | ✓ | Client display-only; Mollie amount from CheckoutIntent |
| C-20 | Staff RBAC + tenant isolation | Preventive | ✓ | Role matrix; cross-tenant 404 |
| C-21 | Manager PIN step-up | Preventive | ✓ | Refund, force close, void require PIN |
| C-22 | Refund manager-only | Preventive | ✓ | No guest self-service refund in MVP |
| C-23 | Audit log (immutable) | Detective | ✓ | Staff actions, overrides, refunds, token issue/rotate |
| C-24 | Rate limits (guest) | Preventive | ✓ | IP + device limits on join, signals, login |
| C-25 | Rate limits (staff login) | Preventive | ✓ | 10 fails / IP / hour |
| C-26 | HSTS + CSP | Preventive | ✓ | Guest app; no inline scripts in pay path |
| C-27 | Venue/table display verification | Preventive | ✓ | Prominent venue name on all guest screens |
| C-28 | Mollie hosted checkout only | Preventive | ✓ | No PAN on platform; PCI SAQ-A scope |
| C-29 | Session expiry cron | Preventive | ✓ | `session.expire_payment_sessions` */5 min |
| C-30 | Log scrubbing (secrets) | Preventive | ✓ | No raw tokens/PINs in logs; CI lint |
| C-31 | Hijack monitoring | Detective | ✓ | Alert `409_rate` >15% / session; join count anomaly |
| C-32 | Reconciliation worker | Detective | ✓ | Daily Mollie vs ledger; orphan_payment queue |
| C-33 | Dispute evidence pack | Corrective | ✓ | Store join meta, allocations, timestamps per payment |
| C-34 | Service signal rate limit | Preventive | ✓ | 3 / 10 min / device / table |
| C-35 | Guest OTP account link | Preventive | ✓ | Magic link / OTP; no password MVP |
| C-36 | Feature exclusion gates | Preventive | ✓ | Crypto, wallet, promo routes return 501 NOT_MVP |
| C-37 | Geo / SSID join gate | Preventive | — | Optional 100 m fence or venue WiFi hint |
| C-38 | Signed QR payload | Preventive | — | HMAC on QR URL params |
| C-39 | Per-guest join links | Preventive | — | Single-use URLs instead of shared PIN |
| C-40 | Staff 2FA | Preventive | — | TOTP for manager/admin roles |
| C-41 | Cross-venue device blocklist | Detective | — | Block repeat chargeback devices |
| C-42 | Loyalty velocity limits | Preventive | — | Accrual caps when loyalty ships |
| C-43 | Promo code entropy + caps | Preventive | — | When promo engine exists |
| C-44 | Crypto PSP AML delegation | Preventive | — | Licensed PSP KYC; Travel Rule |
| C-45 | POS import HMAC | Preventive | — | Signed bill import webhooks |
| C-46 | Mollie webhook IP allowlist | Preventive | — | Network layer on webhook ingress |
| C-47 | Real-time SSE bill sync | Detective | — | Guaranteed push on override (V1.1) |
| C-48 | Chargeback scoring | Detective | — | Risk score before checkout (multi-venue) |

---

## 2. Threat → control mapping

| Threat ID | Threat (short) | Controls | MVP sufficient? |
|-----------|----------------|----------|-----------------|
| T-01 | Outsider QR (empty) | C-01, C-34, C-24 | ✓ |
| T-02 | Outsider QR (payment) | C-02, C-04, C-05, C-06 | ✓ (C-37 optional boost) |
| T-03 | Bill hijacking (leaked secret) | C-02, C-05, C-07, C-15, C-16, C-23, C-31, C-27 | ✓ ops + tech; C-37/C-39 Later |
| T-04 | Malicious claiming | C-08, C-09, C-15, C-16, C-23 | ✓ |
| T-05 | Concurrent claim race | C-08, C-09, C-10, C-11, C-13 | ✓ See [concurrency.md](../domain/split-engine/concurrency.md) |
| T-06 | Stale / cross-table session | C-04, C-05, C-29 | ✓ |
| T-07 | API replay | C-11, C-12, C-18 | ✓ |
| T-08 | Token replay | C-03, C-05, C-06 | ✓ |
| T-09 | QR sticker swap | C-27, C-26, ops SOP | ✓; C-38 Later |
| T-10 | URL injection / phishing | C-26, C-28, C-27 | ✓ |
| T-11 | Fake payment UI | C-28, C-27 | ✓ |
| T-12 | Spoofed participant JWT | C-06, C-20 | ✓ |
| T-13 | Spoofed webhook | C-17, C-18, C-32 | ✓; C-46 Later |
| T-14 | Rewards farming | C-36, C-42 | N/A MVP |
| T-15 | Overpay wallet farming | C-36 | N/A MVP |
| T-16 | Guest refund abuse | C-22, C-33, C-23 | ✓ |
| T-17 | Staff refund collusion | C-21, C-22, C-23, C-32 | ✓ |
| T-18 | Friendly fraud chargeback | C-33, C-28, C-23 | ✓; C-48 Later |
| T-19 | Serial chargeback | C-41, C-48 | Later |
| T-20 | Bill inflation | C-23, C-20 | ✓ |
| T-21 | Withhold payment mode | C-23, metrics | ✓ |
| T-22 | Override theft | C-15, C-21, C-23 | ✓ |
| T-23 | Guest ATO | C-35, C-24 | ✓ |
| T-24 | Staff ATO | C-25, C-20, C-40 | MVP partial; 2FA Later |
| T-25 | Wallet abuse | C-36 | N/A MVP |
| T-26 | Promo abuse | C-43, C-36 | N/A MVP |
| T-27 | Crypto AML | C-36, C-44 | N/A MVP |
| T-28 | Signal spam | C-34 | ✓ |
| T-29 | PIN brute force | C-07 | ✓ |
| T-30 | Partial pay abandon | C-15, C-29, C-21 | ✓ |
| T-31 | VAT manipulation | C-19 | ✓ |
| T-32 | Session fixation | C-06, cookie flags | ✓ |
| T-33 | Token in logs | C-30, C-03 | ✓ |
| T-34 | POS import tamper | C-45 | Later |

---

## 3. PaymentSessionToken controls (detailed)

### 3.1 Issuance

| Step | Control | Implementation |
|------|---------|----------------|
| Waiter taps Open payment | C-20 RBAC | `payment_session:open` permission |
| System generates secret | C-02 | 32-byte CSPRNG → base64url |
| Persist | C-03 | Store SHA-256(secret + pepper) |
| Display | C-30 | Staff UI shows raw once; QR overlay encodes join URL fragment |
| PIN | C-02, C-07 | 6-digit CSPRNG; bcrypt hash stored |

### 3.2 Validation (join)

```
POST /v1/payment-sessions/join
Controls: C-02, C-04, C-05, C-07, C-24

1. Rate limit by IP + device (C-24)
2. Verify token_hash OR join_pin (C-02, C-03)
3. Check expires_at, revoked_at, status=OPEN (C-05)
4. Verify TableSessionState=PAYMENT_ACTIVE (C-04)
5. Increment PIN attempt counter (C-07)
6. Issue participant JWT (C-06)
7. Audit: participant.joined (C-23)
```

### 3.3 Rotation and revocation

| Action | Controls | Effect |
|--------|----------|--------|
| Waiter refresh | C-05, C-23 | Old token REVOKED; new ISSUED |
| Table close | C-05, C-29 | All tokens REVOKED |
| Manager cancel payment | C-05, C-21 | REVOKED if no successful payments |

Reference: [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §2.4, §6.1.

---

## 4. Claim lock controls (detailed)

Bill hijacking and concurrent claim races share the split-engine concurrency stack.

### 4.1 Control flow

```
POST /payment-sessions/{id}/claims
Controls: C-06, C-08, C-09, C-10, C-11, C-16

1. Authorize payment_participant_jwt (C-06)
2. Reject if ALLOCATION_FROZEN (C-16)
3. Idempotency cache lookup (C-11)
4. Redis SET claim:lock:{bill_id}:{unit_id} NX EX 30 (C-08)
5. BEGIN; SELECT allocation FOR unit; verify bill_version (C-09, C-10)
6. INSERT/UPDATE allocation
7. COMMIT; release lock with Lua compare-and-del (C-08)
8. Audit claim outcome (C-23)
```

Full algorithm: [concurrency.md](../domain/split-engine/concurrency.md) §4.2.

### 4.2 Bill hijacking response controls

| Detection signal | Control | Response |
|------------------|---------|----------|
| `participants.count > 8` | C-31 | Staff alert banner |
| `409_rate > 15%` | C-31 | Ops log review |
| Unknown nickname claims high value | C-16, C-15 | Waiter freeze → override |
| Join from distant IP (Later) | C-37 | Optional block or CAPTCHA |

### 4.3 Concurrent race acceptance test

| Test | Control IDs | Pass |
|------|-------------|------|
| 50 parallel claims, 1 unit | C-08, C-09, C-11 | 1 success, 49 × 409 |
| Redis failure fallback | C-08, C-09 | DB FOR UPDATE only; no double alloc |

Reference: [concurrency.md](../domain/split-engine/concurrency.md) §13.

---

## 5. Payment and Mollie controls

| Stage | Threat | Controls |
|-------|--------|----------|
| Checkout create | T-07 double pay | C-11, C-12, C-19 |
| Redirect | T-11 fake UI | C-28 |
| Webhook | T-13 spoof | C-17, C-18 |
| Settlement | T-18 chargeback | C-33, C-32 |
| Refund | T-16, T-17 | C-21, C-22, C-23 |

**Mollie metadata (C-33):** `restaurant_id`, `payment_session_id`, `participant_id`, `checkout_intent_id`, `allocation_snapshot_hash` — no PII.

**Crypto (T-27):** C-36 blocks all crypto endpoints MVP; C-44 applies only when [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) rail is licensed separately.

---

## 6. Staff and insider controls

| Role | Sensitive action | Controls |
|------|------------------|----------|
| waiter | Open payment / issue token | C-20, C-23 |
| waiter | Edit bill | C-20, C-23 |
| manager | Override claims | C-15, C-21, C-23 |
| manager | Refund | C-21, C-22, C-23, C-32 |
| manager | Force close | C-21, C-23 |
| restaurant_admin | Mollie connect | C-20, C-23 |
| platform_ops | Cross-tenant read | C-20, separate issuer |

---

## 7. MVP vs Later control rollout

| Domain | MVP controls | Later additions |
|--------|--------------|-----------------|
| Session join | C-02–C-07, C-24 | C-37 geo, C-39 per-guest links |
| Split engine | C-08–C-16 | C-47 guaranteed SSE |
| Payments | C-17–C-19, C-28, C-33 | C-46 IP allowlist, C-48 scoring |
| Identity | C-20–C-25, C-35 | C-40 2FA |
| Abuse features | C-36 exclude | C-42 loyalty, C-43 promo |
| Crypto | C-36 | C-44 full AML stack |
| Integrations | Manual bill | C-45 POS HMAC |

---

## 8. Control verification matrix

| Control ID | Verification method | Owner |
|------------|---------------------|-------|
| C-08, C-09, C-11 | Automated concurrency integration test | Engineering |
| C-02, C-05 | Auth integration + unit tests | Engineering |
| C-17, C-18 | Webhook replay test | Engineering |
| C-21, C-22 | Staff E2E refund denied without PIN | QA |
| C-27, C-28 | Guest UX review + security review | Product + Eng |
| C-31 | Staging load test + alert routing | Ops |
| C-23 | Audit export spot check | Ops |
| C-36 | CI grep + route guard test | Engineering |
| Waiter SOP (T-03) | Pilot training sign-off | Restaurant + Ops |

---

## 9. Residual risk register (post-control)

| Threat | Residual risk after MVP controls | Acceptance |
|--------|----------------------------------|------------|
| T-03 Bill hijacking | PIN/URL can still leak; outsider may join | Pilot SOP + override; monitor C-31 |
| T-18 Friendly fraud | Restaurant bears chargeback | Evidence pack C-33; insurance out of scope |
| T-04 Malicious claiming | Social dispute, not technical theft | Waiter freeze C-16 |
| T-24 Staff ATO without 2FA | Password compromise | Rate limit C-25; 2FA C-40 V1.1 |
| T-03 + no geo | Remote join possible with secret | Accept for MVP; revisit if metrics bad |

---

*Slice ownership: Part 11 — Security / Fraud / Abuse.*
