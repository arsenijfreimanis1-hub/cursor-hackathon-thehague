# Manual Ops Playbook — Single-Venue Pilot

**Product (working name):** Rekentafel / TabSettle  
**Audience:** Pilot venue manager, shift leads, waitstaff, platform ops  
**Scope:** Tier 0 (MVP manual integration) — executable without POS  
**Cross-references:** [integration-tiers.md](./integration-tiers.md), [qr-lifecycle.md](./qr-lifecycle.md), [flows-a-o.md](../flows/flows-a-o.md) Flow C, D, O

---

## 1. Purpose

This playbook is the **operating manual** for the first Netherlands pilot venue. Every procedure assumes:

- Waiters take orders **off-platform** (verbal/POS terminal at bar).
- Guests pay via Rekentafel **only after** waiter activates payment mode.
- **No phone ordering** — menu on guest phone is browse-only.

---

## 2. Roles and access

| Role | Login | Can do | Cannot do |
|------|-------|--------|-----------|
| **Server** | Staff app PIN | Start session, enter bill, open payment, ack signals, close table (if €0) | Force close with balance, refund, edit menu |
| **Shift lead** | Staff app | All server + override claims, refresh token, cancel payment mode | Change Mollie keys, deactivate QR |
| **Manager** | Admin + staff | All above + menu/tables, CSV import, force close, refund log | Platform ops |
| **Platform ops** | Ops dashboard | Provision venue, QR batch, incident response | — |

---

## 3. Pre-opening checklist (manager, 30 min)

| # | Task | Done when |
|---|------|-----------|
| 1 | Verify internet and staff tablets charged | Ping `guest.rekentafel.nl` OK |
| 2 | Confirm Mollie connection green in admin | Test mode off for live service |
| 3 | Spot-check 3 random table QRs scan to correct table | Table number matches sticker |
| 4 | Publish menu if changes since yesterday | Admin → Menu → Published timestamp today |
| 5 | Brief floor: “Start table → enter bill → open payment” | Lead initials training log |
| 6 | Stock QR backup stickers at host stand | See [qr-lifecycle.md](./qr-lifecycle.md) |
| 7 | Post laminated **one-page flow chart** at POS | Appendix A |

---

## 4. Core service procedures

### 4.1 QR sticker lifecycle (summary)

Full detail: [qr-lifecycle.md](./qr-lifecycle.md).

| Event | Action |
|-------|--------|
| New table / sticker damaged | Apply backup sticker; log in admin |
| Table renumbered | Admin reassign QR; **do not** cross out old number only |
| Sticker removed permanently | Deactivate old QR in admin (410 Gone for guests) |

### 4.2 Open table (start dining session)

**When:** Guests seated.

| Step | Waiter action | Expected UI |
|------|---------------|-------------|
| 1 | Open staff app → floor plan | Table grey (EMPTY) |
| 2 | Tap table → **Start table** | Confirmation |
| 3 | Optional: enter party size | Blue (SEATED) |
| 4 | Serve guests via normal POS/paper | No guest bill visible yet |

**If skipped:** Guest QR still shows menu + call server. Payment cannot open until session started.

**Time target:** ≤10 seconds.

### 4.3 Call-server / ready-to-order signals

| Step | Action |
|------|--------|
| 1 | Guest taps “Call server” on phone |
| 2 | Signal appears in staff **Inbox** with table number |
| 3 | Waiter taps **Ack** when attending |
| 4 | If spam: table auto-rate-limits (60 s cooldown) |

**Do not:** Tell guests to order from the phone menu.

### 4.4 Bill entry (manual)

**When:** Items delivered; guest requests bill or waiter preemptively prepares.

| Step | Action | Notes |
|------|--------|-------|
| 1 | Table detail → **Bill** tab | |
| 2 | Add lines OR upload CSV (manager) | Match printed POS receipt |
| 3 | Apply service charge if venue uses it | Default 10% on food — confirm setting |
| 4 | Review VAT breakdown | 9% food, 21% alcohol |
| 5 | Tap **Validate bill** | Fix errors before payment open |

**Worked example — Table 12:**

| Line | Qty | Unit | VAT | Total |
|------|-----|------|-----|-------|
| Burger | 2 | €14.50 | 9% | €29.00 |
| Steak | 1 | €28.00 | 9% | €28.00 |
| Wine | 1 | €32.00 | 21% | €32.00 |
| Cola | 2 | €3.50 | 9% | €7.00 |
| Service 10% | — | — | 9% | €9.60 |
| **Total** | | | | **€105.60** |

**Common errors:**

| Mistake | Fix |
|---------|-----|
| Wine at 9% VAT | Change to 21% before open |
| Duplicate line | Swipe delete → confirm |
| Wrong table | Manager: move bill (MVP: void and re-enter — move is V1.1) |

### 4.5 Activate payment mode

**When:** Bill validated; guests ready to pay.

| Step | Waiter action | Guest experience |
|------|---------------|------------------|
| 1 | Tap **Open payment** | Confirmation: “Guests can pay from phones” |
| 2 | Confirm dialog | Table amber (PAYMENT_ACTIVE) |
| 3 | Show guest **session QR** or read **6-digit PIN** | Guests scan/enter → join lobby |
| 4 | Monitor **Payment** tab | Remaining balance updates live |

**Say to guests:** “Scan the code on my screen, or enter PIN 482913 — you can split the bill.”

**Never:** Share PIN in Instagram story or public channel.

**Time target:** ≤30 seconds from bill ready to payment open (pilot KPI).

### 4.6 During payment session

| Situation | Procedure |
|-----------|-----------|
| Guest can’t join | Refresh PIN; check token not expired |
| Wrong item claimed | Shift lead → **Override claim** → reassign |
| Guest pays wrong amount | Custom amount allowed; or override after failed split |
| Partial pay (2 of 4 paid) | Normal — remaining balance shown; others pay later |
| Guest wants cash | Mark **External payment** in staff app (manager); reduce remaining manually |
| Dispute at table | **Pause payment** → fix claims → **Resume** |

### 4.7 Close table

| Precondition | Action |
|--------------|--------|
| Remaining balance €0.00 | Waiter → **Close table** |
| Remaining > €0 | Collect cash/terminal OR manager force close with reason |
| After close | Table returns EMPTY; audit frozen |

---

## 5. Shift handoff procedure

**When:** Shift change with open tables.

### 5.1 Outgoing shift lead (10 min before handoff)

| # | Task |
|---|------|
| 1 | Export **Open tables** screenshot or shift summary PDF |
| 2 | For each PAYMENT_ACTIVE table: note remaining €, PIN expiry, disputes |
| 3 | Ack all stale service signals or document |
| 4 | Log handoff note in staff app (free text) |

### 5.2 Handoff brief template

```text
HANDOFF — {date} {time} — {outgoing} → {incoming}

Open tables:
- T7  SEATED      — no bill yet, party 4, birthday
- T12 PAYMENT     — €24.39 remaining, 2/4 paid, PIN expires 21:45
- T3  PAYMENT     — dispute on wine split, lead aware

Incidents:
- 19:20 Mollie timeout T9 — resolved, guest retried OK

Stock:
- QR backups: 8 remaining
```

### 5.3 Incoming shift lead

| # | Task |
|---|------|
| 1 | Read handoff note |
| 2 | Physically walk open payment tables if >€50 remaining |
| 3 | Refresh tokens expiring within 30 min |
| 4 | Confirm Mollie status green |

---

## 6. Offline fallback procedures

Internet or platform outage does **not** stop food service. Payment falls back to traditional methods.

### 6.1 Failure detection

| Symptom | Likely cause |
|---------|--------------|
| Staff app “Reconnecting…” >2 min | Venue WiFi or platform outage |
| Guest “Can’t join” widespread | Platform outage |
| Mollie checkout fails all guests | PSP outage |
| Only one tablet | Device issue — switch tablet |

### 6.2 Decision tree

```text
Internet down?
├─ Yes → Paper receipts + terminal/cash ONLY
│         Log tables on paper handoff sheet (Appendix B)
│         Enter into system when restored (manager)
└─ No → Platform up?
    ├─ No → Same as internet down for payment
    └─ Yes → Mollie up?
        ├─ No → Terminal/cash; mark external payment
        └─ Yes → Support ticket; use PIN refresh
```

### 6.3 Offline payment procedure

| Step | Action |
|------|--------|
| 1 | Shift lead declares **offline mode** verbally to floor |
| 2 | Waiters use **existing** card terminal or cash |
| 3 | Paper log: table, amount, method, waiter initials |
| 4 | Do **not** promise guests “pay by phone later” without manager approval |
| 5 | When online: manager backfills **External payment** rows OR opens adjustment incident |

### 6.4 Partial outage (guest join OK, Mollie fail)

| Step | Action |
|------|--------|
| 1 | Staff app shows Mollie incident banner |
| 2 | Collect via terminal; tap **Record external payment** per guest |
| 3 | Platform ops notified automatically if webhook error rate >10% |

### 6.5 Post-outage reconciliation

| # | Manager task |
|---|--------------|
| 1 | Match paper log to Mollie dashboard settlements |
| 2 | Close orphaned PAYMENT_ACTIVE tables |
| 3 | File incident report within 24 h |

---

## 7. Training program

### 7.1 Training burden estimate

| Audience | Format | Duration | Refresh |
|----------|--------|----------|---------|
| New waiter | In-person + shadow 1 table | **45 min** | — |
| Experienced waiter (new hire mid-pilot) | Video + checklist | **25 min** | — |
| Shift lead | Above + overrides | **+20 min** (65 total) | Monthly 15 min |
| Manager | Admin + CSV + incidents | **90 min** | Quarterly |
| **Venue total (8 waiters, 2 leads, 1 manager)** | | **~8.5 staff-hours** initial | ~2 h/month |

**Pilot week 1 add-on:** Platform ops on-site or video call for first service — **+2 h**.

**Challenge to master prompt:** “Single activate-payment affordance” reduces burden but **bill entry** is the hidden cost. Budget **15 min/week** manager time for bill accuracy review through week 8.

### 7.2 Training checklist (waiter sign-off)

| # | Skill | Demonstrated |
|---|-------|--------------|
| 1 | Log in to staff app | ☐ |
| 2 | Start table session | ☐ |
| 3 | Ack call-server signal | ☐ |
| 4 | Enter 3-line bill with correct VAT | ☐ |
| 5 | Open payment and show PIN/QR | ☐ |
| 6 | Explain to guest: scan, split, tip, pay | ☐ |
| 7 | Monitor remaining balance | ☐ |
| 8 | Close table at €0 | ☐ |
| 9 | Know when to call shift lead (dispute, Mollie fail) | ☐ |
| 10 | State: guests cannot order from phone | ☐ |

### 7.3 60-second waiter script (in-app tutorial copy)

> “When guests sit, tap Start table. When they’re ready to pay, enter the bill exactly like the receipt, then Open payment. Show them the PIN or QR on your screen. They split and pay on their phones — you close the table when it hits zero. They order with you, not the app.”

---

## 8. Incident response (pilot)

| Severity | Example | Response time | Owner |
|----------|---------|---------------|-------|
| P1 | No payments site-wide | 15 min | Platform ops |
| P2 | Single venue cannot open payment | 30 min | Platform ops + manager |
| P3 | Claim dispute | Immediate | Shift lead |
| P4 | Wrong menu price | Next business day | Manager |

**Platform ops contact:** `{ops_oncall}` — configured in admin.

---

## 9. Daily manager closing (15 min)

| # | Task |
|---|------|
| 1 | All tables CLOSED or documented |
| 2 | Reconcile Mollie dashboard total vs app payments export |
| 3 | Review override audit log (target: ≤2/session avg) |
| 4 | Note QR damage / reorder stickers |
| 5 | Submit shift summary (auto-generated + notes) |

---

## Appendix A — One-page floor flow chart

```text
SEAT → START TABLE (blue)
  ↓
SERVE (normal ordering — NOT app)
  ↓
ENTER BILL (match receipt)
  ↓
OPEN PAYMENT (amber) → show PIN/QR
  ↓
GUESTS PAY PHONES (split/tip/iDEAL)
  ↓
REMAINING = €0 ?
  ├─ Yes → CLOSE TABLE (grey)
  └─ No  → nudge guests OR cash/terminal OR call lead
```

---

## Appendix B — Offline payment log (paper)

| Time | Table | Amount € | Method | Waiter | Notes |
|------|-------|----------|--------|--------|-------|
| | | | cash/card terminal | | |

---

## Appendix C — Legal and fraud reminders

| Topic | Guidance |
|-------|----------|
| Bill accuracy | Merchant responsible for VAT on receipt; app displays waiter-entered data |
| Tips | Pass-through to venue; not platform-held |
| Guest PII | No phone required to pay; optional email receipt |
| Bill hijacking | Do not post PIN publicly; rotate if leaked |
| Walkout | Manager force close; police/internal policy — not app scope |

---

*Slice ownership: Part 8 — Restaurant Integration Model. File: `docs/integrations/manual-ops-playbook.md`.*
