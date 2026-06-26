# Bill-Splitting Rules Engine — Specification

**Slice:** Part 5 — Bill-Splitting Logic  
**Product (working name):** Rekentafel / TabSettle  
**Market:** Netherlands-first (EUR, cent precision)  
**Upstream contracts:** `TableSessionState`, `PaymentSessionToken` (see [mvp-roadmap.md](../../product/mvp-roadmap.md))

---

## 1. Purpose and scope

This document defines the **rules engine** that governs how an open table bill is allocated across guests, how amounts are computed (including VAT and service charge), how payments settle, and how waiters override edge cases.

| In scope (MVP) | Out of scope (deferred) |
|----------------|-------------------------|
| Item, equal, custom, shared split modes | Percentage-only custom split (V1.1) |
| Per-guest tip on top of allocated share | Tip pool / staff payout export (V1.1) |
| Partial payments + remaining balance | Automated split refund rules (V1.1) |
| Waiter override + force close | Geo/proximity join gate (V1.1) |
| Mollie checkout per guest payment | Crypto rail (V2+) |
| Optimistic claim locking | ML fraud scoring (V1.1) |

**Security invariant:** The persistent table QR never exposes bill line items. Guests only see the bill after `TableSessionState = PAYMENT_ACTIVE` **and** a valid `PaymentSessionToken` is presented (see §2).

---

## 2. Upstream session contracts

### 2.1 TableSessionState (venue table lifecycle)

| State | Bill visible to guest? | Split engine active? |
|-------|------------------------|----------------------|
| `EMPTY` | No — menu + call server only | No |
| `SEATED` | No — ordering off-platform | No — bill may be draft in staff UI |
| `PAYMENT_ACTIVE` | Yes — with valid token | **Yes** |
| `CLOSED` | No — receipt summary only (optional) | No — read-only audit |

Transition into `PAYMENT_ACTIVE` requires:
1. Waiter finalizes bill lines (manual entry or CSV import).
2. Waiter taps **Activate payment**.
3. System issues `PaymentSessionToken` (see §2.2).
4. Bill snapshot version `bill_version = 1` is locked for allocation (further line edits require waiter override bumping version).

### 2.2 PaymentSessionToken

| Field | Type | Rule |
|-------|------|------|
| `token_id` | UUID | Opaque; never encodes table ID alone |
| `table_session_id` | FK | Links to active seated session |
| `bill_id` | FK | Frozen bill snapshot |
| `issued_at` | timestamp | UTC |
| `expires_at` | timestamp | Default **2h** from issue; refreshable by waiter (+2h, max 6h total) |
| `revoked_at` | timestamp \| null | Set on table close or waiter revoke |
| `join_secret` | string | Short code optional for MVP; token in URL fragment |

**MVP rule:** Scanning table QR returns a join page that **prompts for token validation** (embedded in staff-issued link/QR overlay) or staff-entered 4-digit table payment code. Raw table QR alone does not grant bill access.

**Post-MVP (V1.1):** Optional geo-fence or venue WiFi attestation as secondary factor; waiter unlock remains primary.

---

## 3. Canonical registry (split-engine domain)

| Name | Description |
|------|-------------|
| `Bill` | Header: venue, table, currency EUR, totals, `bill_version` |
| `BillLine` | Single menu/charge line: qty, unit price, VAT rate, line kind |
| `AllocatableUnit` | Smallest atomic claim slot derived from `BillLine` (see §4) |
| `Claimant` | Guest identity in payment session (nickname + device session) |
| `Allocation` | Maps `AllocatableUnit` (or fraction) → `Claimant` |
| `SplitMode` | `ITEM` \| `EQUAL` \| `CUSTOM` \| `SHARED` |
| `ClaimIntent` | Draft allocation before checkout lock |
| `CheckoutIntent` | Frozen allocation + tip → Mollie payment amount |
| `PaymentRecord` | Mollie payment ID, status, idempotency key |
| `RemainingBalance` | `bill_grand_total_cents - sum(confirmed_payments)` |
| `UnclaimedPool` | Units/amount not yet allocated to any claimant |

All monetary values are **integer cents** (EUR). Display rounds half-up to 2 decimals.

---

## 4. Bill composition rules

### 4.1 BillLine kinds

| Kind | MVP | Allocation behavior |
|------|-----|---------------------|
| `MENU_ITEM` | Yes | Discrete units per qty |
| `SERVICE_CHARGE` | Yes | Pro-rata by claimed food/drink subtotal |
| `DISCOUNT` | Yes | Negative line; allocated pro-rata like service charge |
| `ROUNDING_ADJ` | Yes | Waiter-entered ±€0.01–€0.05 fix; allocated last |
| `MANUAL_MISC` | Yes | Same as menu item |

### 4.2 VAT (Netherlands MVP)

| Rate | Applies to | Display |
|------|------------|---------|
| 9% | Food, non-alcoholic drinks, service charge (venue default) | Per-line ex-VAT, VAT, inc-VAT |
| 21% | Alcoholic drinks (e.g., wine, beer) | Per-line ex-VAT, VAT, inc-VAT |

**Storage:** Each `BillLine` stores `unit_price_inc_vat_cents`, `vat_rate_bps` (900 or 2100), computed `line_total_inc_vat_cents`.

**Split rule:** VAT is **not** split independently. Each allocation inherits VAT from its underlying line fraction. Guest receipt shows sum of VAT components from their allocations.

**Compliance risk:** If service charge VAT treatment differs by venue accounting policy, admin configures `service_charge_vat_rate_bps` — default 900.

### 4.3 Service charge

| Setting | Behavior |
|---------|----------|
| Off | No line generated |
| Percentage (e.g., 10%) | Auto line `SERVICE_CHARGE` on bill lock: `% × sum(menu lines inc VAT)` |
| Mandatory vs optional | MVP: display only; included in grand total. Waiter removes line via override if waived. |

**Allocation:** Service charge cents allocated **pro-rata** to each claimant based on their share of **menu subtotal (inc VAT, excluding service charge line)**.

Formula for claimant *c*:

```
sc_share_c = round_half_up(service_charge_total × (menu_subtotal_claimed_c / menu_subtotal_all_claimed_c))
```

When unclaimed menu subtotal exists, unclaimed service charge stays in `UnclaimedPool` until those items are claimed or waiter assigns them.

### 4.4 AllocatableUnit derivation

For `BillLine` with integer `qty = n`:

- Create `n` units: `unit_index = 0..n-1`, each worth `line_total_inc_vat_cents / n` (remainder cents assigned to lowest indices — see §4.5).

For `BillLine` with `qty = 1` and `splittable = true` (shared bottle, platter):

- Create **1** unit with `max_shares = 20` (MVP cap), fractional allocation in 1/20 increments (5% granularity).

**MVP constraint:** Partial qty split on discrete items (e.g., "half burger") is **not** supported — only shared-flag lines accept fractions.

### 4.5 Remainder cent distribution

When splitting line total across units or guests, use **largest remainder method**:

1. Compute exact fractional cents.
2. Floor each allocation.
3. Distribute `+1` cent to allocations with largest fractional remainder until sum matches line total.

Document per-allocation `remainder_rank` in audit log for dispute reconstruction.

---

## 5. Split modes

### 5.1 Mode: ITEM (`SplitMode.ITEM`)

**Intent:** Claim whole discrete units ("I had this burger").

| Rule | Detail |
|------|--------|
| Granularity | One `AllocatableUnit` → at most one `Claimant` at a time |
| Partial qty | Not in MVP for discrete items |
| UI | Tap line → claim 1..n units |
| Validation | Cannot claim more units than available in `UnclaimedPool` |

**State transition:** `ClaimIntent` → validate availability → write `Allocation` or reject with `409 UNIT_UNAVAILABLE`.

### 5.2 Mode: SHARED (`SplitMode.SHARED`)

**Intent:** Multiple guests share one line (bottle of wine, shared starter).

| Rule | Detail |
|------|--------|
| Granularity | Fractional shares on splittable lines only |
| Default split | UI suggests even N-way among selected guests |
| Share sum invariant | Sum of shares on a unit = 1.0 (100%) before checkout lock |
| Min share step | 1/20 (5%) MVP |

**Example:** 4 guests share wine → each share 0.25 → each pays 25% of wine line inc VAT + pro-rata service charge.

**Conflict:** Two guests both claim 100% of same unit → second commit loses (see [concurrency.md](./concurrency.md)); UI shows current owners.

### 5.3 Mode: EQUAL (`SplitMode.EQUAL`)

**Intent:** Split **target amount** equally among *k* selected claimants (subset of table or full table).

| Rule | Detail |
|------|--------|
| Target | Default: entire **remaining** `UnclaimedPool` inc VAT + unclaimed service charge |
| Subset | Exactly *k* claimants selected; must be joined and not `PAID` |
| Amount | `equal_share = remaining_cents // k` with remainder +1 cent to first *r* claimants |
| Overlap with ITEM | **Blocked in MVP** if any selected unit already has ITEM/SHARED allocation — waiter must clear first |
| Lock | Equal split creates `Allocation` rows tagged `mode=EQUAL`, `equal_group_id` |

**Waiter assist:** Force equal split on remaining balance across all joined guests (override code `FORCE_EQUAL_REMAINING`).

### 5.4 Mode: CUSTOM (`SplitMode.CUSTOM`)

**Intent:** Guest pays a self-entered **fixed EUR amount** toward remaining balance without itemizing.

| Rule | Detail |
|------|--------|
| Min | €0.01 |
| Max | `RemainingBalance` for that guest's pending checkout (cannot overpay bill in MVP) |
| Allocation | Does not attach to specific lines — creates `CUSTOM_PLEDGE` ledger entry |
| Settlement | At table close, custom pledges count toward `RemainingBalance`; unallocated pledge surplus flows to `UnclaimedPool` reduction pro-rata |

**Validation:**

```
sum(custom_pledges) + sum(item_allocations) <= bill_grand_total_cents
```

**MVP:** No stored credit if guest pays more than pledge — payment amount capped at checkout intent. **Never** issue wallet balance (EMI risk).

**Post-MVP (V1.1):** Percentage-of-remaining custom mode.

---

## 6. Unclaimed leftovers

| Situation | System behavior | Waiter actions |
|-----------|-----------------|----------------|
| Items never claimed | `UnclaimedPool` > 0 at checkout time | Prompt staff: assign, equal-split, or cash mark-off |
| Some guests paid, others not | `PARTIALLY_PAID`; remaining shown | Notify holdout guests; override assign |
| Guest leaves without paying | Remaining stays | Waiter `FORCE_CLOSE` with reason `WALKOUT` / `CASH_REMAINDER` |
| Shared item partially shared (<100%) | Unclaimed fraction in pool | Others can claim remainder or waiter equalizes |

**Auto-timeout (MVP):** No auto-assignment. After `PaymentSessionToken` expiry, claims freeze; waiter refreshes token or closes table.

**Table close gate:**

```
CLOSE_ALLOWED when:
  RemainingBalance = 0
  OR waiter FORCE_CLOSE with payment_method ∈ {CASH, EXTERNAL_POS, WRITE_OFF}
```

---

## 7. Conflicting claims

| Conflict type | Detection | Resolution (MVP) |
|---------------|-----------|------------------|
| Double unit claim | Two claimants commit same `AllocatableUnit` | First committed wins; second gets `409` + current owner |
| Over-full shared shares | Sum shares > 100% | Reject on commit |
| Equal split + item overlap | Equal on already-allocated units | Reject; UI lists blocking allocations |
| Custom pledge overflow | Pledges + allocations > bill total | Reject at pledge create |
| Paid guest reclaims | Claimant state `PAID` | Reject; new allocation requires refund first (V1.1) |

**Waiter override** (see §12) always supersedes guest claims with audit reason code.

---

## 8. Tips

| Rule | MVP behavior |
|------|--------------|
| Basis | Tip is **on top of** allocated food/drink/service share (inc VAT) |
| Entry | € fixed or % of guest subtotal (guest UI) |
| Min / max | €0 min; max €999.99 (sanity cap) |
| Settlement | Tip included in Mollie checkout total; passes to venue Mollie account |
| Pool vs pass-through | Venue config `tip_destination = PASS_THROUGH` (default) or `VENUE_POOL` (reporting only MVP) |
| Refund | Tip refunded only if full payment refunded (Mollie); partial tip refund manual V1.1 |

**Tax note:** Tips in NL hospitality may have specific payroll/VAT treatment — platform displays "Tip (voluntary)" and does not provide tax advice. Flag for venue accountant.

---

## 9. Checkout and settlement

### 9.1 Guest checkout amount

For claimant *c* at checkout lock:

```
subtotal_c = sum(item_allocations_inc_vat) + sc_share_c + custom_pledge_c
tip_c = guest_selected_tip
checkout_total_c = subtotal_c + tip_c
```

### 9.2 Mollie integration (MVP)

| Step | Action |
|------|--------|
| 1 | Create `CheckoutIntent` with idempotency key |
| 2 | Lock allocations for claimant (`CHECKOUT_LOCKED`) |
| 3 | POST Mollie Payment: amount, description `Table {n} – {nickname}`, redirect URL |
| 4 | Guest completes iDEAL/card/wallet |
| 5 | Webhook `paid` → `PaymentRecord.confirmed`, claimant → `PAID`, release locks |
| 6 | Recompute `RemainingBalance` |

**Architecture:** Restaurant-owned Mollie API key (pilot). Platform is SaaS orchestrator — **does not hold funds**. No crypto in MVP.

**Post-MVP (V2):** Optional crypto via separate licensed PSP; separate payment rail, not Mollie bundle.

### 9.3 Partial payments

- Multiple claimants pay independently.
- `RemainingBalance` updates after each webhook.
- Table state → `PARTIALLY_PAID` when `0 < RemainingBalance < bill_total`.
- Unpaid claimants retain `CHECKOUT_LOCKED` or release after timeout (§11).

### 9.4 Final settlement

| Condition | Table bill state |
|-----------|------------------|
| All allocations claimed AND all checkouts confirmed | `FULLY_PAID` |
| `RemainingBalance = 0` | Waiter may `CLOSE` |
| Force close with cash remainder | `CLOSED` + audit `FORCE_CLOSE` |

---

## 10. Table closure

| Action | Preconditions | Effects |
|--------|---------------|---------|
| `CLOSE_NORMAL` | `RemainingBalance = 0` | `TableSessionState → CLOSED`, token revoked, audit frozen |
| `FORCE_CLOSE_CASH` | Waiter + manager PIN (optional MVP) | Record cash amount; close with possible write-off cents |
| `FORCE_CLOSE_WALKOUT` | Manager reason | Remaining as loss; GDPR-minimal guest data retained 90d |
| `REOPEN` | Not in MVP | — |

**Post-close:** No new claims, payments, or refunds in-app (MVP refunds via Mollie dashboard + manual log).

---

## 11. Payment failures, retries, timeouts

| Event | MVP behavior |
|-------|--------------|
| Mollie payment `failed` / `canceled` | Claimant → `PAYMENT_FAILED`; allocations unlock after **15 min** lock TTL |
| Guest abandons redirect | Same as failed after Mollie expiry (~15 min) |
| Retry | Guest re-initiates checkout; **same idempotency namespace** per `(claimant_id, allocation_snapshot_hash)` for 15 min |
| Double webhook | Idempotent on `mollie_payment_id` |
| Token expiry (2h) | New claims blocked; in-flight Mollie payments still honored via webhook |
| Claim lock TTL | **30 seconds** optimistic lock on unit claim (see concurrency doc) |
| Checkout lock TTL | **15 minutes** |

**Ops risk:** Group waits for one failed iDEAL — surface "Retry" prominently; waiter can override to equal-split remaining.

---

## 12. Waiter override

| Code | Action | Audit fields |
|------|--------|--------------|
| `REASSIGN_UNIT` | Move unit from claimant A → B | reason, staff_id |
| `CLEAR_CLAIM` | Remove allocation | reason |
| `FORCE_EQUAL_REMAINING` | Equal split on unclaimed + failed payers | k, staff_id |
| `ASSIGN_UNCLAIMED_TO` | Assign all pool to one guest (cash payer) | guest_id |
| `LOCK_CLAIMS` | Pause new claims (`ALLOCATION_FROZEN`) | — |
| `UNLOCK_CLAIMS` | Resume | — |
| `BUMP_BILL_VERSION` | Edit bill lines; **invalidates** unpaid allocations | new bill_version |
| `REVOKE_TOKEN` | Invalidate payment token | force rescan |
| `MARK_CASH_PAID` | Record external cash for amount | receipt optional |

**Invariant:** Overrides cannot reduce total below already-confirmed Mollie payments without manager `REFUND_REQUIRED` flag (manual process MVP).

---

## 13. Refunds (MVP minimal)

| Scenario | MVP process |
|----------|-------------|
| Guest paid wrong amount | Manager refunds via Mollie dashboard; log in ops |
| Duplicate payment | Webhook dedupe prevents; if occurs, manual refund |
| Partial group refund | No automated line-level refund split — **V1.1** |
| Table closed, then dispute | Ops queue; claim snapshot JSON reconstructs shares |

**Post-MVP (V1.1):** In-app partial refund tied to `PaymentRecord` with split reversal rules.

---

## 14. Rules engine evaluation order

When computing a claimant's checkout preview:

1. Load bill snapshot `bill_version`.
2. Collect confirmed `Allocation`s + pending `ClaimIntent`s (exclude others' locked intents).
3. Apply pro-rata service charge for claimed menu subtotals.
4. Apply largest-remainder rounding.
5. Add CUSTOM pledges.
6. Add tip.
7. Validate `checkout_total <= RemainingBalance + own_locked_amount`.
8. Return line-level VAT breakdown for display.

**Blocking checks (fail fast):**

| Code | Condition |
|------|-----------|
| `BILL_NOT_ACTIVE` | TableSessionState ≠ PAYMENT_ACTIVE |
| `TOKEN_INVALID` | Token expired or revoked |
| `UNIT_UNAVAILABLE` | Concurrent claim lost |
| `OVERALLOCATION` | Sum allocations > bill total |
| `CLAIMS_FROZEN` | Waiter lock active |
| `CLAIMANT_PAID` | Already paid |

---

## 15. MVP vs post-MVP summary

| Capability | MVP | V1.1 | V2 |
|------------|-----|------|-----|
| Split modes ITEM/EQUAL/CUSTOM/SHARED | ✓ | ✓ | ✓ |
| Pro-rata service charge | ✓ | ✓ | ✓ |
| Line-level VAT display | ✓ | ✓ | ✓ |
| Waiter override | ✓ | + reason presets | ✓ |
| Mollie per-guest checkout | ✓ | ✓ | Connect |
| In-app partial refund | ✗ | ✓ | ✓ |
| Geo join gate | ✗ | optional | ✓ |
| Percentage custom split | ✗ | ✓ | ✓ |
| Crypto payment | ✗ | ✗ | separate rail |

---

## 16. Risk register (slice-specific)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Bill hijacking (remote QR scan) | High | PaymentSessionToken + no public bill; V1.1 geo |
| Double-allocation race | High | Optimistic locking + Redis claim locks |
| VAT receipt mismatch | Medium | Line-locked VAT; audit remainder rank |
| Service charge pro-rata dispute | Medium | Show formula in guest receipt expander |
| CUSTOM mode without itemization | Medium | Waiter review before close; cap over-pledge |
| Walkout with partial digital pay | Medium | FORCE_CLOSE codes; ops training |
| EMI scope from "overpay credit" | Critical | **Never** store spendable balance MVP |
| Tip payroll compliance | Low | Venue config disclaimer |
| Refund without allocation reversal | Medium | Snapshot at payment time; manual MVP |

---

## 17. Cross-references

- State machines: [state-machines.md](./state-machines.md)
- Numeric scenarios: [worked-examples.md](./worked-examples.md)
- Concurrency: [concurrency.md](./concurrency.md)
- MVP scope boundary: [mvp-roadmap.md](../../product/mvp-roadmap.md)

---

*Slice ownership: Part 5 — Bill-Splitting Logic. Exclusive files: `docs/domain/split-engine/*`.*
