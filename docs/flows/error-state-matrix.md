# Error-State Matrix — Core Flows A–O

**Product:** Rekentafel (working name)  
**Slice:** Core User Flows  
**Version:** 1.0

---

## Legend

| Severity | Meaning |
|----------|---------|
| **S1** | Guest-blocking — immediate UI |
| **S2** | Degraded — retry or staff path |
| **S3** | Background — staff/ops only |
| **MVP** | Required handling in pilot |
| **DEFERRED** | Post-MVP feature area |

**Recovery types:** `retry` | `staff` | `refresh` | `exit` | `support`

---

## Guest-Facing Errors

| Code | Flows | Trigger | User message (EN) | User message (NL pilot) | Recovery | Severity | MVP |
|------|-------|---------|-------------------|---------------------------|----------|----------|-----|
| `QR_INVALID` | A | Unknown table/restaurant slug | This table link isn't valid. | Deze tafellink is ongeldig. | `exit` — ask staff | S1 | Yes |
| `QR_RESTAURANT_INACTIVE` | A | `restaurant.live=false` | This restaurant isn't available right now. | Dit restaurant is nu niet beschikbaar. | `exit` | S1 | Yes |
| `API_UNAVAILABLE` | A,B,D | 5xx / timeout | Can't reach the restaurant right now. | Geen verbinding. Probeer opnieuw. | `retry` | S2 | Yes |
| `MENU_EMPTY` | A | No menu configured | Menu coming soon. | Menu volgt binnenkort. | `staff` — call server | S2 | Yes |
| `SIGNAL_RATE_LIMITED` | B | Cooldown active | Please wait a moment before calling again. | Even wachten before opnieuw roepen. | Auto-retry timer | S2 | Yes |
| `SIGNAL_FAILED` | B | Network on POST | Couldn't send — check your connection. | Versturen mislukt — check verbinding. | `retry` | S2 | Yes |
| `PAYMENT_NOT_OPEN` | D | Scan without token / session closed | Ask your server to open the bill. | Vraag bediening om de rekening te openen. | `staff` — enter PIN | S1 | Yes |
| `JOIN_TOKEN_INVALID` | D | Bad token | This payment link isn't valid. | Deze betaallink is ongeldig. | `staff` — new PIN | S1 | Yes |
| `JOIN_TOKEN_EXPIRED` | D | TTL elapsed | This payment link expired. | Deze betaallink is verlopen. | `staff` — refresh | S1 | Yes |
| `JOIN_PIN_LOCKED` | D | 5 failed PIN attempts | Too many tries — ask your server. | Te veel pogingen — vraag bediening. | `staff` | S1 | Yes |
| `JOIN_SESSION_FULL` | D | > max participants | This table session is full. | Deze sessie is vol. | `staff` — override | S2 | Yes |
| `BILL_LOCKED` | E,F,G,H | Waiter editing bill | Server is updating the bill — try again shortly. | Bediening werkt de rekening bij — even wachten. | `refresh` 5s | S2 | Yes |
| `CLAIM_EXCEEDS_AVAILABLE` | E | Qty > remaining on line | That quantity isn't available anymore. | Dat aantal is niet meer beschikbaar. | `refresh` | S1 | Yes |
| `CLAIM_CONFLICT` | E | Concurrent claim lost | Someone else just claimed that item. | Iemand anders claimde dit net. | `refresh` | S1 | Yes |
| `SPLIT_NO_PARTICIPANTS` | F | Empty selection | Select at least one person. | Selecteer minimaal één persoon. | Fix input | S1 | Yes |
| `SPLIT_RECALC_REQUIRED` | F,H | Roster changed | Split amounts changed — please confirm again. | Bedragen gewijzigd — bevestig opnieuw. | Reconfirm | S2 | Yes |
| `CUSTOM_BELOW_MINIMUM` | G | < €0.50 | Minimum payment is €0.50. | Minimum is €0,50. | Adjust amount | S1 | Yes |
| `CUSTOM_EXCEEDS_REMAINING` | G | Amount > remaining | Amount adjusted to remaining balance. | Bedrag aangepast naar openstaand saldo. | Auto-cap | S2 | Yes |
| `SHARED_ZERO_DENOMINATOR` | H | No participants for shared | Select at least one person for this shared item. | Kies minimaal één persoon voor dit gedeelde item. | Fix selection | S1 | Yes |
| `CHECKOUT_CREATE_FAILED` | I,J | Mollie API error | Payment couldn't start — try again. | Betaling starten mislukt — probeer opnieuw. | `retry` | S1 | Yes |
| `PAYMENT_FAILED` | J | Mollie failed webhook | Payment failed — try again or use another method. | Betaling mislukt — probeer opnieuw. | `retry` | S1 | Yes |
| `PAYMENT_EXPIRED` | J | Mollie expired | Payment timed out — start again. | Betaling verlopen — start opnieuw. | `retry` | S2 | Yes |
| `PAYMENT_PENDING` | J | Webhook delay | Processing your payment… | Betaling wordt verwerkt… | Poll 30s | S2 | Yes |
| `PAYMENT_SESSION_CLOSED` | D,E,J | Table closed | This bill is closed. Thank you! | De rekening is gesloten. Bedankt! | `exit` | S1 | Yes |
| `LOYALTY_LINK_FAILED` | K | Email send fail | Couldn't send link — try again. | Link versturen mislukt. | `retry` | S2 | Yes |
| `OVERPAY_UNAVAILABLE` | L | Feature flag off | — (UI hidden) | — | N/A | — | DEFERRED |
| `REDEMPTION_UNAVAILABLE` | M | Feature flag off | — (UI hidden) | — | N/A | — | DEFERRED |

---

## Staff-Facing Errors

| Code | Flows | Trigger | Staff message | Recovery | Severity | MVP |
|------|-------|---------|---------------|----------|----------|-----|
| `STAFF_AUTH_REQUIRED` | C,O | Missing session | Please log in again. | Re-login | S1 | Yes |
| `STAFF_FORBIDDEN` | C,O | Role insufficient | You don't have permission for this action. | Manager assist | S1 | Yes |
| `TABLE_STATE_CONFLICT` | C,O | Optimistic lock fail | Updated by a colleague — refreshing. | Auto-refresh | S2 | Yes |
| `BILL_EMPTY_OPEN_PAYMENT` | C | Open payment with €0 bill | Add items before opening payment. | Add lines | S1 | Yes |
| `BILL_VAT_MISMATCH` | C,N | Line sum ≠ total | Line totals don't match bill total. | Fix lines | S1 | Yes |
| `MOLLIE_NOT_CONNECTED` | C,N,J | Missing OAuth | Payments not configured — contact manager. | Complete onboarding | S1 | Yes |
| `PAYMENT_CLOSE_BLOCKED` | J,O | Remaining > €0.01 | Cannot close — €X.XX still outstanding. | Collect or manager override | S1 | Yes |
| `MANAGER_PIN_REQUIRED` | O | Override without role | Manager PIN required. | Manager PIN | S1 | Yes |
| `WEBSOCKET_DISCONNECTED` | O | Network | Reconnecting… | Auto-reconnect | S2 | Yes |
| `REFUND_FAILED` | O | Mollie refund error | Refund failed — check Mollie dashboard. | Manual Mollie | S3 | Yes |
| `EXTERNAL_PAYMENT_REQUIRED` | O | Mollie outage flag | Record external payment to close table. | Manual terminal + audit | S2 | Yes |

---

## Platform / Ops Errors

| Code | Flows | Trigger | Ops action | MVP |
|------|-------|---------|------------|-----|
| `WEBHOOK_SIGNATURE_INVALID` | J | Bad Mollie sig | Log + alert; reject 401 | Yes |
| `WEBHOOK_DUPLICATE` | J | Idempotency hit | Ack 200; no double ledger | Yes |
| `LEDGER_INVARIANT_BREACH` | J | paid + remaining > total | Freeze table; pager | Yes |
| `RESTAURANT_ONBOARDING_STUCK` | N | Mollie KYC pending | Contact restaurant | Yes |
| `STALE_SESSION_ALERT` | C,O | Dining > 8h | Notify manager | Optional |

---

## Failure Mode → State Machine Mapping (Flow J)

| Mollie status | Internal state | Guest UI | Ledger action |
|---------------|----------------|----------|---------------|
| `open` | `checkout_pending` | Redirect to Mollie | Reserve intent only |
| `paid` | `paid` | Success screen | Decrement remaining |
| `failed` | `failed` | Retry CTA | Release intent |
| `expired` | `expired` | Timeout message | Release intent |
| `canceled` | `canceled` | Canceled message | Release intent |
| `charged_back` | `disputed` | Email only | Ops queue; loyalty reverse |

---

## Concurrent Operation Matrix (Flow E, G, J)

| Scenario | Expected system behavior | User messaging |
|----------|-------------------------|----------------|
| Two guests claim last unit | First wins; second `CLAIM_CONFLICT` | Refresh bill |
| Two custom payments exceed remaining | Second intent rejected at create | "Amount exceeds remaining" |
| Payment webhook during bill edit | Bill edit blocked if any `checkout_pending` | Staff: complete or cancel checkouts first |
| Waiter deletes claimed line | Claims auto-released; notify participants | "Item removed by staff" |

---

## Fraud & Abuse Error Handling

| Vector | Detection | Response | Flows |
|--------|-----------|----------|-------|
| Remote join via leaked token | High IP geo variance (post-MVP signal) | MVP: manual ops review on chargeback | D |
| PIN brute force | 5 fails / 15 min | `JOIN_PIN_LOCKED` | D |
| Signal spam | Rate limits | `SIGNAL_RATE_LIMITED` | B |
| Malicious overclaim | Qty invariants | `CLAIM_EXCEEDS_AVAILABLE` | E |
| Refund abuse | Partial settle + chargeback pattern | Flag account; block loyalty | J, K |

---

## GDPR / Legal Messaging

| Situation | Message principle |
|-----------|-------------------|
| Receipt email | Opt-in only; minimal PII |
| Loyalty signup | Separate marketing consent |
| Data retention | Guest session data purged 90 days post-close (configurable) |
| Flow L overpay | **No UI in MVP** — avoids implied stored-value contract |

---

## Recovery Playbooks (Staff)

### Remaining balance won't reach zero

1. Check payment monitor for failed/expired attempts  
2. Ask unpaid guests to retry or pay custom remainder  
3. Manager: record `external_payment` or split adjustment  
4. Force close only with manager PIN + reason code  

### Guest paid wrong amount (over/under)

| Case | Action |
|------|--------|
| Underpaid | Remaining balance shown; guest pays difference |
| Overpaid ≤ €2 | Manager refund via Mollie partial refund |
| Overpaid > €2 | Manager refund + audit ticket |
| Wrong items claimed | `claim.admin_override` before next payment |

### Mollie outage mid-service

1. Set restaurant flag `payments_degraded=true`  
2. Staff collect via terminal  
3. Mark `payment.external_recorded`  
4. Close table with audit note  

---

## HTTP Status Mapping (API layer)

| HTTP | When | Guest code |
|------|------|------------|
| 400 | Validation | Specific `*_INVALID` codes |
| 403 | Token/session | `JOIN_TOKEN_*`, `PAYMENT_NOT_OPEN` |
| 404 | Unknown resource | `QR_INVALID` |
| 409 | Conflict | `CLAIM_CONFLICT`, `TABLE_STATE_CONFLICT` |
| 423 | Locked | `BILL_LOCKED` |
| 429 | Rate limit | `SIGNAL_RATE_LIMITED`, `JOIN_PIN_LOCKED` |
| 503 | Upstream | `API_UNAVAILABLE`, `CHECKOUT_CREATE_FAILED` |

---

## Error Telemetry (required fields)

```json
{
  "error_code": "CLAIM_CONFLICT",
  "flow": "E",
  "restaurant_id": "uuid",
  "table_id": "uuid",
  "payment_session_id": "uuid?",
  "participant_id": "uuid?",
  "recoverable": true,
  "recovery_action": "refresh"
}
```

---

## MVP vs Deferred Summary

| Area | MVP errors handled | Deferred |
|------|-------------------|----------|
| Core QR/menu/signals | All rows marked Yes | — |
| Payment join security | PIN lock, token expiry | Geo-fence errors |
| Split/claim | Full matrix | — |
| Mollie | paid/failed/expired/canceled | Crypto errors |
| Loyalty | Link/accrual fail | Coalition redemption errors |
| Overpay/redeem | UI absent — no errors | Flow L/M entire matrix |
