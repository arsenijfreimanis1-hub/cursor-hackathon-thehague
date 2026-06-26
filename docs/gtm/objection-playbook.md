# Objection Playbook — Owners, Staff, Guests

**Product (working name):** Rekentafel  
**Slice:** Part 14 — Go-To-Market Plan and Pilot Scorecard  
**Audience:** Founders, sales, pilot onboarding, floor trainers  
**Last updated:** 2026-06-26  
**Cross-references:** [gtm-plan.md](./gtm-plan.md), [positioning.md](../product/positioning.md), [manual-ops-playbook.md](../integrations/manual-ops-playbook.md)

---

## 1. How to use this playbook

Each objection includes:

- **Heard as** — natural language from the stakeholder
- **Root fear** — what they actually worry about
- **Response** — factual talk track (≤60 sec spoken)
- **Proof / demo** — what to show
- **Escalate if** — when to pause sale or change scope
- **MVP vs post-MVP** — what exists today vs later

**Voice rule for waitstaff:** One sentence answers only; full script for managers/owners.

---

## 2. Owner / manager objections

### O1 — "We already use Tikkie. It works fine."

| Field | Content |
|-------|---------|
| **Heard as** | "Our guests are Dutch; everyone has Tikkie." |
| **Root fear** | Adding cost/complexity for no gain |
| **Response** | Tikkie settles **after** someone leaves with the bill. Rekentafel settles **at the table** against the real itemized check — shared wine, partial pay, no wrong amounts. You keep the table 6–10 minutes longer today than you need to. |
| **Proof** | Side-by-side timeline: terminal+Tikkie 16 min vs Rekentafel 10 min ([pilot-scorecard.md](./pilot-scorecard.md) M3). Demo shared bottle split. |
| **Escalate if** | >80% tables are 2-tops with €40 checks — weak wedge |
| **MVP** | Full split + iDEAL | **Post-MVP** | Receipt in guest account (V1.1) |

---

### O2 — "We don't want guests ordering from their phones."

| Field | Content |
|-------|---------|
| **Heard as** | "QR menus killed service at my friend's place." |
| **Root fear** | Waiter disintermediation; brand damage |
| **Response** | Neither do we. **Waiters take every order.** The QR shows menu and call-server before the meal; **payment opens only when your staff activates it.** No kitchen tickets from guest phones. |
| **Proof** | Empty-table scan → menu only. Seated → still no bill. Payment mode → bill appears. |
| **Escalate if** | Owner wants phone ordering — wrong product |
| **MVP** | Call-server signal | **Never** | Phone ordering |

---

### O3 — "Our POS already has pay-at-table."

| Field | Content |
|-------|---------|
| **Heard as** | "Lightspeed/UnTill can do payments." |
| **Root fear** | Duplicate spend |
| **Response** | Terminals excel at **one card, one amount**. Can six guests pay **in parallel on their own phones** without passing a device or trusting a stranger? Rekentafel is the multi-payer layer; your POS stays source of truth in MVP via manual re-key. |
| **Proof** | Live 4-phone parallel checkout. Remaining balance bar on waiter tablet. |
| **Escalate if** | POS vendor contract forbids complementary payment tools — legal review |
| **MVP** | Manual bill entry | **V1.1** | POS CSV import | **V2** | Read-only sync |

---

### O4 — "Manual bill entry is too much work."

| Field | Content |
|-------|---------|
| **Heard as** | "My waiters won't re-type the whole check." |
| **Root fear** | Labor cost; errors |
| **Response** | Honest answer: MVP is **Tier 0** — waiter enters 6–10 lines in about 2–3 minutes, or manager CSV-imports. We picked pilots with **simple à la carte menus** for that reason. POS auto-sync is V1.1 after we prove guests actually pay. |
| **Proof** | Timed bill entry in discovery. Quick-add favorites (10 slots). Error rate target ≤5% ([pilot-scorecard.md](./pilot-scorecard.md) M10). |
| **Escalate if** | Tasting menu or 100+ SKU daily — **disqualify ICP** |
| **MVP** | Manual + CSV | **V1.1** | Scheduled import |

**Weak assumption challenged:** *"Owners will accept manual entry forever."* They won't — manual entry is a **pilot tax**, not the value prop.

---

### O5 — "Who holds the money? Are you a bank?"

| Field | Content |
|-------|---------|
| **Heard as** | "I don't want PSD2 problems." |
| **Root fear** | Regulatory surprise; payout delay |
| **Response** | **Your Mollie merchant account** receives guest payments. Rekentafel is software — we don't hold guest funds overnight. No stored wallet, no platform credit in MVP. Settlement timing is Mollie's T+1/T+2, same as today. |
| **Proof** | Admin Mollie connection screen; MSA clause; [payment-architecture.md](../architecture/payments/payment-architecture.md). |
| **Escalate if** | Owner demands platform-held tips pool without license — counsel |
| **MVP** | Merchant Mollie | **V2** | Mollie Connect (optional bps) | **Never MVP** | Crypto, e-money wallet |

---

### O6 — "What if someone not at the table scans and pays?"

| Field | Content |
|-------|---------|
| **Heard as** | "QR codes leak on social media." |
| **Root fear** | Fraud; guest disputes |
| **Response** | Scanning the table QR **never shows the live bill**. Bill appears only after **your waiter opens payment** with a short-lived session PIN. Optional table PIN for high-risk nights. |
| **Proof** | Scan without activation → menu only. Threat model T-03 ([threat-register.md](../security/threat-register.md)). |
| **Escalate if** | Hijack rate >2% in pilot — enable mandatory PIN |
| **MVP** | Waiter unlock + session token | **V1.1** | Optional geo |

---

### O7 — "Guests won't scan another QR."

| Field | Content |
|-------|---------|
| **Heard as** | "QR fatigue after COVID." |
| **Root fear** | Dead feature; wasted stickers |
| **Response** | No app install. One scan → claim your items → iDEAL. Same behavior as paying a webshop. Pilot target: **50% of eligible tables** choose it when staff offer — not 100%. |
| **Proof** | Guest flow <90 sec on 4G. Table tent NL copy. |
| **Escalate if** | Activation <25% week 6 after staff training — UX or ICP issue |
| **MVP** | Web only | **V1.1** | PWA install prompt |

---

### O8 — "What does it cost?"

| Field | Content |
|-------|---------|
| **Heard as** | "Another SaaS subscription." |
| **Root fear** | ROI uncertainty |
| **Response** | **8-week pilot is free.** You pay Mollie transaction fees only — same as card today. Post-pilot we're testing **€79–€129/month flat** or low bps; you decide after we show turn-time data. |
| **Proof** | ROI sketch: 6.8 min × 13 tables × 2 nights ≈ 3 staff-hours/week ([pilot-scorecard.md](./pilot-scorecard.md)). |
| **Escalate if** | Owner wants rev-share only before proof — defer |
| **MVP** | Free pilot | **V1.1** | Pricing test |

---

### O9 — "VAT and receipts — my accountant will hate this."

| Field | Content |
|-------|---------|
| **Heard as** | "Split checks must match boekhouding." |
| **Root fear** | Compliance exposure |
| **Response** | We show **line-level 9%/21% VAT** on splits. Each guest payment maps to Mollie with itemized audit log. Fiscal receipt printing stays on your POS for MVP — we don't replace your boekhouding, we itemize who paid what. |
| **Proof** | Export JSON for one table; worked example €105.60 bill. |
| **Escalate if** | Accountant requires fiscal receipt per guest — document gap; POS sync V2 |
| **MVP** | VAT display + audit | **V2** | Fiscal printer integration (if ever) |

---

### O10 — "My staff turnover is too high to train."

| Field | Content |
|-------|---------|
| **Heard as** | "New waiters every month." |
| **Root fear** | Broken service |
| **Response** | Training is **45 minutes**: start table → enter bill → open payment → close. Laminated one-pager at POS. If turnover >40%/year, we delay until shift lead stable or waitlist V1.1 self-serve video. |
| **Proof** | [manual-ops-playbook.md](../integrations/manual-ops-playbook.md) Appendix A flow chart. |
| **Escalate if** | Cannot get 2 consecutive weeks with same shift lead — defer pilot |
| **MVP** | Founder-led training | **V1.1** | Video certification |

---

## 3. Staff / waiter objections

### S1 — "This replaces my tips."

| Field | Content |
|-------|---------|
| **Heard as** | "Guests won't tip me on the terminal." |
| **Root fear** | Income loss |
| **Response** | Each guest adds **their own tip** before iDEAL checkout. Default pass-through to your venue's tip rules — same pool as today. |
| **Proof** | Guest checkout tip screen; manager tip config. |
| **Escalate if** | Venue uses hidden service charge only — clarify display |
| **MVP** | Per-guest tip | **V1.1** | Tip pool reporting |

**One-line (voice):** "Tips stay yours — each guest tips on their own phone."

---

### S2 — "Extra taps when I'm slammed."

| Field | Content |
|-------|---------|
| **Heard as** | "I don't have time to type the bill twice." |
| **Root fear** | Workload |
| **Response** | Three taps after service: **Bill → Validate → Open payment.** Typing lines is once, about 2 minutes for a normal four-top — less time than running the terminal three times. |
| **Proof** | Timed demo; quick-add favorites for coffee/bitters. |
| **Escalate if** | Median bill entry >5 min — menu too complex |
| **MVP** | 10 quick-add slots | **V1.1** | CSV import |

**One-line (voice):** "Open payment once; guests pay themselves."

---

### S3 — "Guests will argue about who ate what."

| Field | Content |
|-------|---------|
| **Heard as** | "I'll still have to settle fights." |
| **Root fear** | Conflict mediator role |
| **Response** | They argue on their phones, not with you. If stuck, shift lead taps **Override claim** — you confirm, done. Target: overrides on **≤8%** of tables. |
| **Proof** | Override flow <2 min; shared wine 4-way preset. |
| **Escalate if** | Override >15% — UX training issue |
| **MVP** | Override + pause payment | **V1.1** | Split presets |

**One-line (voice):** "They split on their phones; you override if needed."

---

### S4 — "What if the app breaks mid-service?"

| Field | Content |
|-------|---------|
| **Heard as** | "I can't risk Friday night." |
| **Root fear** | Career embarrassment |
| **Response** | Fallback is **today's flow**: one terminal payment or cash. Rekentafel is optional per table. Internet down → terminal only; menu QR may cache. |
| **Proof** | Incident playbook §8 ([manual-ops-playbook.md](../integrations/manual-ops-playbook.md)). |
| **Escalate if** | Two outage nights in one week — ops postmortem |
| **MVP** | Manual fallback documented | **V1.1** | Offline staff cache |

**One-line (voice):** "If it fails, use the terminal like today."

---

### S5 — "Guests will skip without paying."

| Field | Content |
|-------|---------|
| **Heard as** | "Partial pay then run." |
| **Root fear** | Theft |
| **Response** | Remaining balance stays visible. You **can't close** until €0 unless manager force-closes with reason. Same trust model as letting guests go to the bathroom before paying. |
| **Proof** | Payment tab remaining €X; close blocked. |
| **Escalate if** | >2 abandoned sessions/week with balance — review |
| **MVP** | Remaining balance + manager force-close | **V1.1** | Push notify remaining payers |

**One-line (voice):** "Table stays open until the balance is zero."

---

### S6 — "I don't want to learn new software."

| Field | Content |
|-------|---------|
| **Heard as** | "Another login." |
| **Root fear** | Competence anxiety |
| **Response** | Staff app is **one screen per table**: Start → Bill → Open payment → Close. Training mode lets you practice without live money. |
| **Proof** | 45-min training; laminated flow at POS. |
| **Escalate if** | Staff survey <3/5 week 2 — retrain or simplify |
| **MVP** | Training mode | **V1.1** | Simplified server role |

**One-line (voice):** "Four buttons — I'll show you once."

---

## 4. Guest objections

### G1 — "I'm not downloading an app."

| Field | Content |
|-------|---------|
| **Heard as** | "Do I need an account?" |
| **Root fear** | Friction |
| **Response** | No app. No account required. Browser → nickname → claim → iDEAL. |
| **Proof** | Live guest flow on founder phone. |
| **MVP** | Web session | **V1.1** | Optional account after pay |

**One-line (voice):** "No app — pay in your browser with iDEAL."

---

### G2 — "Why can't I see the bill when I sit down?"

| Field | Content |
|-------|---------|
| **Heard as** | "Other places show the check on QR." |
| **Root fear** | Transparency / control |
| **Response** | Your bill opens when the **waiter starts payment** — that protects your table from strangers scanning from outside. Ask your server to open payment when you're ready. |
| **Proof** | Empty scan vs payment scan. |
| **MVP** | Waiter-gated | **Never** | Public live bill |

**One-line (voice):** "The waiter opens the bill when you're ready to pay."

---

### G3 — "This is awkward — I'll just Tikkie later."

| Field | Content |
|-------|---------|
| **Heard as** | "I'll send you €24 after." |
| **Root fear** | Social awkwardness |
| **Response** | Pay your share now in 60 seconds; no chasing friends on WhatsApp. Claim only what you ate — not a guessed split. |
| **Proof** | Claim UI; shared wine example €8 each exact. |
| **MVP** | Item + shared split | **Post-MVP** | Pay request reminder (V1.1) |

**One-line (voice):** "Pay your part now — no Tikkie chase later."

---

### G4 — "I don't trust paying on a random website."

| Field | Content |
|-------|---------|
| **Heard as** | "Is this legit?" |
| **Root fear** | Phishing |
| **Response** | Checkout is **Mollie** — the same payment page used by major Dutch webshops. Restaurant name and amount shown before you approve in your banking app. |
| **Proof** | Mollie hosted checkout URL; SSL; restaurant branding. |
| **Escalate if** | High checkout abandon — branding issue |
| **MVP** | Mollie hosted | **V1.1** | Apple Pay prominence |

**One-line (voice):** "Payment goes through Mollie, like any Dutch webshop."

---

### G5 — "We shared the wine — I don't know the split."

| Field | Content |
|-------|---------|
| **Heard as** | "Split the bottle four ways?" |
| **Root fear** | Math / fairness |
| **Response** | Tap the wine line → **Share 4 ways** → €8.00 each automatically. Change participant count if needed. |
| **Proof** | Shared-item UX on demo bill. |
| **MVP** | Shared N-way | **V1.1** | Even-split suggestion |

**One-line (voice):** "Tap share — it splits the bottle evenly."

---

### G6 — "My iDEAL failed / I closed the bank app."

| Field | Content |
|-------|---------|
| **Heard as** | "It charged me twice?" |
| **Root fear** | Double charge |
| **Response** | Retry the same claim within 15 minutes — no double allocation. If money left your account once, only one payment succeeds; refresh the payment tab. |
| **Proof** | Retry button; webhook reconciliation. |
| **MVP** | 15-min claim lock | **V1.1** | Status polling UX |

**One-line (voice):** "Tap retry — you won't pay twice."

---

### G7 — "I want a receipt for expensing."

| Field | Content |
|-------|---------|
| **Heard as** | "VAT invoice with my company name." |
| **Root fear** | Admin burden |
| **Response** | MVP: email receipt from Mollie after payment. Company VAT invoice still from restaurant — ask your server. Account history for repeats comes in a later update. |
| **Proof** | Mollie receipt email sample. |
| **MVP** | Mollie receipt | **V1.1** | Guest account + history |

**One-line (voice):** "Mollie emails your receipt right after payment."

---

## 5. Objection routing matrix

| Objection theme | Primary owner | Playbook section | Metric to watch |
|-----------------|---------------|------------------|-----------------|
| Payment trust / PSD2 | Owner | O5 | M6 retention |
| Waiter authority | Owner, Staff | O2, S1 | Staff NPS |
| Manual ops burden | Owner, Staff | O4, S2 | M7, M10 |
| Fraud / hijack | Owner | O6 | M9 |
| Guest adoption | Guest | G1, G3 | M1, M5 |
| Split fairness | Staff, Guest | S3, G5 | M4 |
| POS overlap | Owner | O3 | Force-close rate |

---

## 6. "Do not say" list (regulatory / positioning)

| Never say | Say instead |
|-----------|-------------|
| "Scan anytime to see your bill" | "Waiter opens payment when you're ready" |
| "Wallet balance" / "platform credit" | "Optional account for history" (V1.1) |
| "Crypto checkout available" | "iDEAL and cards via Mollie" |
| "We hold tips overnight" | "Tips pass through per venue rules" |
| "Guaranteed belasting-ready receipts" | "VAT shown; fiscal receipt from POS" |
| "Replace your POS" | "Works alongside your POS" |

---

## 7. Escalation ladder

```
Tier 1 — Waiter / host          → Laminated FAQ, shift lead
Tier 2 — Shift lead / manager   → Override tools, pause payment
Tier 3 — Platform ops (founder)   → Incident channel, webhook check
Tier 4 — Legal / counsel        → PSD2, DPA, fraud pattern
```

| Trigger | Tier |
|---------|------|
| Single failed payment | 1 |
| Override dispute | 2 |
| Mollie webhook mismatch | 3 |
| Suspected fraud ring | 3 + 4 |
| Guest GDPR erasure request | 3 + 4 |

---

## 8. MVP vs post-MVP objection coverage

| Objection | Fully answered MVP? | Post-MVP enhancement |
|-----------|---------------------|----------------------|
| POS double entry | Partial — honest manual tax | V1.1 import |
| Fiscal guest invoice | Partial — Mollie receipt only | V2 fiscal integration TBD |
| Bill hijack | Yes — session token | V1.1 geo optional |
| Loyalty / rewards | Defer — "not in pilot" | V2 venue points |
| Crypto pay | Defer — "not offered" | V2 separate rail |
| Multi-language | NL + EN MVP | DE V1.1 tourist corridors |
| Refund complexity | Manager via Mollie dashboard | V1.1 in-app split refund |

---

## Related artifacts

- [gtm-plan.md](./gtm-plan.md) — ICP and acquisition
- [pilot-scorecard.md](./pilot-scorecard.md) — when objections correlate with metric failure
- [elevator-pitch.md](../product/elevator-pitch.md) — one-line handlers
