# PART 8 — Restaurant Integration Model: Integration Tiers

**Product (working name):** Rekentafel / TabSettle  
**Slice:** Part 8 — Restaurant Integration Tiers and Manual Ops Playbook  
**Market:** Netherlands-first hospitality fintech  
**Cross-references:** [manual-ops-playbook.md](./manual-ops-playbook.md), [pos-adapter-interface.md](./pos-adapter-interface.md), [qr-lifecycle.md](./qr-lifecycle.md), [mvp-roadmap.md](../product/mvp-roadmap.md), [auth-and-sessions.md](../architecture/api/auth-and-sessions.md)

---

## 1. Executive summary

Rekentafel integrates with restaurant operations in **three tiers**, each with a verifiable exit artifact. The platform **never** becomes a phone-ordering channel. Waiters remain the order-taking authority at every tier.

| Tier | Bill source | Menu source | POS coupling | Target venues |
|------|-------------|-------------|--------------|---------------|
| **MVP (Tier 0)** | Waiter manual entry + one-off CSV import | Admin CRUD (static) | None | 1 pilot |
| **V1.1 (Tier 1)** | Scheduled CSV/API import + manual override | Admin CRUD + bulk CSV | Read-only export adapters | 3–10 |
| **V2 (Tier 2)** | POS adapter read-only bill sync | POS menu sync (optional) + admin override | Read-only check sync; **no order APIs** | 25+ |

**Security invariant (all tiers):** Persistent table QR never exposes a live bill. Bill visibility requires a **waiter-activated payment session** plus a **short-lived join token** (see §5).

**Explicit rejection:** Full QR phone ordering, guest-initiated kitchen tickets, and bi-directional POS order sync are **out of scope** for MVP, V1.1, and V2 adapter contracts respectively.

---

## 2. Integration tier comparison

### 2.1 Capability matrix

| Capability | MVP (Tier 0) | V1.1 (Tier 1) | V2 (Tier 2) |
|------------|--------------|---------------|-------------|
| Bill creation | Staff console line-by-line | + CSV/API import per session | + POS check pull (read-only) |
| Bill updates during service | Manual add/remove lines | Manual + re-import merge rules | POS delta sync with lock rules |
| Bill validation | VAT sum check before payment open | + import schema validation | + POS total reconciliation |
| Menu for empty-table QR | Admin CRUD | + CSV bulk import | + POS catalog sync (optional) |
| Table session start | Waiter tap | Same | Same (+ optional POS hint) |
| Payment mode activation | Waiter tap + token | Same | Same (+ optional POS check ID link) |
| Order placement via platform | **Never** | **Never** | **Never** |
| POS write (fire order, void) | **Never** | **Never** | **Never** |
| Offline fallback | Paper + manual terminal | Same | Same |
| Training time (new waiter) | ~45 min | ~30 min | ~20 min (if POS sync stable) |
| Ops burden (per venue/week) | ~2 h manager | ~45 min | ~15 min automated alerts |

### 2.2 When to advance tiers

| From → To | Gate (all must pass) |
|-----------|----------------------|
| MVP → V1.1 | ≥70% pilot tables with bill >€30 use payment mode; ≤8% claim disputes; waiter survey ≥4/5 on “easy to activate payment” |
| V1.1 → V2 | ≥3 venues on Tier 1; import error rate <2%; legal sign-off on POS vendor contract; adapter passes conformance suite |

**Challenge to master prompt assumption:** “POS sync deferred” is correct for MVP, but **manual entry error rate** (wrong qty, wrong VAT rate) will dominate pilot support tickets. V1.1 CSV import is not optional polish — it is the first reliability upgrade.

---

## 3. Tier 0 — MVP manual entry and import

### 3.1 Bill entry paths

| Path | Actor | When | Output |
|------|-------|------|--------|
| **Manual line entry** | Waiter/manager | During or after service | `bill_lines[]` with qty, unit price, VAT rate |
| **Quick-add templates** | Waiter | Repeat items (coffee, bitterballen) | Pre-filled line from venue favorites (MVP: 10 slots) |
| **One-off CSV import** | Manager | Before opening payment | Parsed lines → draft bill |
| **Service charge toggle** | Manager config; waiter applies | Bill finalization | % applied to food subtotal per venue rule |

### 3.2 Manual bill entry UX contract

Staff console **Bill editor** fields per line:

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `description` | string(120) | Yes | `Huiswijn rood` |
| `quantity` | decimal(6,2) | Yes | `1` or `0.5` (shared bottle) |
| `unit_price_cents` | integer | Yes | `3200` (= €32.00) |
| `vat_rate_bps` | integer | Yes | `900` (9%) or `2100` (21%) |
| `is_shared_default` | boolean | No | `true` for platters |
| `pos_sku` | string | No | Empty in MVP |

**Validation before payment open:**

```
Σ(line_total_cents) + service_charge_cents == bill.total_cents
Σ(vat_by_rate) == bill.vat_total_cents  (±1 cent rounding tolerance)
bill.total_cents > 0
line_count >= 1
```

### 3.3 MVP CSV import format

One-off import per dining session. File uploaded in staff console or admin.

**Filename convention:** `bill_{venue_slug}_{table_code}_{YYYYMMDD}.csv`

**Required columns:**

| Column | Format | Example |
|--------|--------|---------|
| `description` | UTF-8 string | `Burger speciaal` |
| `quantity` | decimal | `2` |
| `unit_price` | decimal EUR | `14.50` |
| `vat_rate` | `9` or `21` | `9` |

**Optional columns:** `sku`, `category`, `is_shared`

**Example file (Table 12, 4 covers):**

```csv
description,quantity,unit_price,vat_rate
Burger speciaal,2,14.50,9
Entrecote,1,28.00,9
Huiswijn rood,1,32.00,21
Cola,2,3.50,9
```

**Import result:** €105.60 food subtotal → +10% service charge (venue setting) → bill ready for payment open.

**Import failure modes:**

| Error | Staff message | Recovery |
|-------|---------------|----------|
| Missing column | “CSV missing column: vat_rate” | Fix file, re-upload |
| Invalid VAT | “Line 3: VAT must be 9 or 21” | Edit line in UI after partial import |
| Duplicate upload | “Bill already has lines — merge or replace?” | Manager chooses merge/replace |

### 3.4 MVP menu sync

| Aspect | MVP behavior |
|--------|--------------|
| Source of truth | Restaurant admin CRUD |
| Guest empty-table view | Cached menu JSON; CDN edge cache 5 min |
| Updates | Admin publish → invalidate cache |
| POS menu | **Not synced** — admin maintains parallel catalog |
| Allergens / dietary | Text field per item (no structured allergens MVP) |
| Photos | Optional URL; max 500 KB recommended |
| Languages | Dutch only MVP |

**Rationale:** Empty-table menu is marketing + context, not order cart. Keeping it admin-managed avoids POS menu schema fragmentation in pilot.

### 3.5 MVP integration architecture

```text
┌─────────────┐     manual/CSV      ┌──────────────┐
│ Staff       │ ──────────────────► │ Bill Service │
│ Console     │                     │ (draft→open) │
└─────────────┘                     └──────┬───────┘
                                           │
┌─────────────┐     admin CRUD             │
│ Restaurant  │ ──────────────────► Menu Service (static)
│ Admin       │                            │
└─────────────┘                            ▼
                                    Payment Session
                                    (waiter token gate)
                                           │
                                           ▼
                                    Guest Web (join + pay)
                                           │
                                           ▼
                                    Mollie (merchant account)
```

**Mollie (MVP):** Restaurant-owned Mollie API key; platform is SaaS layer — no fund holding. See [payment-architecture.md](../architecture/payments/payment-architecture.md).

**Crypto:** Not in any integration tier for MVP/V1.1. V2 evaluates separate regulated rail — not via POS adapter or Mollie checkout bundling.

### 3.6 Tier 0 exit artifact

| Artifact | Verification |
|----------|--------------|
| Pilot venue live 14 days | ≥40% eligible tables use payment mode |
| Bill accuracy audit | Manager spot-check 20 sessions: entered total matches printed receipt |
| Zero phone orders | No order API routes in production; guest UI has no “add to order” |

---

## 4. Tier 1 — V1.1 CSV/API import and scaled menu

### 4.1 Bill import upgrades

| Feature | Description |
|---------|-------------|
| **Scheduled re-import** | Webhook or cron pulls export file from POS drop folder / SFTP |
| **Session binding** | Import keyed by `external_check_id` + `table_external_id` |
| **Merge policy** | `REPLACE_DRAFT` (pre-payment) vs `APPEND_DELTA` (post-payment blocked) |
| **Conflict UI** | Side-by-side: imported vs current; manager picks |
| **Audit** | Every import logged with file hash + line diff |

### 4.1.1 Supported V1.1 import sources (NL priority)

| Source | Mechanism | Freshness |
|--------|-----------|-----------|
| UnTill export | CSV via scheduled export | 5–15 min |
| Lightspeed Restaurant | Reporting CSV / REST export (read-only token) | 15 min |
| Generic adapter | [pos-adapter-interface.md](./pos-adapter-interface.md) `pullBill()` | Configurable |

**Not in V1.1:** Real-time kitchen display sync, order firing, inventory writes.

### 4.2 V1.1 menu sync options

| Mode | Description | Use when |
|------|-------------|----------|
| **Admin-only (default)** | Same as MVP | POS menu unreliable or incomplete |
| **CSV bulk import** | Weekly menu CSV from admin | Seasonal menu changes |
| **POS read-only catalog** | Adapter `pullMenu()` → staging → admin publish | Menu parity with POS prices critical |
| **Hybrid** | POS sync + admin overlay for descriptions/photos | Best UX at scale |

**Publish workflow (POS sync mode):**

```text
POS pullMenu() → menu_staging → admin review diff → publish → CDN invalidate
```

Unpublished staging never visible to guests.

### 4.3 V1.1 optional proximity gate

| Control | MVP | V1.1 |
|---------|-----|------|
| Join payment session | Waiter unlock + token/PIN | + optional venue WiFi SSID check or geo fence (100 m) |

Default off; enable only if pilot sees bill hijacking (distant IP joins).

### 4.4 Tier 1 exit artifact

| Artifact | Verification |
|----------|--------------|
| 3 venues on import path | ≥80% bills sourced from import; manual override <20% |
| Import SLA | 95% of imports complete <60 s |
| Dispute rate | <5% sessions need claim override |

---

## 5. Session activation model (all tiers)

Payment mode is **waiter-issued**, not guest-triggered. This section is normative across Tier 0–2.

### 5.1 State machine: table + dining session

```text
                    ┌─────────────┐
         scan QR    │    EMPTY    │  menu + call server only
        ──────────► │ table.status│  no dining_session
                    └──────┬──────┘
                           │ POST dining_session.start (waiter)
                           ▼
                    ┌─────────────┐
                    │   SEATED    │  dining_session.status=DINING
                    │             │  bill may be draft; not guest-visible
                    └──────┬──────┘
                           │ bill finalized + POST payment_session.open
                           ▼
                    ┌─────────────┐
                    │  PAYMENT    │  payment_session.status=OPEN
                    │  _ACTIVE    │  token issued (TTL 2h default)
                    └──────┬──────┘
                           │ remaining=0 OR force close
                           ▼
                    ┌─────────────┐
                    │   CLOSED    │  audit frozen; table → EMPTY
                    └─────────────┘
```

**Guest scan behavior by state:**

| Table state | QR scan result | Bill visible? |
|-------------|----------------|---------------|
| EMPTY | Menu, table label, call server | No |
| SEATED | Same + “Your server will open the bill when ready” | No |
| PAYMENT_ACTIVE | Join gate → lobby (with valid token/PIN) | Yes |
| CLOSED | Menu + “This table is available” | No |

### 5.2 Payment session token issuance

Triggered by waiter **Open payment** after bill validation.

| Field | Value |
|-------|-------|
| `payment_session_id` | UUID v7 |
| `join_secret` | 32-byte base64url; hashed at rest (bcrypt/argon2) |
| `join_pin` | 6 digits; bcrypt; rotates on refresh |
| `ttl_default` | 2 hours |
| `ttl_max_cumulative` | 6 hours (extensions) |
| `max_participants` | 12 (configurable per venue) |
| `binding` | `restaurant_id`, `venue_id`, `table_id`, `dining_session_id`, `bill_id`, `bill_version` |

**Deep link format (QR overlay when payment active):**

```text
https://{guest_host}/t/{venue_slug}/{table_code}?ps={payment_session_id}&t={join_secret}
```

Persistent table QR sticker URL remains **without** `ps` and `t` params. Staff console displays **session QR** (with token) on payment monitor for guests to scan — or guests enter PIN verbally.

**Challenge to weak assumption:** Embedding token in physical sticker QR would expose bill to anyone who photographed the table. **Tokens are ephemeral and shown on staff screen**, not printed on permanent stickers.

### 5.3 Activation sequence (numeric example)

**Table 7, 3 guests, bill €86.40**

| Step | Actor | Action | System state |
|------|-------|--------|--------------|
| 1 | Waiter | Start session, party size 3 | `SEATED`, `dining_session_id=ds_01` |
| 2 | Waiter | Enter 5 bill lines totaling €86.40 | `bill.status=DRAFT`, version 1 |
| 3 | Waiter | Tap **Open payment** → confirm dialog | `payment_session.opened` |
| 4 | System | Issue token TTL 02:00, PIN `482913` | `PAYMENT_ACTIVE` |
| 5 | Guest A | Scan session QR or enter PIN | `participant_id=p_a`, lobby |
| 6 | Guest B,C | Join within TTL | 3 participants |
| 7 | Guests | Claim + pay via Mollie | `PARTIALLY_PAID` → `PAID` per guest |
| 8 | Waiter | Close table when remaining €0 | `CLOSED` |

### 5.4 Token lifecycle events

| Event | Trigger | Effect |
|-------|---------|--------|
| `payment_session.token_issued` | Open payment | New secret + PIN |
| `payment_session.token_rotated` | Waiter refresh | Old links invalid; audit logged |
| `payment_session.token_revoked` | Cancel payment / close table | All joins blocked |
| `payment_session.expired` | TTL elapsed | Join blocked; waiter must refresh |

### 5.5 Cancel and reopen rules

| Scenario | Allowed? | Procedure |
|----------|----------|-----------|
| Cancel payment before any guest pays | Yes | Revert to `SEATED`; bill editable |
| Cancel after partial pay | Manager only | Block new claims; settle remainder via override |
| Reopen closed table | Manager within 24h | Audit incident; new `dining_session` |

---

## 6. Tier 2 — POS adapter read-only sync

### 6.1 Scope boundary

V2 POS integration is **read-only bill and optional menu sync**. Adapter contract: [pos-adapter-interface.md](./pos-adapter-interface.md).

| In scope | Out of scope |
|----------|--------------|
| Pull open check by table/check ID | Push orders to kitchen |
| Pull line items, modifiers, voids | Modify POS check from guest app |
| Map POS table → platform `table_id` | Phone ordering |
| Reconciliation totals | Inventory deduction |
| Link `external_check_id` to `payment_session` | Auto-open payment without waiter (default off) |

### 6.2 V2 sync modes

| Mode | Waiter action | POS action |
|------|---------------|------------|
| **Manual-first (default at V2 launch)** | Enter bill OR pull check button | On-demand `pullBill()` |
| **Auto-pull on payment open** | Open payment | Adapter fetches latest check |
| **Background sync (future)** | Monitor only | Poll every 60s while `SEATED` — **still no guest visibility until payment open** |

### 6.3 Reconciliation example

| Source | Total |
|--------|-------|
| POS check `#8842` | €126.40 |
| Platform bill after pull | €126.40 |
| Guest payments sum | €126.40 |
| Mollie settled (T+1) | €126.40 − Mollie fees |

Mismatch >€0.01 → block table close; manager reconciliation screen.

### 6.4 Tier 2 exit artifact

| Artifact | Verification |
|----------|--------------|
| 2 POS vendors certified | Conformance tests green |
| 25+ venues | ≥60% on POS pull path |
| Order API absent | Security scan: zero POST order routes |

---

## 7. Phone ordering — explicit rejection

| Request | Response |
|---------|----------|
| Guest adds items from menu to cart | **Not built** — menu is browse-only |
| Guest sends order to kitchen | **Not built** — use call-server signal |
| POS adapter accepts `createOrder()` | **Interface forbidden** — see adapter spec |
| “Just add ordering in V3” | Different product (competes with Untill/Lightspeed guest ordering); breaks waiter-control positioning |

**Allowed guest interactions pre-payment:**

- View menu and prices (informational; may drift from POS until V1.1 sync)
- Call server / ready to order signal
- Request bill (informational prompt — does not open payment)

---

## 8. Risk register (integration-specific)

| Risk | Tier | Severity | Mitigation |
|------|------|----------|------------|
| Manual entry transcription errors | 0 | High | CSV import V1.1; double-entry confirm on bills >€200 |
| VAT rate wrong (9% vs 21%) | 0 | High | Line templates; manager review flag on alcohol |
| Bill hijacking via shared PIN photo | 0–1 | Medium | Short TTL; token rotation; V1.1 geo optional |
| POS export delay (15 min stale bill) | 1 | Medium | Show `imported_at`; waiter manual refresh |
| POS vendor API breaking change | 2 | High | Adapter version pinning; conformance CI |
| Waiter skips “Start session” | 0 | Medium | Training; UI nudge when bill entry without session |
| Menu price drift (admin vs POS) | 0–1 | Low | “Prices may vary” disclaimer on empty-table menu |
| PSD2 scope creep via platform settlement | 2 | High | Mollie Connect legal review before platform fees |
| Offline venue internet loss | 0–2 | High | [manual-ops-playbook.md](./manual-ops-playbook.md) §6 |

---

## 9. Registry entries (cross-slice)

| Canonical name | Definition |
|----------------|------------|
| `IntegrationTier` | `MANUAL` \| `IMPORT` \| `POS_READONLY` |
| `BillSource` | `MANUAL` \| `CSV_IMPORT` \| `POS_PULL` |
| `MenuSource` | `ADMIN` \| `CSV` \| `POS_STAGING` |
| `PaymentSessionToken` | Waiter-issued join credential; see [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) |
| `TableSessionState` | `EMPTY` \| `SEATED` \| `PAYMENT_ACTIVE` \| `CLOSED` |
| `external_check_id` | POS check identifier; V1.1+ |

---

*Slice ownership: Part 8 — Restaurant Integration Model. File: `docs/integrations/integration-tiers.md`.*
