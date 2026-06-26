# Bill-Splitting Worked Examples

**Slice:** Part 5 — Bill-Splitting Logic  
**Currency:** EUR, all amounts in cents unless noted  
**Rules reference:** [rules-spec.md](./rules-spec.md)

All examples assume:
- `TableSessionState = PAYMENT_ACTIVE`
- Valid `PaymentSessionToken`
- Service charge **10%** on menu subtotal (inc VAT), VAT **9%** on service charge
- Rounding: half-up to cent; largest-remainder for equal splits

---

## Example 1 — Four guests, mixed ITEM + SHARED + EQUAL (pilot scenario)

**Table 12 · 4 guests (Anna, Bram, Caro, Daan)**

### Bill lines (at payment activation)

| Line ID | Item | Qty | Unit inc VAT | VAT | Line total |
|---------|------|-----|--------------|-----|------------|
| L1 | Burger | 2 | €14.50 | 9% | €29.00 (2900¢) |
| L2 | Steak | 1 | €28.00 | 9% | €28.00 (2800¢) |
| L3 | House wine (splittable) | 1 | €32.00 | 21% | €32.00 (3200¢) |
| L4 | Cola | 2 | €3.50 | 9% | €7.00 (700¢) |
| — | **Menu subtotal** | | | | **€96.00 (9600¢)** |
| L5 | Service charge 10% | 1 | €9.60 | 9% | €9.60 (960¢) |
| — | **Grand total** | | | | **€105.60 (10560¢)** |

### Step 1 — ITEM claims

| Guest | Claim | Line share (inc VAT) |
|-------|-------|----------------------|
| Anna | 1× Burger (L1 unit 0) | 1450¢ |
| Anna | 1× Cola (L4 unit 0) | 350¢ |
| Bram | 1× Steak (L2) | 2800¢ |
| Caro | 1× Cola (L4 unit 1) | 350¢ |

**Menu claimed so far:** Anna 1800¢, Bram 2800¢, Caro 350¢.

**Unclaimed:** 1× Burger (1450¢), full wine (3200¢) → **4650¢ menu**.

### Step 2 — SHARED claim (wine)

Bram, Caro, Daan share wine 3-way (each 1/3):

| Guest | Wine share | Cents (3200÷3) |
|-------|------------|----------------|
| Bram | 33.33% | 1067¢ (1066.67→ rank +1) |
| Caro | 33.33% | 1067¢ |
| Daan | 33.33% | 1066¢ |

Remainder: 3200 - (1067+1067+1066) = 0 ✓

**Updated menu claimed:** Anna 1800, Bram 3867, Caro 1417, Daan 1066.

**Still unclaimed:** 1× Burger **1450¢**.

### Step 3 — EQUAL split on remainder

Anna and Daan equal-split the unclaimed burger (2-way):

| Guest | Burger half | Cents |
|-------|-------------|-------|
| Anna | 50% | 725¢ |
| Daan | 50% | 725¢ |

**Final menu subtotals (inc VAT):**

| Guest | Menu subtotal |
|-------|---------------|
| Anna | 1800 + 725 = **2525¢** |
| Bram | 2800 + 1067 = **3867¢** |
| Caro | 350 + 1067 = **1417¢** |
| Daan | 1066 + 725 = **1791¢** |
| **Sum** | **9600¢** ✓ |

### Step 4 — Service charge pro-rata

Service charge pool: **960¢** (pro-rata over menu 9600¢).

Formula: `sc_guest = round(960 × menu_guest / 9600)`

| Guest | Calculation | SC share |
|-------|-------------|----------|
| Anna | 960 × 2525 / 9600 | 253¢ |
| Bram | 960 × 3867 / 9600 | 387¢ |
| Caro | 960 × 1417 / 9600 | 142¢ |
| Daan | 960 × 1791 / 9600 | 179¢ |
| **Sum** | | **961¢** → adjust −1¢ from Bram → **960¢** ✓ |

(Largest remainder: Bram loses 1¢ adjustment per §4.5.)

### Step 5 — Tips and checkout

| Guest | Subtotal (menu+SC) | Tip | Mollie checkout |
|-------|-------------------|-----|-----------------|
| Anna | 2525+253 = 2778¢ | 200¢ | **2978¢ (€29.78)** |
| Bram | 3867+386 = 4253¢ | 500¢ | **4753¢ (€47.53)** |
| Caro | 1417+142 = 1559¢ | 0 | **1559¢ (€15.59)** |
| Daan | 1791+179 = 1970¢ | 150¢ | **2120¢ (€21.20)** |

**Total collected:** 2978 + 4753 + 1559 + 2120 = **11410¢**

**Bill + tips:** 10560 + 850 = **11410¢** ✓  
**Remaining balance after all webhooks:** **0¢** → `FULLY_PAID`.

### VAT breakdown (Anna, illustrative)

| Component | Ex VAT | VAT | Inc VAT |
|-----------|--------|-----|---------|
| Burger 50% + cola | 2303¢ | 207¢ (9%) | 2510¢ (approx) |
| SC share | 232¢ | 21¢ (9%) | 253¢ |

*(Engine stores per-line VAT; guest receipt aggregates by rate.)*

---

## Example 2 — Equal split with tip (2 of 4 payers)

**Table 7 · 4 joined guests · Bill grand total €84.00 (8400¢)**  
Menu + SC already merged for simplicity: **single pool 8400¢**.

Only **Eva** and **Finn** agree to equal-split the **entire** bill (other two will not pay digitally — waiter will force-close remainder).

### Equal split (2-way)

| Guest | Share | Cents |
|-------|-------|-------|
| Eva | 50% | 4200¢ |
| Finn | 50% | 4200¢ |

### Tips

| Guest | Tip (10% of share) | Checkout |
|-------|-------------------|----------|
| Eva | 420¢ | **4620¢ (€46.20)** |
| Finn | 420¢ | **4620¢ (€46.20)** |

**Digital collected:** 9240¢ (bill 8400 + tips 840).

**Remaining bill balance:** 8400 − 8400 = **0¢** (both covered full bill digitally).

**Waiter action:** Guests G & H did not pay — but bill is fully paid by Eva/Finn over-covering? **Validation blocks this** in MVP: equal split on full bill with only 2 payers assigns 4200¢ each (4200×2=8400), not overpay. G & H remain joined but with **0 allocation**; Eva/Finn each owe 4200¢ + tip.

**Correct interpretation:** Eva and Finn split **half the table each** — they pay 4200¢ each; G/H owe nothing if Eva/Finn voluntarily cover. System records:

| Guest | Allocated | Paid |
|-------|-----------|------|
| Eva | 4200¢ | 4620¢ |
| Finn | 4200¢ | 4620¢ |
| G | 0 | 0 |
| H | 0 | 0 |

**Remaining:** 0¢. Tips pass through Mollie. **No wallet credit** for any over-tip.

### Alternate: equal split **remaining** after partial ITEM claims

Same table; Eva claimed items totaling **2400¢** first.

**Remaining pool:** 8400 − 2400 = **6000¢**  
Eva + Finn equal-split **6000¢** (2-way):

| Guest | Prior ITEM | Equal share | Total owed |
|-------|------------|-------------|------------|
| Eva | 2400¢ | 3000¢ | **5400¢** + tip |
| Finn | 0 | 3000¢ | **3000¢** + tip |

Unclaimed: 0. G/H: 0 unless they claim separately.

---

## Example 3 — Shared bottle split (5-way) + ITEM + unclaimed handling

**Table 3 · 5 guests · Wine €45.00 (4500¢, 21% VAT) + 5× Pasta @ €16.80 (8400¢, 9%)**

| Line | Total |
|------|-------|
| 5× Pasta | 8400¢ |
| 1× Wine (splittable) | 4500¢ |
| Menu subtotal | 12900¢ |
| SC 10% | 1290¢ |
| **Grand total** | **14190¢** |

### ITEM: each guest claims own pasta

| Guest | Pasta |
|-------|-------|
| P1–P5 | 1680¢ each → sum 8400¢ |

### SHARED: wine 5-way

4500 ÷ 5 = **900¢ each**.

| Guest | Pasta | Wine | Menu subtotal |
|-------|-------|------|---------------|
| P1 | 1680 | 900 | 2580 |
| P2 | 1680 | 900 | 2580 |
| P3 | 1680 | 900 | 2580 |
| P4 | 1680 | 900 | 2580 |
| P5 | 1680 | 900 | 2580 |

All menu claimed: **12900¢** ✓

### Service charge pro-rata (equal menu → equal SC)

1290 ÷ 5 = **258¢ each**.

| Guest | Subtotal | Tip 15% | Checkout |
|-------|----------|---------|----------|
| P1 | 2580+258=2838 | 426 | **3264¢** |
| P2 | 2838 | 426 | **3264¢** |
| P3 | 2838 | 0 | **2838¢** |
| P4 | 2838 | 300 | **3138¢** |
| P5 | 2838 | 200 | **3038¢** |

**Bill subtotal collected:** 5×2838 = 14190¢ ✓  
**Tips:** 426+426+0+300+200 = 1352¢  
**Mollie total:** 15542¢

### Unclaimed scenario variant

If **P5 never pays** (payment failed):

| Status | Cents |
|--------|-------|
| Confirmed paid (P1–P4) | 3264+3264+2838+3138 = **12504¢** (incl. their tips) |
| Bill portion paid | 2838×4 = **11352¢** |
| **Remaining bill** | 14190 − 11352 = **2838¢** (P5's share) |

Waiter options:
1. `MARK_CASH_PAID` P5 2838¢ + tip
2. `FORCE_EQUAL_REMAINING` among P1–P4 (not applicable — single debtor)
3. `REASSIGN_UNIT` — N/A (already allocated)
4. `FORCE_CLOSE_CASH` 2838¢

**State:** `PARTIALLY_PAID` until resolved → `FULLY_PAID` → `CLOSED`.

---

## Example 4 — CUSTOM pledge + ITEM (MVP edge)

**Grand total 5000¢.** Guest X: ITEM claims 3000¢. Guest Y: CUSTOM pledge **2000¢** (no itemization).

| Guest | Amount |
|-------|--------|
| X | 3000 + SC share + tip |
| Y | 2000 (pledge) + tip |

Sum allocations = 5000¢ → **no unclaimed pool**.

If Y pledges **1500¢** only:

| Pool | Cents |
|------|-------|
| Unclaimed | 500¢ |

Waiter must assign 500¢ before close (equal, assign to X, or cash).

---

## Example 5 — Concurrent claim conflict (numeric outcome)

**Unclaimed:** 1 beer 500¢. Guest M and Guest N both tap claim within 50ms.

| Order | Result |
|-------|--------|
| M commit `t=100` (wins lock) | Allocated 500¢ |
| N commit `t=101` | **409 UNIT_UNAVAILABLE** |

N sees: "Claimed by M." No partial state.

---

## Verification checklist (acceptance)

| Scenario | Grand total match | Remaining → 0 | SC sum | VAT auditable |
|----------|-------------------|---------------|--------|---------------|
| Ex 1 mixed | ✓ 10560¢ | ✓ | ✓ 960¢ | ✓ |
| Ex 2 equal + tip | ✓ 8400¢ | ✓ | ✓ | ✓ |
| Ex 3 shared 5-way | ✓ 14190¢ | ✓ (variant partial) | ✓ 1290¢ | ✓ |
| Ex 4 custom | ✓ 5000¢ | conditional | ✓ | ✓ |
| Ex 5 race | — | — | — | — |

---

*Slice ownership: Part 5 — Bill-Splitting Logic.*
