# PART 11 — Threat Register (Security / Fraud / Abuse)

**Product (working name):** Rekentafel  
**Slice:** Part 11 — Security / Fraud / Abuse  
**Cross-references:** [auth-and-sessions.md](../architecture/api/auth-and-sessions.md), [concurrency.md](../domain/split-engine/concurrency.md), [payment-architecture.md](../architecture/payments/payment-architecture.md), [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md), [scope-boundary.md](../product/scope-boundary.md)

**Purpose:** Exhaustive threat catalog for a Netherlands-first table QR split-pay pilot. Each threat includes attack description, impact rating, mitigations (summary), and MVP vs later scope.

**Impact scale:**

| Rating | Definition | Example outcome |
|--------|------------|-----------------|
| **Critical** | Direct financial loss, regulatory breach, or venue churn | Double-spend bill, EMI violation, GDPR fine |
| **High** | Material guest/merchant harm; manual ops recovery | Wrong guest charged; table hijacked for €200 |
| **Medium** | Recoverable with staff intervention; reputational | Slow claim conflicts; noisy fraud alerts |
| **Low** | Nuisance or bounded loss | Menu spam; fake service signal |

---

## 1. Threat summary matrix

| ID | Threat | Category | Impact | MVP exposure | Primary control family |
|----|--------|----------|--------|--------------|------------------------|
| T-01 | Outsider QR scanning (empty table) | Physical / recon | Low | Menu only | Public surface minimization |
| T-02 | Outsider QR scanning (payment mode) | Session gate | Medium | No bill without token | `PaymentSessionToken` gate |
| T-03 | Bill hijacking via leaked join secret | Session abuse | **High** | PIN/URL shared beyond table | Token TTL + staff training + rotation |
| T-04 | Malicious item claiming | Allocation fraud | **High** | Claim expensive lines | Claim locks + waiter override |
| T-05 | Concurrent claim race (double allocation) | Concurrency | **Critical** | Two guests, one unit | Redis `claim:lock` + DB constraints |
| T-06 | Bill hijacking via stale session | Session lifecycle | High | Rejoin after close | Token revocation on close |
| T-07 | Replay of mutating API requests | Protocol | High | Double checkout | Idempotency keys + webhook dedup |
| T-08 | Replay of join / payment tokens | Credential | High | Reuse revoked token | Token state machine + hash storage |
| T-09 | QR tampering (sticker swap) | Physical | **High** | Pay wrong venue/table | Signed QR payload + venue verify UX |
| T-10 | QR tampering (URL injection) | Client | Medium | Phishing clone site | HSTS, domain pinning UX, CSP |
| T-11 | Spoofed payment session (fake UI) | Phishing | High | Credential harvest | Official domain + no card fields on platform |
| T-12 | Spoofed participant JWT | Auth | High | Act as another guest | Short TTL JWT bound to `ps_id` |
| T-13 | Spoofed Mollie webhook | Payment | **Critical** | Fake `paid` events | Fetch-verify from Mollie API |
| T-14 | Rewards farming (visit / loyalty) | Abuse | Medium | **Not MVP** | N/A MVP; rate limits when enabled |
| T-15 | Overpay-to-wallet farming | Regulatory / fraud | **Critical** | **Not MVP** | Feature excluded; no stored value |
| T-16 | Refund abuse (guest-initiated) | Payment ops | High | Dispute after split | Manager-only refunds + audit |
| T-17 | Refund abuse (staff collusion) | Insider | **Critical** | Cash-out via refunds | Dual control + reconciliation |
| T-18 | Chargeback abuse (friendly fraud) | Payment ops | High | Pay share, charge back | Mollie dispute flow + evidence pack |
| T-19 | Chargeback abuse (serial) | Payment ops | High | Repeat across venues | Cross-venue device block (later) |
| T-20 | Staff misuse (bill inflation) | Insider | **High** | Inflate before split | Manager review + audit |
| T-21 | Staff misuse (token hoarding) | Insider | Medium | Delay payment mode | Role RBAC + session timeouts |
| T-22 | Staff misuse (claim override theft) | Insider | High | Reassign paid allocations | Override audit + PIN |
| T-23 | Account takeover (guest) | Auth | Medium | Merge wrong history | OTP magic link only |
| T-24 | Account takeover (staff) | Auth | **Critical** | Full venue control | Rate limit + 2FA later |
| T-25 | Wallet abuse (stored balance) | Regulatory | **Critical** | **Not MVP** | No wallet in MVP |
| T-26 | Promo abuse (discount codes) | Abuse | Medium | **Not MVP** | Single-use caps when built |
| T-27 | Crypto AML / sanctions evasion | Regulatory | **Critical** | **Not MVP** | Separate rail; Travel Rule |
| T-28 | Service signal spam | Abuse | Low | Fake "call server" | Device rate limits |
| T-29 | Join PIN brute force | Credential | Medium | Guess 6-digit PIN | 5 attempts / 15 min lockout |
| T-30 | Partial pay abandonment | Ops / UX | Medium | Table stuck open | TTL + waiter force close |
| T-31 | VAT / split display manipulation | Compliance | High | Wrong guest VAT view | Server-side tax calc only |
| T-32 | Session fixation (guest device) | Auth | Low | Bind wrong device | New device cookie on join |
| T-33 | Insider export of join tokens | Data leak | High | Logs expose secrets | Hash-only storage + log scrub |
| T-34 | POS import bill tampering (V1.1) | Integration | High | **Later** | Signed import webhooks |

---

## 2. Detailed threat entries

### T-01 — Outsider QR scanning (empty table)

**Attack description:** Attacker scans persistent table QR from outside the venue (photo, Google Maps, social post). Expects live bill or ordering.

**Impact:** **Low** — reconnaissance only; no payment surface.

**Actual MVP behavior:** `GET /t/{slug}/{table_code}` returns menu, table label, service signals only. No bill, no pay CTA.

**Mitigations:**
- Persistent QR resolves to public menu route only ([scope-boundary.md](../product/scope-boundary.md)).
- Rate limit by IP + `guest_device_id` on service signals (10/hour/table).

**Tag:** MVP

**Weak assumption challenged:** "QR on every table is a public entry point." Acceptable for empty state; must not leak session state in API responses (no `payment_session_id` until waiter opens).

---

### T-02 — Outsider QR scanning during payment mode

**Attack description:** Attacker scans same QR while table is in `PAYMENT_ACTIVE` but is not seated at the table.

**Impact:** **Medium** — without join secret, attacker sees join gate only, not line items.

**Mitigations:**
- **Security invariant:** Live bill requires valid `PaymentSessionToken` + `payment_participant_jwt` ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §1).
- QR deep link may include `?ps={payment_session_id}` but **not** raw token; join still requires secret or PIN.
- Optional V1.1: geo fence 100 m or venue WiFi SSID hint ([integration-tiers.md](../integrations/integration-tiers.md)).

**Tag:** MVP (token gate); **Later** (geo/SSID)

---

### T-03 — Bill hijacking via leaked join secret

**Attack description:** Join URL or 6-digit PIN shared on social media, overheard, or photographed from waiter tablet. Outsider joins payment session and claims items.

**Impact:** **High** — wrongful allocation; guest dispute; waiter must override.

**Example (numeric):** Table 7 bill €124.00. Leaked PIN allows stranger to claim €48 steak before legitimate guest pays.

**Mitigations:**
- Waiter operational control: share PIN only when guests seated ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §7).
- `max_joins` default 12; alert when `participants.count > expected_party_size + 2`.
- Token rotation on waiter refresh invalidates old links.
- Manager override + audit (`staff_override=true`) per [concurrency.md](../domain/split-engine/concurrency.md) §12.
- Monitor `409_rate` spike per session ([concurrency.md](../domain/split-engine/concurrency.md) §14).

**Tag:** MVP (operational + rotation + override); **Later** (geo, per-guest links)

**Legal / UX risk:** Not fully solvable cryptographically without proximity hardware. Staff training is a **control**, not a guarantee — document in pilot SOP.

---

### T-04 — Malicious item claiming

**Attack description:** Joined participant claims highest-value items (bottles, shared platters) they did not consume, minimizing their share or blocking others.

**Impact:** **High** — interpersonal dispute; partial table pay deadlock.

**Mitigations:**
- First-claim-wins with visible nicknames on taken units.
- Shared lines: fractional shares capped at 100% sum ([concurrency.md](../domain/split-engine/concurrency.md) §7).
- Waiter `ALLOCATION_FROZEN` + override batch ([concurrency.md](../domain/split-engine/concurrency.md) §6).
- Unclaimed pool remains until close; force-close path for unpaid remainder ([rules-spec.md](../domain/split-engine/rules-spec.md)).

**Tag:** MVP

---

### T-05 — Concurrent claim race (double allocation)

**Attack description:** Two guests tap "Claim" on same €22.00 pasta line within milliseconds. Without serialization, both allocations commit → `sum(allocations) > bill_total`.

**Impact:** **Critical** — merchant financial discrepancy; reconciliation failure.

**Example:** 50 parallel POST `/claims` on one `AllocatableUnit`; exactly 1 must succeed.

**Mitigations (see [concurrency.md](../domain/split-engine/concurrency.md)):**
- Redis `claim:lock:{bill_id}:{unit_id}` NX EX 30s.
- DB unique constraint on active allocation per unit.
- Optimistic `bill_version` check on mutation.
- Idempotency-Key required on `POST /claims`.
- Integration test gate: 50 concurrent attempts → 1×200, 49×409.

**Tag:** MVP

**Ops risk:** Redis down → degrade to `SELECT FOR UPDATE` on unit row; log `redis_degraded`.

---

### T-06 — Bill hijacking via stale / cross-table session

**Attack description:** Attacker reuses `payment_session_id` from previous night or different table; or staff forgets to revoke after walkout.

**Impact:** **High** — wrong bill exposed to wrong guests.

**Mitigations:**
- Token bound to `(restaurant_id, table_id, bill_id, payment_session_id)` ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §2.4).
- `PaymentSessionToken` state machine: `REVOKED` on table close ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §6.1).
- Cron `session.expire_payment_sessions` every 5 min ([background-jobs.md](../architecture/api/background-jobs.md)).
- Cross-table join returns `404` (not `403`).

**Tag:** MVP

---

### T-07 — Replay of mutating API requests

**Attack description:** Attacker replays captured `POST /checkout` or `POST /claims` to create duplicate payments or allocations.

**Impact:** **High** — duplicate Mollie payments; guest double-charged.

**Mitigations:**
- Client `Idempotency-Key` (UUID) cached 24h ([concurrency.md](../domain/split-engine/concurrency.md) §5).
- DB unique `(endpoint, idempotency_key)`.
- Checkout composite key includes `allocation_snapshot_hash` ([concurrency.md](../domain/split-engine/concurrency.md) §5.3).
- `checkout:lock:{bill_id}:{claimant_id}` NX EX 900s.

**Tag:** MVP

---

### T-08 — Replay of join / payment tokens

**Attack description:** Attacker stores raw `PaymentSessionToken` or participant JWT and reuses after waiter intended revocation.

**Impact:** **High** — re-entry to closed or rotated session.

**Mitigations:**
- Store `token_hash` only (SHA-256 + pepper); raw shown once ([data-classification.md](../architecture/data-model/data-classification.md)).
- JWT `jti` + short TTL (2h participant, 2h payment session).
- Revocation sets `revoked_at`; join validates `revoked_at IS NULL`.
- Token rotation marks prior tokens `REVOKED`.

**Tag:** MVP

---

### T-09 — QR tampering (physical sticker swap)

**Attack description:** Fraudster replaces venue QR sticker with attacker-controlled URL pointing to phishing site or different merchant slug.

**Impact:** **High** — payments to wrong merchant; credential theft.

**Mitigations:**
- QR encodes canonical URL `https://{guest_host}/t/{venue_slug}/{table_code}` only.
- Guest UI shows **venue name + table number** prominently before any action.
- Pilot: tamper-evident stickers; staff weekly QR audit walk.
- **Later:** Signed QR payload `?v=1&sig=HMAC(venue_id, table_id)` verified server-side.

**Tag:** MVP (UX verify + ops); **Later** (signed QR)

---

### T-10 — QR tampering (URL injection / open redirect)

**Attack description:** Attacker crafts malicious link mimicking product domain with typos or subdomain takeover.

**Impact:** **Medium** — phishing; no platform card data (Mollie hosted checkout).

**Mitigations:**
- HSTS preload on guest host.
- CSP strict on guest app; no third-party scripts in checkout path.
- Mollie redirect URLs allowlist per environment.
- No `redirect_uri` query params accepted from guests.

**Tag:** MVP

---

### T-11 — Spoofed payment session (fake UI)

**Attack description:** Clone site asks for card numbers or iDEAL credentials directly instead of redirecting to Mollie.

**Impact:** **High** — PCI scope violation if platform ever touches PAN; guest fraud.

**Mitigations:**
- **MVP invariant:** Platform never collects card data; checkout is Mollie redirect only ([payment-architecture.md](../architecture/payments/payment-architecture.md)).
- Guest education copy: "You will pay on Mollie.nl."
- Report-phishing link in footer.

**Tag:** MVP

---

### T-12 — Spoofed participant JWT

**Attack description:** Attacker forges or steals another guest's `payment_participant_jwt` to modify their claims or checkout.

**Impact:** **High** — unauthorized payment initiation.

**Mitigations:**
- JWT signed RS256; `sub=participant_id`, `ps_id`, `bill_id` bound.
- Prefer HttpOnly cookie transport for participant JWT ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §11).
- Claims/checkout verify JWT `sub` matches allocation owner.
- Invalidate JWT on participant `RELEASED` / session `CLOSED`.

**Tag:** MVP

---

### T-13 — Spoofed Mollie webhook

**Attack description:** Attacker POSTs fake `id=tr_xxx` to `/webhooks/mollie` to mark payments paid without funds.

**Impact:** **Critical** — table marked paid; restaurant revenue gap.

**Mitigations:**
- Never trust webhook body alone; worker **GET /v2/payments/{id}** with restaurant OAuth token ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §4.2).
- `processed_webhooks` idempotency PK ([concurrency.md](../domain/split-engine/concurrency.md) §9.3).
- Unknown `tr_xxx` → reject + alert.
- **Later:** Mollie IP allowlist.

**Tag:** MVP

---

### T-14 — Rewards farming (loyalty / visit history)

**Attack description:** Sybil devices join sessions, pay minimal amounts, or link accounts repeatedly to farm loyalty points when program launches.

**Impact:** **Medium** — program economics broken.

**MVP exposure:** **None** — loyalty accrual requires account link; minimal in MVP ([scope-boundary.md](../product/scope-boundary.md)).

**Mitigations (when enabled V1.1+):**
- Accrual only on **paid** allocations above minimum (e.g. €5).
- One accrual per `payment_session_id` per `user_id`.
- Velocity limits on account creation (3/day/device).
- Manual review queue for >3 visits/day same device.

**Tag:** **Later**

---

### T-15 — Overpay-to-wallet / stored-value farming

**Attack description:** Users overpay intentionally to create spendable platform credit; farm partner redemptions or arbitrage VAT.

**Impact:** **Critical** — **EMI / e-money licensing**; accounting fraud.

**MVP exposure:** **None** — feature explicitly excluded ([scope-boundary.md](../product/scope-boundary.md)).

**Mitigations:**
- No stored-value balance in MVP codebase; feature flag hard off.
- Tips pass through to restaurant policy; no platform credit ledger.
- Legal review before any "bonus %" mechanic.

**Tag:** **Later** (likely never as stored value; reframe as merchant-funded discount)

---

### T-16 — Refund abuse (guest-initiated / social engineering)

**Attack description:** Guest pays share via iDEAL, eats meal, requests chargeback or restaurant refund claiming "didn't authorize."

**Impact:** **High** — restaurant loses food revenue + refund.

**Mitigations:**
- MVP: **no guest self-service refund**; manager initiates via staff console.
- Mollie metadata: `payment_session_id`, `participant_id`, allocation snapshot hash.
- Email receipt opt-in with itemized breakdown.
- Staff SOP: verify identity at table before refund.

**Tag:** MVP (process + metadata); **Later** (automated dispute evidence export)

---

### T-17 — Refund abuse (staff collusion)

**Attack description:** Complicit staff issues refunds to accomplice guest after meal; splits cash offline.

**Impact:** **Critical** — merchant loss; platform trust destroyed.

**Mitigations:**
- Refunds require `manager` role + `X-Manager-PIN` ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §3.4).
- Refund cap per shift without `restaurant_admin` (e.g. €100).
- Daily reconciliation report: refunds vs Mollie settlement ([webhook-reconciliation.md](../architecture/payments/webhook-reconciliation.md)).
- Audit log immutable: `staff_user_id`, `pin_verified`, `amount_cents`.

**Tag:** MVP

---

### T-18 — Chargeback abuse (friendly fraud)

**Attack description:** Guest completes iDEAL payment for €21.60 share, then disputes with bank claiming fraud.

**Impact:** **High** — chargeback debited to restaurant Mollie balance.

**Example:** Table of 4; one guest chargebacks €21.60; restaurant already closed table as fully paid.

**Mitigations:**
- Merchant of record = restaurant ([payment-architecture.md](../architecture/payments/payment-architecture.md)).
- Platform stores join timestamp, IP, device hash, allocation lines for dispute pack.
- Partial table pay leaves audit trail per guest payment.
- Ops playbook: submit Mollie dispute evidence within SLA.

**Tag:** MVP (evidence capture); **Later** (chargeback scoring)

---

### T-19 — Chargeback abuse (serial across venues)

**Attack description:** Same device or payment method chargebacks repeatedly at coalition scale.

**Impact:** **High** — platform-wide risk when multi-venue.

**Mitigations:**
- MVP single pilot: manual ops review of disputes.
- **Later:** Device hash blocklist; Mollie consumer block; cross-venue velocity.

**Tag:** **Later** (multi-venue)

---

### T-20 — Staff misuse (bill inflation)

**Attack description:** Waiter adds phantom items or inflates quantities before activating payment mode; splits with accomplice guest.

**Impact:** **High** — guest overpay; VAT misreporting.

**Mitigations:**
- Bill edit audit: every line change logged with `staff_user_id`.
- Manager can view bill edit history before close.
- **Later:** POS import reduces manual entry.

**Tag:** MVP (audit); **Later** (POS)

---

### T-21 — Staff misuse (withholding payment mode)

**Attack description:** Staff delays activating payment session to force single-card payment offline.

**Impact:** **Medium** — product bypass; not fraud per se.

**Mitigations:**
- Metrics: time from `bill_finalized` to `payment_session.opened`.
- Admin dashboard alert if >15 min median.

**Tag:** MVP (metrics); **Later** (incentives)

---

### T-22 — Staff misuse (claim override theft)

**Attack description:** Manager reassigns paid guest's allocations to another participant or voids claims without PIN.

**Impact:** **High** — payment/allocation mismatch.

**Mitigations:**
- Override requires `manager` + PIN + `bill:admin:lock` ([concurrency.md](../domain/split-engine/concurrency.md) §12).
- Cannot reassign **PAID** allocations without refund workflow.
- SSE notify all participants on override.

**Tag:** MVP

---

### T-23 — Account takeover (guest)

**Attack description:** Attacker intercepts magic link / OTP to link victim email; merges visit history.

**Impact:** **Medium** — privacy; mistaken loyalty (when enabled).

**Mitigations:**
- OTP 6 digits, 10 min TTL, single use.
- Link only from active `payment_participant_jwt` session.
- No password in MVP reduces credential stuffing.

**Tag:** MVP

---

### T-24 — Account takeover (staff)

**Attack description:** Credential stuffing on `POST /staff/auth/login`; attacker obtains waiter/manager JWT.

**Impact:** **Critical** — open payment sessions, refunds, bill edits.

**Mitigations:**
- Login rate limit: 10 failures / IP / hour; account lock 30 min.
- Staff JWT 8h TTL; refresh token rotation.
- **Later:** Mandatory 2FA for `manager` and `restaurant_admin`.

**Tag:** MVP (rate limit); **Later** (2FA)

---

### T-25 — Wallet abuse (stored balance / float)

**Attack description:** Attacker exploits wallet top-up, transfer, or negative balance bug to extract EUR.

**Impact:** **Critical** — platform fund loss; EMI.

**MVP exposure:** **None** — no wallet ([payment-architecture.md](../architecture/payments/payment-architecture.md)).

**Mitigations:**
- No `wallet_balance` column in MVP schema.
- Code search CI gate: block merge if wallet routes added without legal sign-off.

**Tag:** **Later** / excluded

---

### T-26 — Promo abuse (discount / referral codes)

**Attack description:** Brute-force promo codes; multi-account referral farming.

**Impact:** **Medium** — margin loss.

**MVP exposure:** **None** — no promo engine in pilot.

**Mitigations (when built):**
- High-entropy codes; per-user redemption cap.
- Device velocity limits; manual approval for >€50 discount.

**Tag:** **Later**

---

### T-27 — Crypto AML / sanctions evasion

**Attack description:** Guest uses crypto rail to pay anonymously; structured amounts; sanctioned wallet interaction.

**Impact:** **Critical** — MiCA / Wwft violations; platform licensing.

**MVP exposure:** **None** — crypto excluded ([crypto-rail-design.md](../architecture/payments/crypto-rail-design.md)).

**Mitigations (post-MVP rail):**
- Licensed crypto PSP owns KYC/AML; platform integration only.
- Separate `crypto_payment_intents` table; never mix with Mollie ledger.
- Travel Rule for transfers >€1000 equivalent.
- Sanctions screening on deposit addresses.
- No platform custody of private keys.

**Tag:** **Later** (separate regulated rail)

---

### T-28 — Service signal spam

**Attack description:** Bot floods `POST /tables/{id}/service-signals` from scanned QR.

**Impact:** **Low** — waiter alert fatigue.

**Mitigations:**
- Rate limit: 3 signals / 10 min / device / table.
- Dedup identical signal type within 2 min.

**Tag:** MVP

---

### T-29 — Join PIN brute force

**Attack description:** Attacker enumerates 6-digit PIN for active payment session.

**Impact:** **Medium** — session join without waiter intent.

**Mitigations:**
- 5 failed attempts / 15 min / `payment_session_id`; lockout 30 min ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §7).
- Redis counter `join:pin_attempts:{payment_session_id}` ([idempotency-concurrency.md](../architecture/api/idempotency-concurrency.md)).
- Alert on lockout event.

**Tag:** MVP

---

### T-30 — Partial pay abandonment

**Attack description:** Two of six guests pay; remainder leave; table stuck in `PARTIALLY_PAID`.

**Impact:** **Medium** — ops burden; not strictly fraud.

**Mitigations:**
- Waiter force close with manager PIN; unpaid → restaurant loss or manual chase.
- Payment session TTL max 6h cumulative; expiry blocks new joins.
- `orphan_payment` flag if webhook after close ([concurrency.md](../domain/split-engine/concurrency.md) §9.4).

**Tag:** MVP

---

### T-31 — VAT / split display manipulation

**Attack description:** Client-side tampering shows lower VAT-inclusive total; guest pays wrong amount believing UI.

**Impact:** **High** — Dutch VAT compliance exposure for merchant.

**Mitigations:**
- All totals computed server-side; client display-only.
- Checkout amount from immutable `CheckoutIntent` snapshot.
- Mollie `amount` matches server intent; mismatch rejects create.

**Tag:** MVP

---

### T-32 — Session fixation (guest device)

**Attack description:** Attacker sets victim's `rt_device` cookie to attacker-controlled device ID.

**Impact:** **Low** — rate limit bypass; wrong nickname association.

**Mitigations:**
- Cookie `Secure`, `HttpOnly`, `SameSite=Lax`.
- New participant always binds fresh `participant_id` on join.

**Tag:** MVP

---

### T-33 — Insider export of join tokens via logs

**Attack description:** Developer logging accidentally captures raw `PaymentSessionToken` or PIN in application logs.

**Impact:** **High** — mass bill exposure if logs leaked.

**Mitigations:**
- Log `token_hash` prefix only ([auth-and-sessions.md](../architecture/api/auth-and-sessions.md) §11).
- CI lint: block log patterns matching token format.
- L3 classification on `payment_session_tokens` ([data-classification.md](../architecture/data-model/data-classification.md)).

**Tag:** MVP

---

### T-34 — POS import bill tampering (V1.1+)

**Attack description:** Attacker spoofs POS webhook to inject inflated bill before payment mode.

**Impact:** **High** — fraudulent bill total.

**MVP exposure:** **None** — manual bill entry only.

**Mitigations (when built):**
- HMAC-signed webhooks per venue integration key.
- Bill import requires waiter confirm before `payment_session.open`.

**Tag:** **Later**

---

## 3. Attack surface state machine (guest path)

```
                    ┌─────────────────┐
                    │ Scan table QR   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     ┌────────────────┐           ┌────────────────┐
     │ EMPTY / SEATED │           │ PAYMENT_ACTIVE │
     │ Menu + signals │           │ Join gate only │
     │ T-01, T-28     │           │ T-02, T-29     │
     └────────────────┘           └───────┬────────┘
                                            │ valid PaymentSessionToken
                                            ▼
                                   ┌────────────────┐
                                   │ JOINED         │
                                   │ Claims + pay   │
                                   │ T-03–T-05, T-07│
                                   └────────────────┘
```

---

## 4. Numeric scenario — bill hijacking + race (combined)

**Setup:** Restaurant De Rekentafel, Table 12, bill €86.40, 4 guests, payment session open 20:45 CET.

| Time | Event | Threat | Outcome if unmitigated | Control |
|------|-------|--------|------------------------|---------|
| 20:46 | Stranger obtains PIN `482917` from Instagram story | T-03 | Claims €32 wine | Nickname visible; waiter freeze + override |
| 20:47 | Anna + Boris both claim €22 pasta (same unit) | T-05 | Double €44 allocated | Redis lock → 1×200, 1×409 |
| 20:48 | Boris retries with new Idempotency-Key | T-07 | Second allocation | 409 UNIT_UNAVAILABLE |
| 20:50 | Anna double-taps Pay | T-07 | Two Mollie payments | Checkout idempotency + lock |
| 20:52 | Fake webhook `paid` | T-13 | Table over-credited | Mollie GET verify |

---

## 5. Regulatory and legal flags (this slice)

| Area | Risk | MVP stance |
|------|------|------------|
| PSD2 / EMI | Platform holds guest funds or stored value | **No** — Mollie merchant-of-record restaurant |
| GDPR | Payment session PII, retention | Minimize; 90-day nickname anonymization |
| Wwft / AML | Crypto, high-value anonymous pay | Crypto **out of MVP** |
| Dutch VAT | Incorrect split receipts | Server-side calculation only |
| Consumer law | Misleading overpay rewards | Overpay-wallet **not shipped** |

---

## 6. Open assumptions to monitor in pilot

1. **Waiter-only join secret is sufficient** for pilot venue culture — if hijack rate >2% sessions, enable geo or per-guest links (V1.1).
2. **12 max participants** adequate for large parties — monitor override frequency.
3. **No guest refunds** acceptable to pilot restaurant — confirm contractually.
4. **Friendly fraud rate** on iDEAL lower than cards — still capture evidence from day one.

---

*Slice ownership: Part 11 — Security / Fraud / Abuse. Files: `docs/security/threat-register.md`, `control-matrix.md`, `mvp-security-checklist.md`.*
