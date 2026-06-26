# Counsel Question List — Netherlands / EU

**Slice:** Part 12 — Legal / Compliance  
**Audience:** Dutch/EU fintech and privacy counsel  
**Purpose:** Specific questions requiring professional legal opinion before pilot and before each post-MVP expansion  
**Disclaimer:** This list reflects product architecture assumptions in repo docs; answers may change regulatory tiering in [risk-tiering.md](./risk-tiering.md).

**Cross-references (architecture only, not legal conclusions):**

- [payment-architecture.md](../architecture/payments/payment-architecture.md) — Model A vs Model B
- [regulatory-framing.md](../domain/loyalty/regulatory-framing.md) — loyalty / overpay boundaries
- [data-classification.md](../architecture/data-model/data-classification.md) — retention schedule
- [crypto-rail-design.md](../architecture/payments/crypto-rail-design.md) — post-MVP rail

---

## 1. Engagement scope (ask counsel to confirm)

1. **Matter scope:** Does your engagement cover (a) Wft/PSD2 payment services classification, (b) GDPR/AVG compliance, (c) consumer contract law, (d) VAT advisory, or should VAT be referred to a separate fiscal advisor?

2. **Regulator mapping:** For our MVP architecture (platform BV, Dutch pilot venue, Mollie as PSP), which regulators matter at pilot stage: **AFM**, **DNB**, **ACM**, **AP**, **Belastingdienst** (indirectly via merchant)?

3. **Opinion format:** Will you provide a written memo suitable for investor/regulator diligence with explicit **MVP** vs **post-MVP** conclusions?

---

## 2. PSD2 and payment services boundaries

4. **Model A classification:** Under PSD2/Wft as implemented in NL, if our platform (a) is not merchant of record, (b) creates Mollie payments via **restaurant OAuth token** only, (c) never receives guest funds on platform bank account, and (d) charges **monthly SaaS fee by separate invoice**, is the platform **outside** payment institution / money remittance licensing? What factual changes would flip that conclusion?

5. **Payment initiation vs technical service:** Does Mollie Connect for Platforms OAuth (scopes: `payments.write`, `payments.read`) make us a **payment initiation service provider (PISP)** or purely a technical agent of the merchant? What contractual language with restaurants and Mollie supports the intended classification?

6. **Model B marketplace split:** If we later use Mollie `routing[]` to deduct a platform fee per transaction (e.g. guest pays €27.00; €26.19 to restaurant org, €0.81 to platform org), does that structure require **payment institution**, **electronic money institution**, or **marketplace** registration beyond Mollie's licenses?

7. **Tip and service charge routing:** When guest payment amount includes **tip** and/or **service charge** as metadata on a single Mollie Payment to the **restaurant org**, does the platform incur any payment services obligation if we **never touch** those funds?

8. **Partial payments architecture:** Multiple Mollie Payments per table session (application-layer aggregation) — any PSD2 concern vs single aggregated payment? Example: table €86.40 paid as four separate `tr_xxx` objects.

9. **Refund API usage:** When platform UI triggers `POST /v2/payments/{id}/refunds` using **restaurant OAuth token**, are we acting as merchant agent only? Liability for unauthorized refunds?

10. **Passporting:** If platform BV serves EU restaurants outside NL post-pilot, does Model A require **passporting** notifications or establishment per member state?

---

## 3. Stored value, e-money, and loyalty

11. **Overpay rejection validation:** Product explicitly rejects guest "dining wallet" / EUR balance. Confirm that MVP scope (tips only, no surplus ledger) stays **outside** EMI scope under Wft.

12. **Venue-scoped points (V2):** If points are (a) integer-only, (b) non-transferable, (c) no cash-out, (d) redeemable **only at issuing restaurant**, (e) expire in 12 months, (f) marketing states "no monetary value" — are we **outside** e-money? At what point does cross-venue coalition redemption trigger EMI?

13. **Internal planning value:** Restaurant accrues marketing liability using internal €0.01/point **not shown to consumers** — any disclosure or e-money imputation risk?

14. **Same-visit overpay reframe:** Guest adds €5 "support the house" applied as **line discount on same bill before Mollie checkout** (no stored balance). Classify under gift voucher rules vs ordinary discount vs e-money.

15. **Same-venue future discount code:** Single-use code, 90-day expiry, same restaurant only, non-transferable, no cash refund — classify under **single-purpose voucher** rules in NL VAT and consumer law.

16. **Breakage / expiration:** Who must disclose breakage accounting to consumers under NL/EU rules if platform manages expiration of promotional points?

17. **Insolvency:** If restaurant enters insolvency, what happens to outstanding venue points under NL consumer and insolvency law? Required terms language?

---

## 4. Gift vouchers and partner redemption (post-MVP)

18. **Multi-merchant redemption:** Partner marketplace where guest redeems rewards at unaffiliated venues — triggers **multi-purpose voucher** VAT treatment, EMI, or both? Minimum legal structure (separate issuer entity, licensed partner)?

19. **Platform-issued EUR voucher at checkout:** If we ever issue a **€5 discount voucher** email after payment (no wallet UI), is that treated differently from persistent balance?

20. **Third-party brand rewards:** Redemption via external gift cards (e.g. national retail chains) — AML/KYC thresholds for issuance or aggregation?

---

## 5. VAT / BTW — splits, tips, service charge

21. **Display vs invoice:** Platform shows itemized VAT on split shares for guest convenience; **restaurant** issues fiscal receipt. Is platform liable for display errors if terms disclaim fiscal responsibility? Required disclaimer wording under NL law?

22. **Split rounding:** Bill €86.40 incl. VAT; four guests pay €21.60 each. Confirm acceptable rounding methodology so sum of guest VAT lines reconciles to merchant obligation.

23. **Service charge vs fooi (tip):** Under Dutch hospitality practice and tax rules, how must UI distinguish **mandatory service charge** (often VAT-bearing) vs **voluntary tip** (often treated differently)? Can both flow through same Mollie Payment?

24. **Platform SaaS fee VAT:** Confirm BTW treatment on monthly SaaS invoices to restaurants (likely 21% on B2B services) — separate from guest meal VAT.

25. **Single-purpose voucher VAT (if Option B discount codes):** Timing of VAT point for deferred single-venue discount codes.

---

## 6. GDPR / AVG — retention, minimization, profiling

26. **Controller vs processor roles:** For MVP guest payment sessions (nickname, device fingerprint hash, payment amounts), is platform **processor** to restaurant **controller**? When optional guest account launches (V1.1), does platform become **joint controller** for account data?

27. **Retention alignment:** Confirm proposed schedule matches legitimate minimization:
   - `participants.display_name`: 90 days after `table.reset`
   - `guest_devices`: 90 days inactive purge
   - `payments` / closed bills: 7 years pseudonymized where needed
   - `webhook_events.payload_json`: 90 days delete raw payload

28. **Lawful basis for fraud signals:** Is **legitimate interest** (Art. 6(1)(f)) adequate for `guest_devices.fingerprint_hash` and `ip_hash` with 90-day retention? Need LIA (legitimate interest assessment)?

29. **Erasure vs financial retention:** Guest requests Art. 17 erasure after payment. Confirm approach: delete direct identifiers, retain pseudonymous payment records 7 years. Draft response template?

30. **Payment session token (L3):** Store SHA-256 hash only of session token — sufficient security measure for GDPR Art. 32?

31. **Profiling / recommendations (post-MVP):** Order-history-based restaurant discovery — require **explicit consent** only, or legitimate interest ever viable? Is DPIA mandatory before launch?

32. **Cross-venue history (coalition):** Data sharing between restaurants for loyalty — need **joint controller agreement** and separate consent?

33. **Geo/proximity join gate (V1.1):** Collect coarse location to reduce remote session hijacking — lawful basis, precision limits, and whether **consent** required?

34. **Children:** QR menu may be scanned by minors; payment session joins without age verification. Any age-specific privacy obligations beyond standard policy?

35. **DPA chain:** Required clauses for restaurant ↔ platform DPA and platform ↔ Mollie sub-processing. Must restaurants obtain guest consent for platform processing, or is restaurant's hospitality relationship sufficient?

36. **Data breach:** If L3 OAuth token exfiltrated, trigger GDPR Art. 33 notification to AP? Notify restaurants as controllers?

37. **Transfers:** If infrastructure uses US sub-processors (e.g. email, error tracking), confirm SCCs + transfer impact assessment adequacy for payment metadata.

---

## 7. Crypto (explicit post-MVP — MVP excluded)

38. **MVP confirmation:** Confirm zero crypto UI/API at pilot creates **no** MiCA CASP obligation for platform BV.

39. **Post-MVP Option A:** Licensed crypto PSP settles EUR to restaurant IBAN; platform integrates API only — map CASP/AML obligations between PSP and platform.

40. **Stablecoin table pay:** Guest pays USDC via partner; platform never custodies keys — still trigger travel rule or KYC for sub-€100 dine-in payments?

41. **Loyalty on crypto payment:** If V2 points accrue on crypto-settled checks, any compounded EMI/AML concern?

---

## 8. Restaurant commercial terms and consumer refunds

42. **Merchant of record messaging:** Required guest-facing disclosure that **restaurant** is seller of food/drink and payment recipient via Mollie, not platform?

43. **Guest terms counterparty:** For anonymous split-pay (no account), is contract (a) guest–restaurant with platform as processor, or (b) guest–platform for software access? Impact on consumer rights and refund jurisdiction.

44. **Refund responsibility:** Item returned to kitchen after Anna paid €27 for her share — who is legally responsible for partial refund: restaurant only, or platform as payment agent? Draft refund policy allocation.

45. **Chargebacks:** Card chargeback on group bill after table closed — merchant of record dispute obligations; can platform terms limit liability for allocation errors?

46. **Waiter override closing unpaid balance:** Restaurant writes off €14.50 unpaid share to close table — consumer credit or debt collection implications if guest later disputes?

47. **Unfair terms (ACM):** Review guest terms for one-sided limitation of liability, mandatory arbitration, or waiver inconsistent with EU Consumer Rights Directive where applicable.

---

## 9. Partner settlement and marketplace (post-MVP)

48. **Coalition settlement:** Platform collects marketing fees from Partner A when guest redeems points at Partner B — payment services or commercial invoicing only?

49. **Agency vs marketplace:** If platform lists partner offers, are we **commercial agent** or **platform operator** under P2B / Digital Services Act transparency rules?

50. **Insolvency of partner merchant:** Liability for unredeemed third-party rewards.

---

## 10. Employment, tips, and sector rules

51. **Tip pooling metadata:** Platform reports tip amounts to restaurant dashboard only — any platform obligation under Dutch **fooiregel** or collective hospitality agreements if restaurant pools tips?

52. **Platform never pays staff directly:** Confirm this avoids wage tax / employer classification for platform.

---

## 11. Security, fraud, and operational law

53. **Session hijacking:** Join PIN + waiter activation — sufficient **authentication** for SCA purposes under PSD2, or entirely out of scope because Mollie handles SCA at checkout?

54. **Bill hijacking criminal law:** Remote user joins session maliciously — any platform duty to report or prevent under NL fraud statutes beyond reasonable security?

55. **Audit logs 7 years:** Confirm proportionality for non-financial staff actions (waiter override) vs payment audit.

---

## 12. Corporate and pilot structure

56. **Pilot MOU vs full MSA:** Can pilot operate under simplified agreement with explicit MVP feature exclusions (no wallet, no crypto, no loyalty)?

57. **Insurance:** Professional indemnity / cyber insurance expectations for Dutch fintech SaaS with payment orchestration.

58. **Product naming / trademarks:** Any restricted terms ("wallet," "bank," "pay") in AFM communication rules when marketing split-pay?

---

## 13. Question priority matrix

| Priority | Questions | Blocker for |
|----------|-----------|-------------|
| **P0 — before pilot** | 4, 5, 11, 21, 23, 26, 27, 35, 42, 43, 44, 56 | First guest payment |
| **P1 — before V1.1 accounts** | 29, 30, 33, 34, 47 | Guest accounts + geo |
| **P2 — before Model B / bps** | 6, 7, 10 | Marketplace fees |
| **P3 — before V2 loyalty** | 12–17, 31, 32 | Points program |
| **P4 — before crypto eval** | 38–41 | Any crypto UI |
| **P5 — before partner marketplace** | 18–20, 48–50 | Coalition redemption |

---

## 14. Document bundle for counsel review

Provide counsel with:

| Document | Path |
|----------|------|
| Payment architecture | `docs/architecture/payments/payment-architecture.md` |
| Loyalty regulatory framing | `docs/domain/loyalty/regulatory-framing.md` |
| Data classification & retention | `docs/architecture/data-model/data-classification.md` |
| Scope boundary (MVP Never list) | `docs/product/scope-boundary.md` |
| Crypto rail (exclusion) | `docs/architecture/payments/crypto-rail-design.md` |
| Risk tiering | `docs/compliance/risk-tiering.md` |
| Policy outlines | `docs/compliance/policy-drafts-needed.md` |
| Sample bill split numeric example | payment-architecture §2.3 (€86.40 table) |

---

## 15. Expected deliverables from counsel

| Deliverable | Use |
|-------------|-----|
| MVP regulatory classification memo (PSD2/EMI: in/out) | Investor diligence; engineering guardrails |
| GDPR role + retention sign-off | Privacy policy finalization |
| Guest terms + MSA redlines | Pilot signature |
| VAT display disclaimer language | Product copy |
| V2 loyalty gate memo | Feature flag `loyalty.enabled` |
| Crypto go/no-go memo | Permanent or time-boxed exclusion |

---

*Slice ownership: Part 12 — Legal / Compliance. Minimum 58 specific questions for NL/EU counsel.*
