# POS Adapter Interface — Read-Only Bill Sync

**Product (working name):** Rekentafel / TabSettle  
**Slice:** Part 8 — Restaurant Integration  
**Version:** 1.0 (V1.1 import / V2 POS)  
**Cross-references:** [integration-tiers.md](./integration-tiers.md), [entity-dictionary.md](../architecture/data-model/entity-dictionary.md)

---

## 1. Purpose and non-goals

This document defines the **POS adapter contract** for pulling open checks and optional menu catalogs into Rekentafel. Adapters run as **venue-scoped workers** (platform-managed or self-hosted connector).

### 1.1 In scope

- Read open check / bill by table or check ID
- Read line items, modifiers, voids, service charges, tax lines
- Optional read-only menu catalog pull
- Health check and credential validation
- Idempotent pull with cursor/version

### 1.2 Explicit non-goals (forbidden in adapter API)

| Forbidden capability | Rationale |
|---------------------|-----------|
| `createOrder()` / `addLineItem()` | Phone ordering rejected — product positioning |
| `voidLine()` / `compCheck()` from platform | Write access increases fraud and support liability |
| `fireKitchen()` / KDS integration | Out of product scope |
| `processPayment()` on POS | Mollie is PSP; no dual payment rails |
| Inventory decrement | Not a inventory system |
| Guest-facing order status | Waiter-controlled service |

**Security review gate:** Any PR adding write methods to `PosAdapter` interface is **auto-rejected**.

---

## 2. Architecture overview

```text
┌────────────────┐         pullBill / pullMenu          ┌─────────────────┐
│ POS Vendor     │ ◄────── (read-only API/export) ────── │ Venue Connector │
│ (UnTill, etc.) │                                       │ (adapter impl)  │
└────────────────┘                                       └────────┬────────┘
                                                                  │ HTTPS
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │ Integration     │
                                                         │ Service (API)   │
                                                         └────────┬────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┼──────────────┐
                    ▼                                             ▼              ▼
              Bill Service                                  Menu Staging    Audit Log
              (merge rules)                                 (admin publish)
```

**Mollie:** Payments never flow through POS adapter. Settlement remains Mollie → merchant account. Adapter may receive `external_check_id` for reconciliation only.

**Crypto:** No adapter methods for crypto. Separate rail per [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) — not exposed here.

---

## 3. Adapter registration

Each venue connector registers at provision time.

```json
{
  "adapter_id": "until_export_v1",
  "venue_id": "ven_abc123",
  "tier": "IMPORT",
  "capabilities": ["pullBill", "pullMenu"],
  "config": {
    "export_url": "https://pos.local/export",
    "auth_type": "oauth2",
    "poll_interval_seconds": 300,
    "table_mapping_strategy": "external_table_code"
  },
  "status": "ACTIVE"
}
```

| Field | Description |
|-------|-------------|
| `adapter_id` | Platform registry key |
| `tier` | `IMPORT` (V1.1 file/API) or `POS_READONLY` (V2 live) |
| `capabilities` | Subset of §4 interface |
| `table_mapping_strategy` | How POS table maps to platform `table_id` |

---

## 4. Core interface (TypeScript normative sketch)

```typescript
/** All adapters MUST implement. Write methods MUST NOT exist on this interface. */
interface PosAdapter {
  /** Adapter metadata for ops dashboard */
  getInfo(): Promise<AdapterInfo>;

  /** Validate credentials / reachability — no side effects */
  healthCheck(): Promise<HealthCheckResult>;

  /**
   * Pull open check for a table or explicit check ID.
   * Returns null if no open check (not an error).
   */
  pullBill(request: PullBillRequest): Promise<PosBill | null>;

  /**
   * Optional: full or delta menu catalog.
   * V1.1: may return CSV-equivalent structure.
   */
  pullMenu?(request: PullMenuRequest): Promise<PosMenu | null>;

  /**
   * Optional: list open checks for floor sync (V2).
   * Still read-only; does not open payment sessions.
   */
  listOpenChecks?(request: ListOpenChecksRequest): Promise<PosBillSummary[]>;
}

/** FORBIDDEN — do not implement
interface PosOrderingAdapter {
  createOrder(...): never;
  addLineItem(...): never;
}
*/
```

### 4.1 Request types

```typescript
interface PullBillRequest {
  venue_id: string;
  table_id?: string;           // platform UUID
  external_table_code?: string; // POS table number/name
  external_check_id?: string;  // if known
  dining_session_id?: string;  // platform context
  correlation_id: string;      // tracing
}

interface PullMenuRequest {
  venue_id: string;
  since_version?: string;      // delta pull
  correlation_id: string;
}

interface ListOpenChecksRequest {
  venue_id: string;
  correlation_id: string;
}
```

### 4.2 Response types

```typescript
interface PosBill {
  external_check_id: string;
  external_table_code: string;
  status: 'OPEN' | 'CLOSED' | 'VOID';
  opened_at: string;           // ISO 8601
  updated_at: string;
  currency: 'EUR';
  lines: PosBillLine[];
  subtotal_cents: number;
  service_charge_cents: number;
  vat_lines: PosVatLine[];
  total_cents: number;
  source_version: string;      // POS revision cursor
  raw_payload_ref?: string;    // S3/blob for audit (optional)
}

interface PosBillLine {
  external_line_id: string;
  description: string;
  quantity: string;            // decimal string e.g. "2.00"
  unit_price_cents: number;
  line_total_cents: number;
  vat_rate_bps: number;        // 900, 2100
  status: 'ACTIVE' | 'VOID';
  modifiers?: { name: string; price_cents: number }[];
  sku?: string;
  is_shared_hint?: boolean;
}

interface PosVatLine {
  vat_rate_bps: number;
  base_cents: number;
  vat_cents: number;
}

interface PosMenu {
  version: string;
  categories: {
    external_id: string;
    name: string;
    sort_order: number;
    items: {
      external_id: string;
      name: string;
      description?: string;
      price_cents: number;
      vat_rate_bps: number;
      available: boolean;
    }[];
  }[];
}
```

---

## 5. Platform integration service behavior

### 5.1 pullBill orchestration

```text
Staff taps "Pull from POS" OR auto on payment open (V2 config)
  → Integration Service calls adapter.pullBill()
  → Map external_table_code → table_id
  → Transform PosBill → BillDraft
  → Apply merge policy
  → Emit bill.imported event
  → Return diff to staff UI
```

### 5.2 Merge policies

| Policy | When | Behavior |
|--------|------|----------|
| `REPLACE_DRAFT` | Bill not open for payment | Replace all draft lines |
| `MERGE_APPEND` | New lines only | Add lines with new `external_line_id` |
| `BLOCK` | Payment session OPEN | Pull rejected — use manual override after cancel |
| `MANAGER_REVIEW` | Total delta > €0.50 | Hold in staging UI |

### 5.3 Mapping rules (NL VAT)

| POS tax code | Platform `vat_rate_bps` |
|--------------|-------------------------|
| Food / low rate | 900 |
| Alcohol / standard | 2100 |
| Unknown | Block import; require manager map |

### 5.4 Worked example — pullBill response

**POS check `#8842`, table `T12`**

```json
{
  "external_check_id": "8842",
  "external_table_code": "12",
  "status": "OPEN",
  "opened_at": "2026-06-26T19:12:00+02:00",
  "updated_at": "2026-06-26T20:45:00+02:00",
  "currency": "EUR",
  "lines": [
    {
      "external_line_id": "L1",
      "description": "Burger speciaal",
      "quantity": "2",
      "unit_price_cents": 1450,
      "line_total_cents": 2900,
      "vat_rate_bps": 900,
      "status": "ACTIVE"
    },
    {
      "external_line_id": "L2",
      "description": "Huiswijn rood",
      "quantity": "1",
      "unit_price_cents": 3200,
      "line_total_cents": 3200,
      "vat_rate_bps": 2100,
      "status": "ACTIVE",
      "is_shared_hint": true
    }
  ],
  "subtotal_cents": 6100,
  "service_charge_cents": 610,
  "vat_lines": [
    { "vat_rate_bps": 900, "base_cents": 2900, "vat_cents": 261 },
    { "vat_rate_bps": 2100, "base_cents": 3200, "vat_cents": 672 }
  ],
  "total_cents": 6710,
  "source_version": "8842-v3"
}
```

Platform maps to `bill_version=2`, waiter reviews, opens payment.

---

## 6. HTTP webhook variant (V1.1 file drop)

For vendors without REST API, adapter may be **file-based**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/integrations/{venue_id}/imports/bill` | POST | Multipart CSV/JSON upload |
| `/v1/integrations/{venue_id}/imports/menu` | POST | Menu CSV |

**Auth:** Venue-scoped HMAC signature `X-Rekentafel-Signature`.

**Idempotency:** Header `Idempotency-Key: {external_check_id}-{source_version}`.

---

## 7. Error model

```typescript
type AdapterErrorCode =
  | 'AUTH_FAILED'
  | 'POS_UNAVAILABLE'
  | 'CHECK_NOT_FOUND'
  | 'TABLE_MAPPING_MISSING'
  | 'SCHEMA_INVALID'
  | 'TOTAL_MISMATCH'
  | 'RATE_LIMITED'
  | 'UNSUPPORTED_CAPABILITY';

interface AdapterError {
  code: AdapterErrorCode;
  message: string;
  retryable: boolean;
  retry_after_seconds?: number;
}
```

| Code | Staff-facing message | Retry |
|------|---------------------|-------|
| `POS_UNAVAILABLE` | “Couldn’t reach POS — enter bill manually.” | Yes, 60 s |
| `CHECK_NOT_FOUND` | “No open check for this table.” | No |
| `TABLE_MAPPING_MISSING` | “Table not linked — ask manager.” | No |
| `TOTAL_MISMATCH` | “POS total doesn’t match — manager review.” | No |

---

## 8. Conformance test suite

Adapters must pass before `status=ACTIVE`:

| # | Test | Pass criteria |
|---|------|---------------|
| 1 | healthCheck | `ok: true` <3 s |
| 2 | pullBill happy path | Maps to platform bill; totals match |
| 3 | pullBill no check | Returns null, not error |
| 4 | Void line handling | VOID lines excluded from total |
| 5 | VAT mapping | 9%/21% correct on food/alcohol fixtures |
| 6 | Idempotent pull | Same `source_version` → no duplicate lines |
| 7 | **No write probe** | HTTP trace shows zero POST to order endpoints |
| 8 | Payment open block | pullBill during OPEN session → `BLOCK` unless manager |

---

## 9. Vendor priority (Netherlands)

| Vendor | V1.1 path | V2 path | Notes |
|--------|-------------|---------|-------|
| UnTill | Scheduled CSV export | REST export if licensed | High NL share |
| Lightspeed Restaurant | Reporting API read token | Official API read scope | OAuth refresh |
| Mplus Kassa | CSV | Partner API eval | Smaller venues |
| Generic CSV | `generic_csv_v1` adapter | — | Fallback |

**Bi-directional sync:** Explicitly **not** on roadmap. If vendor offers only bi-directional API, use **read-only scoped token** or export-only integration.

---

## 10. Reconciliation with Mollie

Adapter provides **bill truth**; Mollie provides **payment truth**.

| Reconciliation row | Source |
|--------------------|--------|
| `external_check_id` | POS adapter |
| `bill.total_cents` | Platform after merge |
| `payments.sum_cents` | Mollie webhooks |
| `remaining_cents` | Platform ledger |

**Close table gate:** `remaining_cents === 0` AND (optional V2) `|bill.total - pos.total| ≤ 1 cent`.

Settlement timing (T+1/T+2) is Mollie merchant dashboard — adapter does not track payouts.

---

## 11. Security and compliance

| Risk | Control |
|------|---------|
| Stolen POS read token | Rotate quarterly; IP allowlist on connector |
| Adapter MITM | TLS 1.2+; cert pinning in venue connector |
| PII in raw_payload | Strip guest names from POS if not needed; retention 90 days |
| Fraud: inflated POS pull | Manager review on delta; audit `raw_payload_ref` |
| Scope creep into ordering | Interface lint + conformance test #7 |

---

## 12. Event catalog (integration events)

| Event | Payload keys |
|-------|--------------|
| `bill.import.started` | `venue_id`, `adapter_id`, `correlation_id` |
| `bill.import.succeeded` | `bill_id`, `external_check_id`, `source_version`, `line_count` |
| `bill.import.failed` | `error_code`, `message` |
| `menu.import.succeeded` | `staging_version`, `item_count` |
| `adapter.health.degraded` | `adapter_id`, `last_ok_at` |

---

*Slice ownership: Part 8 — Restaurant Integration Model. File: `docs/integrations/pos-adapter-interface.md`.*
