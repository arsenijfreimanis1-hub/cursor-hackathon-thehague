import type { MoneyCents } from "@rekentafel/shared-types";

export type BillLineInput = {
  lineId: string;
  lineTotalIncVatCents: MoneyCents;
  splittable: boolean;
};

export type AllocationInput = {
  allocationId: string;
  participantId: string;
  amountCents: MoneyCents;
  state: "COMMITTED" | "LOCKED_FOR_CHECKOUT";
};

export type BillSettlementSnapshot = {
  billGrandTotalCents: MoneyCents;
  confirmedPaidCents: MoneyCents;
  allocatedCents: MoneyCents;
  unclaimedCents: MoneyCents;
  remainingCents: MoneyCents;
};

export function sumLineTotals(lines: BillLineInput[]): MoneyCents {
  return lines.reduce((sum, line) => sum + line.lineTotalIncVatCents, 0);
}

export function computeSettlement(
  billGrandTotalCents: MoneyCents,
  confirmedPaidCents: MoneyCents,
  allocations: AllocationInput[],
): BillSettlementSnapshot {
  const allocatedCents = allocations
    .filter((a) => a.state === "COMMITTED" || a.state === "LOCKED_FOR_CHECKOUT")
    .reduce((sum, a) => sum + a.amountCents, 0);

  const remainingCents = Math.max(0, billGrandTotalCents - confirmedPaidCents);
  const unclaimedCents = Math.max(0, billGrandTotalCents - allocatedCents);

  return {
    billGrandTotalCents,
    confirmedPaidCents,
    allocatedCents,
    unclaimedCents,
    remainingCents,
  };
}

export type CombinedCheckoutPledge = {
  participantId: string;
  pledgedCents: MoneyCents;
  tipCents: MoneyCents;
};

export type CombinedCheckoutQuote = {
  /** Sum of all active participant pledges (food share only). */
  pledgedFoodCents: MoneyCents;
  /** Optional tips aggregated for display; combined Mollie payment uses remaining balance. */
  pledgedTipCents: MoneyCents;
  /** Amount due in one Mollie payment to settle remaining bill balance. */
  checkoutTotalCents: MoneyCents;
  /** Participants included in the combined checkout. */
  participantIds: string[];
};

/**
 * Combined checkout: guests claim/split items individually, but settlement uses
 * a single Mollie payment for the table's remaining balance (payment lead model).
 */
export function quoteCombinedCheckout(
  settlement: BillSettlementSnapshot,
  pledges: CombinedCheckoutPledge[],
  options?: { includeUnpledgedRemainder?: boolean },
): CombinedCheckoutQuote {
  const pledgedFoodCents = pledges.reduce((sum, p) => sum + p.pledgedCents, 0);
  const pledgedTipCents = pledges.reduce((sum, p) => sum + p.tipCents, 0);
  const includeRemainder = options?.includeUnpledgedRemainder ?? true;

  const checkoutTotalCents = includeRemainder
    ? settlement.remainingCents + pledgedTipCents
    : pledgedFoodCents + pledgedTipCents;

  return {
    pledgedFoodCents,
    pledgedTipCents,
    checkoutTotalCents,
    participantIds: pledges.map((p) => p.participantId),
  };
}

export function validateAllocationAmount(
  amountCents: MoneyCents,
  unclaimedCents: MoneyCents,
): { ok: true } | { ok: false; reason: string } {
  if (amountCents <= 0) {
    return { ok: false, reason: "Allocation must be positive" };
  }
  if (amountCents > unclaimedCents) {
    return { ok: false, reason: "Allocation exceeds unclaimed balance" };
  }
  return { ok: true };
}
