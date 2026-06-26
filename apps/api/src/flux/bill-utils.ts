import { prisma } from "@rekentafel/db";
import { computeSettlement } from "@rekentafel/split-engine";
import type { BillEventBus } from "@rekentafel/realtime";
import { createBillUpdatedEvent } from "@rekentafel/realtime";

export function generateJoinPin(): string {
  return String(Math.floor(100000 + Math.random() * 900000));
}

export async function recalculateBillTotals(billId: string): Promise<void> {
  const lines = await prisma.billLine.findMany({
    where: { billId, voidedAt: null },
  });

  const menuSubtotalCents = lines
    .filter((l) => l.lineKind === "MENU_ITEM" || l.lineKind === "MANUAL_MISC")
    .reduce((sum, l) => sum + l.lineTotalIncVatCents, 0);

  const serviceChargeCents = lines
    .filter((l) => l.lineKind === "SERVICE_CHARGE")
    .reduce((sum, l) => sum + l.lineTotalIncVatCents, 0);

  const discountCents = lines
    .filter((l) => l.lineKind === "DISCOUNT")
    .reduce((sum, l) => sum + l.lineTotalIncVatCents, 0);

  const billGrandTotalCents = menuSubtotalCents + serviceChargeCents - discountCents;

  const allocations = await prisma.allocation.findMany({
    where: { billId, state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } },
  });
  const allocatedCents = allocations.reduce((sum, a) => sum + a.allocatedAmountCents, 0);

  await prisma.bill.update({
    where: { id: billId },
    data: {
      menuSubtotalCents,
      serviceChargeCents,
      discountCents,
      billGrandTotalCents,
      allocatedCents,
      unclaimedCents: Math.max(0, billGrandTotalCents - allocatedCents),
      billVersion: { increment: 1 },
    },
  });
}

export async function ensureAllocatableUnits(billLineId: string, qty: number, unitValueCents: number): Promise<void> {
  const existing = await prisma.allocatableUnit.count({ where: { billLineId } });
  if (existing >= qty) return;

  for (let i = existing; i < qty; i++) {
    await prisma.allocatableUnit.create({
      data: {
        billLineId,
        unitIndex: i,
        unitValueCents,
        maxShares: 1,
      },
    });
  }
}

export async function publishBillUpdate(
  billEvents: BillEventBus,
  paymentSessionId: string,
  billId: string,
): Promise<void> {
  const bill = await prisma.bill.findUniqueOrThrow({
    where: { id: billId },
    include: {
      allocations: { where: { state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } } },
    },
  });

  const settlement = computeSettlement(
    bill.billGrandTotalCents,
    bill.confirmedPaidCents,
    bill.allocations.map((a) => ({
      allocationId: a.id,
      participantId: a.participantId,
      amountCents: a.allocatedAmountCents,
      state: a.state as "COMMITTED" | "LOCKED_FOR_CHECKOUT",
    })),
  );

  billEvents.publish(createBillUpdatedEvent(paymentSessionId, bill.billVersion, settlement));
}

export function formatBillLine(line: {
  id: string;
  name: string;
  qty: { toNumber?: () => number } | number | string;
  unitPriceIncVatCents: number;
  vatRateBps: number;
  lineTotalIncVatCents: number;
  splittable: boolean;
  lineKind: string;
}) {
  const qty = typeof line.qty === "object" && line.qty !== null && "toNumber" in line.qty
    ? (line.qty as { toNumber: () => number }).toNumber()
    : Number(line.qty);

  return {
    line_id: line.id,
    name: line.name,
    qty,
    unit_price_inc_vat_cents: line.unitPriceIncVatCents,
    vat_rate_bps: line.vatRateBps,
    line_total_inc_vat_cents: line.lineTotalIncVatCents,
    splittable: line.splittable,
    line_kind: line.lineKind,
  };
}

export async function getDevStaffId(): Promise<string> {
  const staffId = process.env.DEV_STAFF_ID;
  if (staffId) return staffId;

  const staff = await prisma.staffMember.findFirst({ where: { isActive: true } });
  if (!staff) throw new Error("No staff member found — run db:seed");
  return staff.id;
}
