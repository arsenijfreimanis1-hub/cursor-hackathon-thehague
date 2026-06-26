# MVP Security Launch Checklist — Pilot Gate

**Product (working name):** Rekentafel  
**Slice:** Part 11 — Security / Fraud / Abuse  
**Purpose:** Go/no-go gate before Netherlands single-venue pilot. Every item must pass or have documented exception with owner sign-off.

**References:** [threat-register.md](./threat-register.md), [control-matrix.md](./control-matrix.md), [concurrency.md](../domain/split-engine/concurrency.md), [auth-and-sessions.md](../architecture/api/auth-and-sessions.md)

---

## How to use this checklist

| Status | Meaning |
|--------|---------|
| ☐ | Not started |
| ◐ | In progress |
| ☑ | Verified |
| ⚠ | Exception (document in §6) |

**Gate rule:** All **P0** items ☑. **P1** items ☑ or ⚠ with ops mitigation. **P2** may defer post-pilot.

---

## 1. P0 — Block launch if failing

### 1.1 PaymentSessionToken and session gate

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-01 | Scanning table QR **without** join secret does **not** return bill line items | C-01, C-02 | Manual: empty + payment-active table |
| P0-02 | `PaymentSessionToken` stored as hash only; raw never in DB/logs | C-03, C-30 | DB inspect + log sample |
| P0-03 | Join rejects expired, revoked, or wrong-table tokens | C-04, C-05 | API test matrix |
| P0-04 | Join PIN lockout after 5 failures / 15 min | C-07 | Automated test |
| P0-05 | `payment_participant_jwt` required on claims/checkout | C-06 | API 401 without token |
| P0-06 | Token rotation invalidates prior join URLs | C-05 | Refresh + retry old URL → 401 |
| P0-07 | Table close revokes all active payment session tokens | C-05, C-29 | E2E close flow |

### 1.2 Claim locks and bill hijacking / race mitigation

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-08 | Redis `claim:lock:{bill_id}:{unit_id}` NX EX 30 on every claim | C-08 | Code review + integration test |
| P0-09 | **50 concurrent claims on 1 unit** → exactly 1 success, 49 × 409 | C-08, C-09 | [concurrency.md](../domain/split-engine/concurrency.md) §13 k6/Jest |
| P0-10 | DB prevents duplicate active allocation per unit | C-09 | Constraint test |
| P0-11 | `Idempotency-Key` required on POST claims/checkout | C-11 | OpenAPI + 400 test |
| P0-12 | Duplicate idempotency key returns same response, single side effect | C-11 | Replay test |
| P0-13 | `checkout:lock:{bill_id}:{claimant_id}` prevents double Mollie payment | C-12 | Double-tap test |
| P0-14 | Waiter override uses `bill:admin:lock` + audit entry | C-15, C-23 | Staff E2E |
| P0-15 | `ALLOCATION_FROZEN` blocks guest claims with 423 | C-16 | API test |
| P0-16 | Bill hijack playbooks documented: freeze → verify nicknames → override | T-03 | Ops runbook exists |

Reference: [concurrency.md](../domain/split-engine/concurrency.md) §4 (claim lock), §12 (override), §13 (tests).

### 1.3 Payments (Mollie)

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-17 | Checkout redirects to Mollie hosted page only; no PAN fields on platform | C-28 | UX + code scan |
| P0-18 | Webhook handler fetches payment from Mollie API before marking paid | C-17 | Replay fake POST → no credit |
| P0-19 | `processed_webhooks` prevents double increment of `confirmed_paid_cents` | C-18 | Duplicate webhook test |
| P0-20 | Mollie `amount` matches server `CheckoutIntent` exactly | C-19 | Unit test |
| P0-21 | VAT/grand totals computed server-side only | C-19, T-31 | Tamper client JSON → ignored |
| P0-22 | Refunds require manager role + PIN; no guest refund UI | C-21, C-22 | Staff E2E denial |

### 1.4 Auth, staff, and tenancy

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-23 | Staff JWT tenant isolation; cross-restaurant ID → 404 | C-20 | API test |
| P0-24 | Staff login rate limit active | C-25 | 11th fail blocked |
| P0-25 | Manager PIN required for force close and refund | C-21 | E2E |
| P0-26 | Immutable audit log for token issue, override, refund | C-23 | Export sample |

### 1.5 Excluded features (regulatory)

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-27 | Crypto payment routes disabled (`501 NOT_MVP`) | C-36 | Route probe |
| P0-28 | No stored-value wallet / overpay credit ledger in schema | C-36, T-15 | Schema review |
| P0-29 | No guest account password storage (OTP/magic link only) | C-35 | Schema review |
| P0-30 | Platform does not hold guest funds; Mollie settles to restaurant | Payment arch | Legal sign-off doc |

### 1.6 Infrastructure and transport

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P0-31 | HSTS enabled on guest + staff hosts | C-26 | SSL Labs / curl |
| P0-32 | CSP deployed on guest pay path | C-26 | Header inspect |
| P0-33 | `rt_device` cookie: HttpOnly, Secure, SameSite=Lax | C-06 | Browser devtools |
| P0-34 | Secrets (Mollie OAuth, JWT keys, pepper) in KMS/env — not in repo | C-30 | Secret scan CI |
| P0-35 | Cron `session.expire_payment_sessions` running */5 min | C-29 | Job monitor |

---

## 2. P1 — Required for pilot ops (exception allowed with mitigation)

| # | Check | Control | Verify |
|---|-------|---------|--------|
| P1-01 | Venue name + table number visible before join/pay | C-27 | UX review |
| P1-02 | Service signal rate limit 3/10min/device/table | C-34 | Load test |
| P1-03 | Guest join rate limit by IP + device | C-24 | Config review |
| P1-04 | Alert on join PIN lockout events | C-07, C-31 | Pager route test |
| P1-05 | Alert on `409_rate > 15%` per payment session | C-31 | Synthetic spike test |
| P1-06 | Alert on `orphan_payment_count > 0` | C-32 | Simulated late webhook |
| P1-07 | Daily reconciliation job: Mollie vs platform ledger | C-32 | First run report |
| P1-08 | Dispute evidence export includes join time, allocations, device hash | C-33 | Sample export |
| P1-09 | Bill edit audit visible to manager before close | C-23, T-20 | Staff UI |
| P1-10 | Waiter training completed: when to open payment, PIN handling, hijack SOP | T-03 | Signed checklist |
| P1-11 | QR sticker tamper-evident install + weekly audit scheduled | T-09 | Venue ops doc |
| P1-12 | Redis unavailable fallback documented and tested (`FOR UPDATE`) | C-08 | Chaos test |
| P1-13 | `max_joins` default 12 enforced; banner when >8 participants | C-31 | API test |
| P1-14 | GDPR retention job scheduled (nickname anonymization 90d) | Auth doc §8 | Job config |
| P1-15 | Incident response contact + 4-hour ack SLA defined | Ops | Runbook |

---

## 3. P2 — Post-pilot hardening (track, not blocking)

| # | Item | Control | Target |
|---|------|---------|--------|
| P2-01 | Staff 2FA for manager/admin | C-40 | V1.1 |
| P2-02 | Geo or SSID join gate | C-37 | V1.1 if hijack >2% sessions |
| P2-03 | Signed QR payloads | C-38 | V1.1 |
| P2-04 | Per-guest single-use join links | C-39 | V1.1 |
| P2-05 | Mollie webhook IP allowlist | C-46 | V1.1 |
| P2-06 | Cross-venue device blocklist | C-41 | Multi-venue |
| P2-07 | Loyalty velocity controls | C-42 | Loyalty launch |
| P2-08 | Crypto AML stack | C-44 | Separate rail eval |
| P2-09 | Penetration test (external) | — | Before venue #2 |
| P2-10 | SOC2 / ISO roadmap | — | Series A prep |

---

## 4. Automated test bundle (CI gate)

Run before pilot deploy tag:

```bash
# Illustrative — wire to repo test commands
npm run test:security:concurrency   # P0-08–P0-12 (50-claim race)
npm run test:security:auth          # P0-01–P0-07, P0-23–P0-25
npm run test:security:webhooks      # P0-18–P0-19
npm run test:security:idempotency   # P0-11–P0-13
npm run test:security:exclusions    # P0-27–P0-28
```

**Minimum pass criteria:**

| Suite | Tests | Threshold |
|-------|-------|-----------|
| Concurrency | 50-parallel claim | 1×200, 49×409 |
| Concurrency | SHARED 60%+50% race | Second tx 422 |
| Webhook | Double delivery | Single `confirmed_paid_cents` increment |
| Auth | Revoked token join | 401 |
| Exclusions | `POST /crypto/checkout` | 501 |

---

## 5. Pilot day smoke test (15 minutes)

Execute on staging, then production pilot venue:

| Step | Action | Expected |
|------|--------|----------|
| 1 | Scan QR at empty table | Menu only; no bill |
| 2 | Waiter start dining + enter bill €43.20 | Bill in staff UI |
| 3 | Waiter open payment; note PIN | Token ISSUED |
| 4 | Guest A join with PIN | Participant list shows A |
| 5 | Guest B join same session | Two participants |
| 6 | A + B simultaneous claim same €14 line | One wins, one 409 |
| 7 | A checkout iDEAL test mode | Mollie redirect |
| 8 | Webhook marks partial paid | Remaining balance correct |
| 9 | Manager force close remainder with PIN | Session CLOSED |
| 10 | Retry join with old PIN | 401 revoked |

---

## 6. Exception log

| Date | Item ID | Reason | Mitigation | Approver |
|------|---------|--------|------------|----------|
| | | | | |

---

## 7. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Engineering lead | | | ☐ |
| Security / platform | | | ☐ |
| Product | | | ☐ |
| Pilot restaurant manager | | | ☐ |
| Legal (PSD2 / GDPR) | | | ☐ |

**Launch decision:** ☐ GO  ☐ NO-GO

---

## 8. Quick reference — critical patterns

### PaymentSessionToken

- Issued only by waiter `payment_session:open`
- 32-byte secret + 6-digit PIN; hash-at-rest
- 2h TTL; REVOKED on close/rotate
- Join requires `TableSessionState=PAYMENT_ACTIVE`

### Claim lock

- Redis: `claim:lock:{bill_id}:{unit_id}` value `{participant_id}:{payment_session_id}` TTL 30s
- DB: unique active allocation per unit
- Idempotency-Key on all claim mutations
- Override: staff `bill:admin:lock:{bill_id}` + manager PIN

See [concurrency.md](../domain/split-engine/concurrency.md) §4 and [control-matrix.md](./control-matrix.md) §3–§4.

---

*Slice ownership: Part 11 — Security / Fraud / Abuse.*
