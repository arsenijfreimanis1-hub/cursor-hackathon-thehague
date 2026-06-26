# QR Code Lifecycle — Table Identity and Stickers

**Product (working name):** Rekentafel / TabSettle  
**Slice:** Part 8 — Restaurant Integration  
**Cross-references:** [integration-tiers.md](./integration-tiers.md), [manual-ops-playbook.md](./manual-ops-playbook.md), [auth-and-sessions.md](../architecture/api/auth-and-sessions.md)

---

## 1. Design principles

| Principle | Implementation |
|-----------|----------------|
| **Persistent table identity** | One QR per physical table encodes stable `venue_slug` + `table_code` |
| **No live bill on sticker** | Sticker URL has no payment session token |
| **Ephemeral payment access** | Join secret/PIN issued on staff screen at payment time |
| **Physical ops matter** | Stickers are inventory with issuance, damage, and retirement workflow |

---

## 2. QR URL structure

### 2.1 Persistent sticker URL (printed)

```text
https://{guest_host}/t/{venue_slug}/{table_code}
```

**Example:**

```text
https://pay.rekentafel.nl/t/de-gouden-lepel/t12
```

| Component | Rules |
|-----------|-------|
| `guest_host` | Production subdomain; HTTPS only |
| `venue_slug` | Immutable after publish; `[a-z0-9-]` max 64 |
| `table_code` | Venue-unique; e.g. `t12`, `patio-3`, `bar-1` |

**QR encoding:** Model 2, Error correction **M** (15%), min print size **30×30 mm** on sticker.

### 2.2 Session URL (staff screen only — NOT printed on permanent sticker)

```text
https://{guest_host}/t/{venue_slug}/{table_code}?ps={payment_session_id}&t={join_secret}
```

| Param | Lifetime | Printed on sticker? |
|-------|----------|---------------------|
| `ps` | Payment session duration | **No** |
| `t` | 2 h default (rotatable) | **No** |

**Challenge to weak assumption:** Printing payment-capable QR on table tent would let remote users join after a photo leak. Permanent stickers must resolve to **empty-table or join-gate** experience only.

---

## 3. Guest experience by scan context

| Scan target | Table state | Guest sees |
|-------------|-------------|------------|
| Sticker (no params) | EMPTY | Menu, table name, call server |
| Sticker (no params) | SEATED | Menu + “Bill opens when server ready” |
| Sticker (no params) | PAYMENT_ACTIVE | Join gate: enter PIN or “Ask server for QR” |
| Staff session QR | PAYMENT_ACTIVE | Auto-join → payment lobby |
| Sticker | CLOSED | Menu + “Welcome” (table available) |
| Deactivated QR | any | 410 page: “This QR is no longer valid” |

### 3.1 Join gate copy (PAYMENT_ACTIVE, no token)

> **Your bill is ready.** Ask your server for the 6-digit code or scan the code on their screen.

PIN entry field + rate limit (5 failures / 15 min / device).

---

## 4. Sticker issuance workflow

### 4.1 Initial venue provisioning

| Step | Owner | Action |
|------|-------|--------|
| 1 | Platform ops | Create venue + table registry in admin |
| 2 | Manager | Confirm table list matches floor plan |
| 3 | Platform ops | Generate QR PDF batch (`qr_batch_id`) |
| 4 | Manager | Print on waterproof vinyl (recommended) or laminate paper |
| 5 | Staff | Apply to table: visible, scan-tested at 30 cm |
| 6 | Manager | Sign **QR deployment log** (Appendix A) |

**Batch export formats:**

| Format | Use |
|--------|-----|
| PDF A4 grid (6 per page) | Standard stickers |
| PNG 512×512 per table | Digital displays |
| CSV manifest | Ops audit |

### 4.2 Sticker content (physical)

| Element | Required |
|---------|----------|
| QR code | Yes |
| Table number (human readable) | Yes — large font |
| Venue trade name | Yes |
| “Scan for menu & pay” | Yes (NL: “Scan voor menu & betalen”) |
| Platform logo | Optional |
| Payment logos (iDEAL) | Optional post-Mollie approval |

**Do not print:** Prices, open hours only if stable, PIN, session URLs.

### 4.3 Inventory par levels (pilot)

| Item | Par level |
|------|-----------|
| Pre-printed backup stickers | 10% of table count (min 5) |
| Blank table tents | 4 |
| Lamination pouches | 20 |

**Example:** 24 tables → keep 5 backup stickers at host stand.

---

## 5. Table reassignment and renumbering

### 5.1 Scenario matrix

| Scenario | QR action | Admin action |
|----------|-----------|--------------|
| Rename table `t12` → `t14` | **New sticker** with new code OR alias | Update `table_code`; old code 301 redirect 90 days |
| Move QR sticker to different physical table | **Forbidden** without admin | Deactivate old mapping; issue new |
| Merge two tables for large party | Use one “primary” table session | Secondary stays EMPTY |
| Split party across tables | Separate sessions | No QR change |
| Patio seasonal tables | Activate/deactivate table rows | QR stored off-season |

### 5.2 Reassignment procedure

```text
1. Manager → Admin → Tables → Select table
2. If physical sticker moves: Deactivate current QR (reason: REASSIGNED)
3. Create new table row OR update table_code with redirect
4. Print/apply new sticker
5. Scan-test both old (should 410 or redirect) and new (correct menu)
6. Log in qr_lifecycle_events
```

### 5.3 Redirect policy (table_code change)

| Phase | Old URL behavior |
|-------|------------------|
| Days 0–90 | 301 → new `table_code` + banner “Table moved” |
| After 90 days | 410 Gone |

Prevents broken stickers during transition without exposing wrong-table bills (session still bound to `table_id` UUID internally).

---

## 6. Deactivation and retirement

### 6.1 Deactivation triggers

| Reason | Code | Guest impact |
|--------|------|--------------|
| Sticker damaged/unreadable | `DAMAGED` | 410 + support phone |
| Fraud suspicion (QR posted online) | `FRAUD` | 410 immediately |
| Venue closed table permanently | `RETIRED` | 410 |
| Venue churn | `VENUE_OFFBOARD` | Branded sunset page |
| QR batch compromised | `BATCH_REVOKE` | Entire batch invalidated |

### 6.2 Deactivation state machine

```text
        ┌──────────┐
        │  ACTIVE  │  scans resolve normally
        └────┬─────┘
             │ deactivate(reason)
             ▼
        ┌──────────┐
        │ INACTIVE │  410 Gone (or sunset)
        └────┬─────┘
             │ reactivate (manager + ops)
             ▼
        ┌──────────┐
        │  ACTIVE  │  new audit event
        └──────────┘
```

**Rule:** Deactivating QR does **not** auto-close open payment sessions — manager must close table first.

### 6.3 Replacement after damage

| Step | Action | SLA |
|------|--------|-----|
| 1 | Waiter reports damage in staff app | — |
| 2 | Apply backup sticker (pre-printed `t12`) | **≤5 min** |
| 3 | Manager orders reprint if backups low | 48 h |
| 4 | Ops notified if batch defect | 24 h |

---

## 7. Security controls

| Threat | Mitigation |
|--------|------------|
| QR photo shared on social media | Payment still needs PIN/token; rotate on leak |
| Sticker swapped between venues | `venue_slug` in URL; cross-venue scan shows wrong menu — ops alert on anomaly |
| Brute force PIN | 6 digits + rate limit + lockout + waiter rotation |
| Scraping all table URLs | Robots.txt; no table enumeration API |
| Malicious QR overlay sticker | Staff visual check; tamper-evident stickers recommended |

### 7.1 Fraud response playbook

| Signal | Action |
|--------|--------|
| >3 joins from foreign IP in 10 min | Alert shift lead; rotate PIN |
| Same PIN posted publicly | Revoke token; reissue; consider `FRAUD` deactivation |
| Guest joins wrong table dispute | Waiter override; verify party at table |

---

## 8. Data model (reference)

Aligns with [entity-dictionary.md](../architecture/data-model/entity-dictionary.md).

### 8.1 `table_qr_codes`

| Column | Purpose |
|--------|---------|
| `id` | UUID |
| `table_id` | FK → `tables` |
| `public_slug` | `{venue_slug}/{table_code}` |
| `status` | `ACTIVE` \| `INACTIVE` \| `REDIRECT` |
| `batch_id` | Print batch reference |
| `deactivated_at` | Nullable |
| `deactivate_reason` | Enum |
| `redirect_to_table_id` | Nullable |

### 8.2 `qr_lifecycle_events` (audit)

| Event | Payload |
|-------|---------|
| `qr.batch.generated` | `batch_id`, `table_count` |
| `qr.deployed` | `table_id`, `staff_member_id` |
| `qr.damaged.reported` | `table_id`, photo optional |
| `qr.deactivated` | `reason`, `actor_id` |
| `qr.reactivated` | `table_id` |
| `qr.scan.anomaly` | `ip_country`, `table_id` |

---

## 9. Testing checklist (go-live)

| # | Test | Expected |
|---|------|----------|
| 1 | Scan each table sticker | Correct table number in UI |
| 2 | Scan during EMPTY | Menu only; no bill |
| 3 | Scan during PAYMENT_ACTIVE without token | Join gate only |
| 4 | Scan staff session QR | Lobby access |
| 5 | Deactivate test QR | 410 within 60 s CDN |
| 6 | Redirect old table_code | Lands on new table |
| 7 | Damaged QR replacement | Backup works same URL path |

---

## 10. Examples with numbers

**Venue:** De Gouden Lepel, 18 tables + 6 patio (seasonal)

| Metric | Value |
|--------|-------|
| Initial batch | `qb_2026_001`, 24 codes |
| Backup stock | 5 stickers |
| Avg scans per table per evening | 8–15 (menu + payment) |
| PIN rotations per evening (pilot) | 2–4 |
| Sticker replacements month 1 | 3 (wine spill, sun fade, theft) |

**Cost estimate (pilot):**

| Item | Cost |
|------|------|
| Vinyl stickers 24× | ~€45 |
| Backup set | ~€12 |
| Table tents (optional) | ~€30 |
| **Total one-time** | **~€87** |

---

## Appendix A — QR deployment log

| Table code | Batch ID | Applied date | Applied by | Scan OK | Notes |
|------------|----------|--------------|------------|---------|-------|
| t12 | qb_2026_001 | 2026-06-20 | Maria | ☐ | Window seat |

---

## Appendix B — Sticker artwork spec

| Spec | Value |
|------|-------|
| Size | 80×80 mm sticker, 50×50 mm QR quiet zone |
| Contrast | Dark QR on white |
| Material | Vinyl waterproof, matte (reduce glare) |
| Adhesive | Removable for first 24 h, then permanent |

---

*Slice ownership: Part 8 — Restaurant Integration Model. File: `docs/integrations/qr-lifecycle.md`.*
