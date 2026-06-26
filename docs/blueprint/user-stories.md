# PART 19 — MVP User Stories

**Product:** Rekentafel  
**Scope:** MVP pilot only  
**Last updated:** 2026-06-26  
**Owner mapping:** ws-1 (Guest) · ws-2 (Staff/Admin) · ws-3 (Backend/Payments)

Stories are ordered by **dependency** (backend contracts before guest UI). Each story links to flow/spec docs. **ws-4** (ui-core/infra) supports all surfaces — not primary owner here.

**Legend:** `[MVP]` required for pilot · `[P0]` launch blocker · Flow = [flows-a-o.md](../flows/flows-a-o.md)

---

## Epic map

| Epic | Stories | Primary owner | Flows |
|------|---------|---------------|-------|
| E1 — Table QR & empty experience | US-101–104 | ws-1 + ws-3 | A, B |
| E2 — Staff session & bill | US-201–208 | ws-2 + ws-3 | C, N, O |
| E3 — Payment session & join | US-301–306 | ws-1 + ws-3 | D |
| E4 — Split & claim | US-401–408 | ws-1 + ws-3 | E, F, G, H |
| E5 — Tip & Mollie checkout | US-501–508 | ws-1 + ws-3 | I, J |
| E6 — Admin & ops | US-601–606 | ws-2 + ws-3 | N, O |
| E7 — Reconciliation & audit | US-701–704 | ws-3 | J, O |

---

## E1 — Table QR and empty-table experience

### US-101 — Resolve table QR to menu landing `[MVP][P0]`

**As a** guest scanning a table QR  
**I want** to see the restaurant name, table number, and menu  
**So that** I can browse before ordering with the waiter  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 (UI) · ws-3 (`GET /t/{slug}/{code}`) |
| **Flow** | A |
| **Acceptance** | QR `https://app.rekentafel.nl/t/{slug}/{code}` renders menu; no bill lines; no pay button |
| **Spec** | [screen-inventory.md](../surfaces/screen-inventory.md) guest landing |

---

### US-102 — Browse menu with VAT-inclusive pricing note `[MVP]`

**As a** guest  
**I want** to browse categories and items with allergen info  
**So that** I can decide what to order verbally with the waiter  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 (menu API) |
| **Flow** | A |
| **Acceptance** | Categories load; prices shown; footer "Orders are taken by your server" |
| **Spec** | [flows-a-o.md](../flows/flows-a-o.md) Flow A |

---

### US-103 — Call server / ready to order signal `[MVP][P0]`

**As a** guest  
**I want** to notify staff that I need service  
**So that** I don't have to flag someone down  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 (`POST /tables/{id}/service-signals`) |
| **Flow** | B |
| **Acceptance** | Signal appears in staff inbox <2s (WS); 60s client cooldown; rate limit 5/hr/IP |
| **Spec** | [flows-a-o.md](../flows/flows-a-o.md) Flow B |

---

### US-104 — Language toggle (NL/EN) `[MVP]`

**As a** tourist guest  
**I want** to switch UI language  
**So that** I can understand the menu without an account  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 |
| **Flow** | A |
| **Acceptance** | localStorage persistence; no backend account |

---

## E2 — Staff session and bill management

### US-201 — Staff login and floor grid `[MVP][P0]`

**As a** waiter  
**I want** a floor view of all tables with status colors  
**So that** I know which tables need attention  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (`GET /staff/floor`, WS) |
| **Flow** | O |
| **Acceptance** | Login → 12+ table tiles; states EMPTY/SEATED/PAYMENT/CLOSED visible |
| **Spec** | [rbac-matrix.md](../surfaces/rbac-matrix.md) |

---

### US-202 — Service signal inbox `[MVP][P0]`

**As a** waiter  
**I want** incoming call-server signals in a list  
**So that** I can respond in order  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | B, O |
| **Acceptance** | Dismiss action; table deep link; mock WS in dev |

---

### US-203 — Start dining session `[MVP][P0]`

**As a** waiter  
**I want** to mark a table as seated  
**So that** the system knows service is in progress  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (`POST /dining-sessions`) |
| **Flow** | C |
| **Acceptance** | Table transitions `EMPTY → SEATED`; guest still sees menu only |
| **Spec** | [state-machines.md](../domain/split-engine/state-machines.md) Machine A |

---

### US-204 — Manual bill entry with VAT rates `[MVP][P0]`

**As a** waiter  
**I want** to enter bill lines with qty, price, and VAT (9%/21%)  
**So that** the open check matches the receipt  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (`POST /bills`, line CRUD) |
| **Flow** | C, O |
| **Acceptance** | 5-line bill totals match waiter calculator; service charge rule applied |
| **Example** | Table 12 €105,60 — [mvp-roadmap.md](../product/mvp-roadmap.md) |

---

### US-205 — CSV/simple bill import `[MVP]`

**As a** manager  
**I want** to import bill lines from CSV  
**So that** I can reduce typing errors on large tables  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | O |
| **Acceptance** | Import populates draft bill; waiter confirms before payment activation |

---

### US-206 — Activate payment mode and issue session token `[MVP][P0]`

**As a** waiter  
**I want** one tap to open payment with a join token/PIN  
**So that** guests can split the bill securely  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (`POST /payment-sessions/activate`) |
| **Flow** | C, D |
| **Acceptance** | Bill total > €0 gate; confirm dialog; token TTL 15 min; 6-digit PIN displayed |
| **Spec** | [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) |

---

### US-207 — Payment progress monitor `[MVP][P0]`

**As a** waiter  
**I want** to see paid vs remaining balance and active guests  
**So that** I know when to close the table  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (SSE/WS aggregates) |
| **Flow** | J, O |
| **Acceptance** | Remaining € updates on webhook; participant list with paid/pending badges |

---

### US-208 — Close table / force settle `[MVP][P0]`

**As a** waiter  
**I want** to close the table when settled or record cash remainder  
**So that** the next party gets a clean QR experience  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | J, O |
| **Acceptance** | Force close requires audit reason if remaining > €0,01; session → CLOSED; guest PII TTL scheduled |

---

## E3 — Payment session and join

### US-301 — Payment session API and token validation `[MVP][P0]`

**As the** platform  
**I want** payment sessions bound to restaurant, table, and TTL  
**So that** raw QR scans never expose the bill  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | D |
| **Acceptance** | Invalid/expired token → join gate error; max 12 joins default |
| **Spec** | [auth-and-sessions.md](../architecture/api/auth-and-sessions.md) |

---

### US-302 — Guest join gate with PIN `[MVP][P0]`

**As a** guest  
**I want** to enter a PIN or deep-link token to join  
**So that** only people at the table can pay  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 (`POST /payment-sessions/join`) |
| **Flow** | D |
| **Acceptance** | Nickname required; guest session token issued; lobby shows participants |

---

### US-303 — Payment lobby with live participant list `[MVP]`

**As a** guest  
**I want** to see who else joined the session  
**So that** we can coordinate splits  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 (SSE `participant.joined`) |
| **Flow** | D |
| **Acceptance** | List updates without refresh; no chat feature |

---

### US-304 — Block bill view without valid join `[MVP][P0]`

**As the** platform  
**I want** bill endpoints to require guest session token  
**So that** bill hijacking via QR photo is mitigated  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | D |
| **Acceptance** | `GET /payment-sessions/{id}/bill` returns 401 without token; 403 if session closed |

---

### US-305 — Session expiry and refresh UX `[MVP]`

**As a** guest  
**I want** clear messaging when the session expires  
**So that** I ask the waiter to refresh rather than assume failure  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | D, J |
| **Acceptance** | Countdown in lobby; expired state with staff instruction copy |

---

### US-306 — Rate limit distant join attempts `[MVP]`

**As the** platform  
**I want** to throttle join attempts by IP  
**So that** remote QR scraping is harder  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | D |
| **Acceptance** | 429 after threshold; logged for ops |

---

## E4 — Split and claim engine

### US-401 — Split engine core module `[MVP][P0]`

**As the** platform  
**I want** a pure split-engine with deterministic allocation math  
**So that** all clients show identical amounts  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | E–H |
| **Acceptance** | All 6 [worked-examples.md](../domain/split-engine/worked-examples.md) pass in CI |
| **Spec** | [rules-spec.md](../domain/split-engine/rules-spec.md) |

---

### US-402 — Item-level claiming UI `[MVP][P0]`

**As a** guest  
**I want** to tap items I consumed  
**So that** I pay only for my food  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 (`POST .../claims`) |
| **Flow** | E |
| **Acceptance** | Optimistic UI; 409 conflict modal with refresh; € preview updates |
| **Example** | Guest A: 1 burger + 1 cola = €18,00 ex tip |

---

### US-403 — Concurrent claim locking `[MVP][P0]`

**As the** platform  
**I want** optimistic locking on allocatable units  
**So that** two guests cannot claim the same beer  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | E |
| **Acceptance** | Torture test: 4 concurrent claims on 1 unit → 1 success, 3 conflicts |
| **Spec** | [concurrency.md](../domain/split-engine/concurrency.md) |

---

### US-404 — Equal split (subset or full table) `[MVP][P0]`

**As a** guest  
**I want** to split the remaining balance equally among N people  
**So that** we don't itemize every shared dinner  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | F |
| **Acceptance** | 2-of-4 or 6-of-6; remainder cents assigned per rules-spec |

---

### US-405 — Custom amount split `[MVP]`

**As a** guest  
**I want** to pay a specific euro amount toward the bill  
**So that** I can cover a fixed share without itemizing  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | G |
| **Acceptance** | Validation: sum of commitments ≤ remaining; min €0,50 checkout |

---

### US-406 — Shared-item N-way split `[MVP][P0]`

**As a** guest  
**I want** to mark a bottle/platter as shared among N guests  
**So that** wine splits fairly  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | H |
| **Acceptance** | €32 wine / 4 = €8,00 each ex tip; shared badge on bill |
| **Example** | [positioning.md](../product/positioning.md) wine scenario |

---

### US-407 — Service charge proportional allocation `[MVP]`

**As a** guest  
**I want** service charge split proportionally to my claimed subtotal  
**So that** the total matches the restaurant receipt  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | E–H |
| **Acceptance** | 10% service on €96 food → €9,60 allocated per rules-spec |

---

### US-408 — Waiter claim override `[MVP][P0]`

**As a** waiter  
**I want** to reassign or clear disputed claims  
**So that** table arguments don't block payment  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 (`POST /claims/{id}/override`) |
| **Flow** | E, O |
| **Acceptance** | Reason code required; audit log entry; guest sees updated bill via SSE |

---

## E5 — Tip and Mollie checkout

### US-501 — Per-guest tip selection `[MVP][P0]`

**As a** guest  
**I want** to add a tip (€ or %) before checkout  
**So that** I reward service individually  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | I |
| **Acceptance** | Tip included in Mollie payment amount; shown in summary |
| **Open** | Pass-through vs pool — [open-questions.md](./open-questions.md) Q6 |

---

### US-502 — Create Mollie checkout per guest `[MVP][P0]`

**As a** guest  
**I want** to pay my allocation via iDEAL/card through Mollie  
**So that** I don't need cash or Tikkie  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 (`POST /checkout-intents`) · ws-1 (redirect) |
| **Flow** | I, J |
| **Acceptance** | Test mode `tr_test_*` created; redirect to hosted checkout |
| **Spec** | [payment-architecture.md](../architecture/payments/payment-architecture.md) |

---

### US-503 — Mollie return URL handling `[MVP][P0]`

**As a** guest returning from Mollie  
**I want** to see success, pending, or failure clearly  
**So that** I know whether to retry  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | J |
| **Acceptance** | Pending state if webhook delayed; poll or SSE update within 30s |

---

### US-504 — Webhook reconciliation worker `[MVP][P0]`

**As the** platform  
**I want** idempotent processing of Mollie webhooks  
**So that** paid totals are accurate under retries  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | J |
| **Acceptance** | Duplicate `tr_*` webhook does not double-credit; BullMQ queue |
| **Spec** | [webhook-reconciliation.md](../architecture/payments/webhook-reconciliation.md) |

---

### US-505 — Partial payment and remaining balance `[MVP][P0]`

**As a** guest  
**I want** to see remaining balance after others pay  
**So that** I know what's left before closing  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | J |
| **Acceptance** | 4 guests, 2 pay now, 2 later — remaining accurate to cent |
| **Example** | [mvp-roadmap.md](../product/mvp-roadmap.md) partial scenario |

---

### US-506 — Failed checkout retry with claim lock `[MVP]`

**As a** guest  
**I want** to retry payment within 15 minutes without losing my claim  
**So that** a dropped iDEAL session doesn't force re-splitting  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | J |
| **Acceptance** | Same allocation_id reusable; ≥90% retry success target |

---

### US-507 — Restaurant Mollie OAuth connect `[MVP][P0]`

**As a** restaurant admin  
**I want** to connect our Mollie organization  
**So that** guest payments settle to our account  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 (UI) · ws-3 (OAuth) |
| **Flow** | N |
| **Acceptance** | Connect flow completes; encrypted token storage; test payment succeeds |
| **Spec** | [mollie-capabilities.md](../architecture/payments/mollie-capabilities.md) |

---

### US-508 — Display VAT breakdown on checkout summary `[MVP][P0]`

**As a** guest  
**I want** to see VAT portions on my share  
**So that** I trust the amount before paying  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 (display) · ws-3 (calc) |
| **Flow** | I |
| **Acceptance** | `vat_cents` from API only — no client-side VAT math |
| **Spec** | [payment-trust-patterns.md](../ux/payment-trust-patterns.md) |

---

## E6 — Admin and venue configuration

### US-601 — Venue onboarding: tables and QR PDF `[MVP][P0]`

**As a** restaurant admin  
**I want** to configure tables and print QR sheets  
**So that** every table has a scannable code  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | N |
| **Acceptance** | 20-table PDF; QR resolves correctly in guest app |
| **Spec** | [qr-lifecycle.md](../integrations/qr-lifecycle.md) |

---

### US-602 — Menu CRUD `[MVP][P0]`

**As a** restaurant admin  
**I want** to manage menu categories and items  
**So that** empty-table scans show current offerings  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | N, A |
| **Acceptance** | Changes reflect on guest menu within 60s |

---

### US-603 — Staff roles (waiter/manager) `[MVP]`

**As a** restaurant admin  
**I want** to assign staff roles  
**So that** only managers can force-close or refund  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | N |
| **Acceptance** | RBAC matches [rbac-matrix.md](../surfaces/rbac-matrix.md) |

---

### US-604 — Service charge venue setting `[MVP]`

**As a** restaurant admin  
**I want** to enable/disable service charge percentage  
**So that** bills match our policy  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | N |
| **Acceptance** | On/off + % ; applied on bill entry |
| **Open** | Mandatory vs optional — [open-questions.md](./open-questions.md) Q7 |

---

### US-605 — Manager manual refund logging `[MVP]`

**As a** manager  
**I want** to log refunds initiated in Mollie dashboard  
**So that** audit trail matches bank reality  

| Field | Value |
|-------|-------|
| **Owner** | ws-2 · ws-3 |
| **Flow** | J |
| **Acceptance** | Refund record links `tr_*` to claim snapshot |
| **Open** | Refund policy — [open-questions.md](./open-questions.md) Q5 |

---

### US-606 — Optional post-pay account link `[MVP]` (minimal)

**As a** guest  
**I want** an optional link to save receipt after payment  
**So that** I can create an account later  

| Field | Value |
|-------|-------|
| **Owner** | ws-1 · ws-3 |
| **Flow** | K (minimal) |
| **Acceptance** | No wall before pay; email capture post-success only |

---

## E7 — Reconciliation, audit, ops

### US-701 — Immutable audit log `[MVP][P0]`

**As** platform ops  
**I want** every claim, payment, and override logged  
**So that** I can reconstruct any table session  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | O |
| **Acceptance** | JSON/CSV export for one session; 7-year payment retention pseudonymized |

---

### US-702 — Webhook reconciliation dashboard `[MVP][P0]`

**As** platform ops  
**I want** to see Mollie payments mapped to claims  
**So that** I can fix webhook failures  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 (API) · ws-2 (ops UI routes) |
| **Flow** | O |
| **Acceptance** | Mismatch alert; manual reconcile action |
| **Spec** | [manual-ops-playbook.md](../integrations/manual-ops-playbook.md) |

---

### US-703 — Chargeback manual queue `[MVP]`

**As** platform ops  
**I want** a status field for disputes linked to claim snapshots  
**So that** we can respond without automation  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | O |
| **Acceptance** | Spreadsheet or in-app queue; no auto-evidence pack MVP |

---

### US-704 — OpenAPI contract + MSW fixtures `[MVP][P0]`

**As a** parallel dev team  
**I want** contract-first API with mock server  
**So that** ws-1/ws-2 can build without blocking ws-3  

| Field | Value |
|-------|-------|
| **Owner** | ws-3 |
| **Flow** | All |
| **Acceptance** | Spectral lint pass; `VITE_API_MOCK=true` happy paths A–J |
| **Spec** | [openapi-skeleton.yaml](../architecture/api/openapi-skeleton.yaml) |

---

## Story → workstream summary

| Workstream | Story count | P0 stories |
|------------|-------------|------------|
| **ws-1** (Guest) | 18 primary UI | US-101, 103, 302–303, 402, 404–406, 501–503, 505–506, 508 |
| **ws-2** (Staff/Admin) | 16 primary UI | US-201–208, 408, 507, 601–604 |
| **ws-3** (Backend) | 28 primary API/engine | US-301, 304, 306, 401, 403, 407, 502, 504–505, 507, 701–704 + all API counterparts |

---

## Deferred stories (post-MVP — do not implement)

| ID | Story | Phase | Spec |
|----|-------|-------|------|
| US-801 | Guest account + visit history | V1.1 | [mvp-roadmap.md](../product/mvp-roadmap.md) |
| US-802 | POS read-only import | V1.1 | [pos-adapter-interface.md](../integrations/pos-adapter-interface.md) |
| US-803 | Geo/proximity join gate | V1.1 | [open-questions.md](./open-questions.md) Q4 |
| US-804 | Loyalty points accrual | V2 | [rewards-ledger-model.md](../domain/loyalty/rewards-ledger-model.md) |
| US-805 | Crypto checkout | V2+ | [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) |
| US-806 | Partner rewards redemption | V2+ | [surface-map.md](../surfaces/surface-map.md) |
| US-807 | In-app split refund engine | V1.1 | [rules-spec.md](../domain/split-engine/rules-spec.md) refunds |

---

*Slice ownership: PART 19 — User Stories. Mapped to ws-1–ws-3 per [workstream-plan.md](../engineering/workstream-plan.md).*
