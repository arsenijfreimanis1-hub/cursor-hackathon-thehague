# UX Heuristic Checklist — Design & PR Review

**Product (working name):** Rekentafel  
**Purpose:** Gate guest payment UX changes before merge or pilot deploy  
**Version:** 1.0  
**Last updated:** 2026-06-26  
**Companion:** [ux-principles.md](./ux-principles.md), [payment-trust-patterns.md](./payment-trust-patterns.md)

---

## How to Use

1. **Designer:** Self-review before handoff (Sections A–E).
2. **Engineer:** Verify implementation against Section F (component checklist).
3. **PR reviewer:** Complete Section G scoring table; **block merge** on any Critical fail.
4. **Pilot QA:** Run Section H on real devices at venue.

**Pass threshold:** All Critical ✅; High ≤1 fail with documented exception; Medium failures tracked as follow-ups.

---

## Severity Legend

| Level | Block merge? | Example |
|-------|--------------|---------|
| **Critical** | Yes | Bill visible without payment token |
| **High** | Yes (or exception ticket) | No 44px touch targets on pay button |
| **Medium** | No | Missing EN translation for new string |
| **Low** | No | Animation duration >300ms on toast |

---

## A. Scan & Entry (Flows A, B, D)

| # | Heuristic | Pass criteria | Sev | MVP |
|---|-----------|---------------|-----|-----|
| A1 | Instant context | Table # + restaurant name visible above fold within 2s | High | Yes |
| A2 | No false ordering | No cart, "Add to order," or checkout on idle/dining screens | Critical | Yes |
| A3 | State banner | Correct banner for IDLE / DINING / PAYMENT / CLOSED | High | Yes |
| A4 | Footer authority | "Orders are taken by your server" on menu screens | Medium | Yes |
| A5 | Call server throttle | Button disabled with countdown after submit (60s) | Medium | Yes |
| A6 | Language toggle | NL/EN switch without account; persists | High | Yes |
| A7 | Invalid QR | Friendly error G-010; no stack trace | High | Yes |
| A8 | No prior party data | Hard reset — no ghost claims or balances | Critical | Yes |

---

## B. Payment Gate & Join (Flow D)

| # | Heuristic | Pass criteria | Sev | MVP |
|---|-----------|---------------|-----|-----|
| B1 | **No bill without token** | Raw QR never shows line items or totals | **Critical** | Yes |
| B2 | PIN entry accessible | Numeric input 44px; `inputmode=numeric` | High | Yes |
| B3 | PIN lockout | 5 failures → `JOIN_PIN_LOCKED` message | High | Yes |
| B4 | Expired token copy | Matches error-state-matrix EN + NL | High | Yes |
| B5 | Join explainer | ≤3 slides; skippable; mentions no account | Medium | Yes |
| B6 | Exit hatch | "Not your table?" link returns to menu | Medium | Yes |
| B7 | Session full | Soft cap message + staff path | Medium | Yes |
| B8 | Display name optional | Default "Guest N"; max 12 chars | Low | Yes |

---

## C. Bill, Claims & Splits (Flows E, F, G, H)

| # | Heuristic | Pass criteria | Sev | MVP |
|---|-----------|---------------|-----|-----|
| C1 | Remaining prominent | Largest figure in sticky header | Critical | Yes |
| C2 | Avatar chips | Show claimants per line; max 3 + overflow | High | Yes |
| C3 | Unclaimed visibility | Available qty shown on partial claims | High | Yes |
| C4 | Conflict recovery | `CLAIM_CONFLICT` → toast + auto-refresh ≤3s | High | Yes |
| C5 | Undo window | 10s undo toast on own claim release | Medium | Yes |
| C6 | Shared badge | 🍽 + label; distinct from individual claim | High | Yes |
| C7 | Equal split formula | Shows `total ÷ N = per person` before confirm | High | Yes |
| C8 | Whole-bill equal off | Split entire bill requires waiter confirm (hidden/default off) | Critical | Yes |
| C9 | Custom amount bounds | Min €0.50; max remaining; auto-cap message | High | Yes |
| C10 | Custom ≠ tip | Separate screens/labels; no combined field | High | Yes |
| C11 | Rounding note | Visible when cents remainder assigned | Medium | Yes |
| C12 | Bill lock banner | `BILL_LOCKED` non-blocking banner | High | Yes |
| C13 | Real-time sync | Remaining updates ≤3s poll / ≤1s WS after payment | Critical | Yes |

---

## D. Tip & Checkout (Flows I, J)

| # | Heuristic | Pass criteria | Sev | MVP |
|---|-----------|---------------|-----|-----|
| D1 | **0% tip default** | Zero pre-selected; same visual weight as other presets | Critical | Yes |
| D2 | No guilt copy | No "Most people tip X%" or countdown | Critical | Yes |
| D3 | Tip basis shown | "Tip on your share: €X.XX" | High | Yes |
| D4 | Service charge distinction | Separate line when bill includes service charge | High | Yes |
| D5 | Merchant identification | Restaurant legal name on checkout summary | Critical | Yes |
| D6 | Pay amount clarity | Single large total; breakdown expandable | High | Yes |
| D7 | Mollie handoff loading | G-016 spinner + "Secure payment" copy | High | Yes |
| D8 | No account gate | Email/phone not required before Pay CTA | **Critical** | Yes |
| D9 | Minimum payment | €0.50 enforced with clear message | High | Yes |

---

## E. Payment Result & Partial Pay (Flow J)

| # | Heuristic | Pass criteria | Sev | MVP |
|---|-----------|---------------|-----|-----|
| E1 | Webhook honesty | Success only after confirm or poll timeout handling | Critical | Yes |
| E2 | Processing state | "Processing your payment…" if webhook delayed | High | Yes |
| E3 | Partial remaining | All participants see updated remaining | Critical | Yes |
| E4 | Failed retry | Clear retry CTA; preserve allocation | High | Yes |
| E5 | Expired session | Distinct copy from failed payment | Medium | Yes |
| E6 | Receipt opt-in | Post-success email optional; skip prominent | High | Yes |
| E7 | Session closed | Thank-you; no pay CTAs | High | Yes |
| E8 | Participant roster | G-018 shows who paid / who owes | Medium | Yes |

---

## F. Component-Level Review

Use when changing specific UI components.

### F1. Remaining Balance Banner

| Check | Spec |
|-------|------|
| Placement | Sticky top on G-007, G-008, G-018 |
| Typography | ≥24px mobile; currency formatted per locale |
| Live region | `aria-live="polite"` |
| Progress | Bar or "€X of €Y paid" secondary line |
| Color | Not red unless overdue/waiter flag (post-MVP) |

### F2. Claim Row

| Check | Spec |
|-------|------|
| Tap target | Full row 44px min height |
| Stepper | +/- buttons 44px; disabled at 0 and max |
| States | Available / partial / fully claimed / shared |
| Loading | Skeleton on initial fetch; inline spinner on claim submit |

### F3. Claim Conflict Modal/Toast

| Check | Spec |
|-------|------|
| Trigger | HTTP 409 / `CLAIM_CONFLICT` |
| Copy EN | "Someone else just claimed that item." |
| Copy NL | "Iemand anders claimde dit net." |
| Action | Primary: Refresh bill; no dismiss-only |
| Duration | Toast 5s or until refresh complete |

### F4. Tip Selector

| Check | Spec |
|-------|------|
| Control type | Radio group, not slider-only |
| Presets | 0%, 5%, 10%, 15%, Custom |
| Custom | Opens numeric input; validates ≥0 |
| Summary | Updates total live below presets |

### F5. Checkout Summary (G-015)

| Check | Spec |
|-------|------|
| Lines | Share, tip, total — no hidden fees |
| CTA | "Pay €X.XX" with exact amount |
| Secondary | Back to bill without losing allocations |
| Trust | "Payment to [Restaurant] via Mollie" |

### F6. Mollie Redirect Shim (G-016)

| Check | Spec |
|-------|------|
| State | Loading only; no second confirm |
| Timeout | 30s → error + retry checkout create |
| Back button | Warn: "Payment may still be processing" |

### F7. Payment Result (G-017)

| State | Primary content | Secondary | CTA |
|-------|-----------------|-----------|-----|
| `paid` | "Paid €X.XX" | Remaining if partial | View bill / Done |
| `pending` | Processing spinner | "This may take a moment" | None (auto-poll) |
| `failed` | "Payment failed" | Reason if known | Try again |
| `expired` | "Payment timed out" | — | Start again |
| `canceled` | "Payment canceled" | — | Return to bill |

### F8. Partial Pay Screen (G-018)

| Check | Spec |
|-------|------|
| Header | Remaining €XX.XX |
| List | Participants: Paid ✓ / Owes €X / Processing |
| CTA | "Pay my share" if current user owes |
| Waiter note | "Ask your server if you need help" |

### F9. Language Toggle

| Check | Spec |
|-------|------|
| Position | Header right |
| Scope | All visible strings switch |
| Persistence | `localStorage.rekentafel_locale` |
| Payment strings | 100% coverage both locales |

### F10. Accessibility Spot Checks

| Check | Tool |
|-------|------|
| axe clean on G-006–G-018 | CI / manual |
| Keyboard path join → pay | Manual tab audit |
| VoiceOver/TalkBack on tip + pay | Device test |
| Contrast on error text | Lighthouse |

---

## G. PR Review Scorecard

**PR title:** _______________________  
**Reviewer:** _______________________  
**Date:** _______________________

| Section | Critical fails | High fails | Pass? |
|---------|----------------|------------|-------|
| A. Scan & entry | | | ☐ |
| B. Payment gate | | | ☐ |
| C. Bill & splits | | | ☐ |
| D. Tip & checkout | | | ☐ |
| E. Payment result | | | ☐ |
| F. Components (list changed) | | | ☐ |

**Non-negotiables (must all pass):**

- [ ] B1 — No bill without token
- [ ] D8 — No account before pay
- [ ] D1 — 0% tip default
- [ ] D2 — No tip dark patterns
- [ ] C13 — Remaining sync
- [ ] E1 — No false payment success

**i18n:**

- [ ] New strings have `nl` and `en` keys
- [ ] Error codes match [error-state-matrix.md](../flows/error-state-matrix.md)

**Deferred feature leak:**

- [ ] No crypto UI
- [ ] No wallet / overpay UI
- [ ] No phone ordering cart
- [ ] No discovery feed

**Decision:** ☐ Approve  ☐ Approve with exceptions  ☐ Block

**Exception notes:** _______________________

---

## H. Pilot Device QA Script

Run on **iPhone Safari**, **Android Chrome**, and one **low-end device**.

| Step | Action | Expected | Pass |
|------|--------|----------|------|
| 1 | Scan idle QR | Menu only; no bill | ☐ |
| 2 | Tap call server | Confirmation + cooldown | ☐ |
| 3 | Switch EN → NL | All strings update | ☐ |
| 4 | Scan without payment open | PIN gate; no bill lines | ☐ |
| 5 | Enter PIN | Lobby + remaining | ☐ |
| 6 | Two devices claim same item | One wins; other refreshes | ☐ |
| 7 | Pay with test iDEAL | Mollie → success → remaining updates on both devices | ☐ |
| 8 | Leave tip at 0% | Checkout proceeds | ☐ |
| 9 | Kill browser mid-Mollie | Return URL handles pending | ☐ |
| 10 | Zoom 200% | Payment screens usable | ☐ |

---

## I. Copy & Tone Review

| # | Check | Fail example |
|---|-------|--------------|
| I1 | Sentences ≤15 words on errors | "We were unable to process your request at this time due to…" |
| I2 | Active voice | "Payment failed" not "Payment has been failed" |
| I3 | No blame on guest for conflicts | Not "You were too slow" |
| I4 | Staff-directed recovery | "Ask your server" when guest can't self-serve |
| I5 | EUR formatting correct per locale | `€12,10` NL / `€12.10` EN |
| I6 | No emoji in error states | Except 🍽 shared badge context |

---

## J. Anti-Patterns (Automatic Fail)

| Anti-pattern | Why |
|--------------|-----|
| Login modal before Pay | Violates P2 |
| Pre-selected 10% tip | Violates P8 |
| Whole bill on QR scan | Violates P3 |
| Green checkmark before webhook | Violates P12 |
| "Create account to save 10%" at checkout | Growth hack / abandonment |
| Platform name as merchant on Mollie summary | Trust failure |
| Hidden service charge added at checkout | Transparency failure |
| Split whole bill without confirm | Financial risk |

---

## K. Post-MVP Items (Do Not Block MVP)

Track but do not fail MVP PRs:

- Geo-fence join UX
- PWA install banner
- High-contrast theme
- Staff panel EN localization
- Crypto method selector
- Loyalty earn animations
- Partner voucher entry

---

## Review Cadence

| When | Who | Artifact |
|------|-----|----------|
| Every guest UI PR | Engineer + reviewer | Section G scorecard |
| Weekly pre-pilot | Design + product | Full A–E pass |
| Pilot week 1 | Venue shadow | Section H script |
| Post-incident | Ops + eng | Add row to Section J if new anti-pattern |
