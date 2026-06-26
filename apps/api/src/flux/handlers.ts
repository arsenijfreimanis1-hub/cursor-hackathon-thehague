import { randomUUID, createHash } from "node:crypto";
import type { MessageBus } from "./bus.js";
import type {
  ActivatePaymentModeCommand,
  AddBillLineCommand,
  AckServiceSignalCommand,
  CallServerCommand,
  CloseDiningSessionCommand,
  CreateClaimCommand,
  GetPaymentSessionQuery,
  GetTableBillQuery,
  InitiateCombinedCheckoutCommand,
  JoinPaymentSessionCommand,
  ListServiceSignalsQuery,
  ListStaffTablesQuery,
  OpenDiningSessionCommand,
  ReconcileMollieWebhookCommand,
  ResolveTableQrQuery,
} from "./messages.js";
import { prisma } from "@rekentafel/db";
import { computeSettlement, validateAllocationAmount } from "@rekentafel/split-engine";
import {
  CombinedCheckoutService,
  MolliePaymentsAdapter,
  reconcileMollieWebhook,
} from "@rekentafel/payments";
import { BillEventBus, createBillUpdatedEvent } from "@rekentafel/realtime";
import {
  ensureAllocatableUnits,
  formatBillLine,
  generateJoinPin,
  getDevStaffId,
  publishBillUpdate,
  recalculateBillTotals,
} from "./bill-utils.js";

const guestWebUrl = process.env.GUEST_WEB_URL ?? "http://localhost:5173";

function buildQrUrl(restaurantSlug: string, tableCode: string): string {
  return `${guestWebUrl}/t/${restaurantSlug}/${tableCode}`;
}

export type HandlerDeps = {
  billEvents: BillEventBus;
  mollie?: MolliePaymentsAdapter;
  combinedCheckout?: CombinedCheckoutService;
};

export function registerHandlers(bus: MessageBus, deps: HandlerDeps): void {
  bus.register<ResolveTableQrQuery, unknown>("query.resolveTableQr", async (msg) => {
    const restaurant = await prisma.restaurant.findFirst({
      where: { slug: msg.restaurantSlug, status: "ACTIVE" },
      include: {
        venues: {
          include: {
            tables: {
              where: { tableCode: msg.tableCode, isActive: true },
              include: {
                qrCode: true,
                currentDiningSession: {
                  include: {
                    paymentSessions: {
                      where: { state: { in: ["OPEN", "PARTIALLY_PAID"] } },
                      take: 1,
                      orderBy: { openedAt: "desc" },
                    },
                  },
                },
              },
            },
          },
        },
      },
    });

    const table = restaurant?.venues.flatMap((v) => v.tables)[0];
    if (!restaurant || !table) return { notFound: true as const };

    const session = table.currentDiningSession;
    const paymentSession = session?.paymentSessions[0];

    return {
      table: {
        table_id: table.id,
        restaurant_id: restaurant.id,
        table_code: table.tableCode,
        session_state: session?.state ?? "EMPTY",
        qr_url: table.qrCode?.qrPayloadUrl ?? buildQrUrl(restaurant.slug, table.tableCode),
      },
      restaurant: {
        restaurant_id: restaurant.id,
        name: restaurant.tradeName,
        slug: restaurant.slug,
      },
      session_state: session?.state ?? "EMPTY",
      payment_session_hint: paymentSession
        ? { payment_session_id: paymentSession.id, join_required: true }
        : null,
      menu: { categories: [] },
    };
  });

  bus.register<ListStaffTablesQuery, unknown>("query.listStaffTables", async (msg) => {
    const tables = await prisma.table.findMany({
      where: { venueId: msg.venueId, isActive: true },
      include: {
        qrCode: true,
        currentDiningSession: {
          include: {
            paymentSessions: {
              where: { state: { in: ["OPEN", "PARTIALLY_PAID", "FULLY_PAID"] } },
              take: 1,
              orderBy: { openedAt: "desc" },
            },
            bills: { take: 1, orderBy: { createdAt: "desc" } },
          },
        },
        venue: { include: { restaurant: true } },
      },
      orderBy: { sortOrder: "asc" },
    });

    return tables.map((table) => {
      const restaurant = table.venue.restaurant;
      const session = table.currentDiningSession;
      const paymentSession = session?.paymentSessions[0];
      return {
        table: {
          table_id: table.id,
          restaurant_id: restaurant.id,
          table_code: table.tableCode,
          session_state: session?.state ?? "EMPTY",
          qr_url: table.qrCode?.qrPayloadUrl ?? buildQrUrl(restaurant.slug, table.tableCode),
        },
        dining_session: session
          ? { dining_session_id: session.id, state: session.state }
          : undefined,
        payment_session_id: paymentSession?.id,
        join_pin: paymentSession?.joinPin,
        bill_total_cents: session?.bills[0]?.billGrandTotalCents ?? 0,
        pending_signals: 0,
      };
    });
  });

  bus.register<OpenDiningSessionCommand, unknown>("command.openDiningSession", async (msg) => {
    const table = await prisma.table.findUnique({
      where: { id: msg.tableId },
      include: { currentDiningSession: true, venue: true },
    });
    if (!table) return { notFound: true as const };
    if (table.currentDiningSession && table.currentDiningSession.state !== "CLOSED") {
      return { error: "SESSION_ALREADY_OPEN" as const, dining_session_id: table.currentDiningSession.id };
    }

    const staffId = await getDevStaffId();
    const restaurant = await prisma.restaurant.findFirst({
      where: { venues: { some: { id: table.venueId } } },
    });
    if (!restaurant) return { notFound: true as const };

    const session = await prisma.diningSession.create({
      data: {
        tableId: table.id,
        venueId: table.venueId,
        restaurantId: restaurant.id,
        state: "SEATED",
        partySize: msg.partySize ?? 2,
        openedByStaffId: staffId,
        openedAt: new Date(),
      },
    });

    await prisma.table.update({
      where: { id: table.id },
      data: { currentDiningSessionId: session.id },
    });

    return { dining_session_id: session.id, state: "SEATED" };
  });

  bus.register<AddBillLineCommand, unknown>("command.addBillLine", async (msg) => {
    const table = await prisma.table.findUnique({
      where: { id: msg.tableId },
      include: {
        currentDiningSession: {
          include: { bills: { take: 1, orderBy: { createdAt: "desc" } } },
        },
        venue: true,
      },
    });
    if (!table?.currentDiningSession) return { error: "NO_ACTIVE_SESSION" as const };

    const restaurant = await prisma.restaurant.findFirst({
      where: { venues: { some: { id: table.venueId } } },
    });
    if (!restaurant) return { notFound: true as const };

    let bill = table.currentDiningSession.bills[0];
    if (!bill) {
      bill = await prisma.bill.create({
        data: {
          diningSessionId: table.currentDiningSession.id,
          restaurantId: restaurant.id,
          settlementState: "BILL_DRAFT",
          billGrandTotalCents: 0,
          menuSubtotalCents: 0,
        },
      });
    }

    const lineTotal = Math.round(msg.qty * msg.unitPriceIncVatCents);
    const line = await prisma.billLine.create({
      data: {
        billId: bill.id,
        lineKind: msg.lineKind ?? "MENU_ITEM",
        name: msg.name,
        qty: msg.qty,
        unitPriceIncVatCents: msg.unitPriceIncVatCents,
        vatRateBps: msg.vatRateBps,
        lineTotalIncVatCents: lineTotal,
        splittable: msg.splittable ?? true,
      },
    });

    if (line.splittable) {
      await ensureAllocatableUnits(line.id, Math.ceil(msg.qty), msg.unitPriceIncVatCents);
    }

    await recalculateBillTotals(bill.id);
    const updated = await prisma.bill.findUniqueOrThrow({ where: { id: bill.id } });

    return {
      line: formatBillLine(line),
      bill: {
        bill_id: updated.id,
        bill_version: updated.billVersion,
        bill_grand_total_cents: updated.billGrandTotalCents,
      },
    };
  });

  bus.register<GetTableBillQuery, unknown>("query.getTableBill", async (msg) => {
    const table = await prisma.table.findUnique({
      where: { id: msg.tableId },
      include: {
        currentDiningSession: {
          include: {
            bills: {
              take: 1,
              orderBy: { createdAt: "desc" },
              include: { lines: { where: { voidedAt: null }, orderBy: { sortOrder: "asc" } } },
            },
            paymentSessions: {
              where: { state: { in: ["OPEN", "PARTIALLY_PAID"] } },
              take: 1,
            },
          },
        },
      },
    });
    if (!table?.currentDiningSession) return { error: "NO_ACTIVE_SESSION" as const };

    const bill = table.currentDiningSession.bills[0];
    const paymentSession = table.currentDiningSession.paymentSessions[0];

    return {
      dining_session_id: table.currentDiningSession.id,
      state: table.currentDiningSession.state,
      payment_session_id: paymentSession?.id,
      join_pin: paymentSession?.joinPin,
      bill: bill
        ? {
            bill_id: bill.id,
            bill_version: bill.billVersion,
            bill_grand_total_cents: bill.billGrandTotalCents,
            confirmed_paid_cents: bill.confirmedPaidCents,
            lines: bill.lines.map(formatBillLine),
          }
        : null,
    };
  });

  bus.register<ActivatePaymentModeCommand, unknown>("command.activatePaymentMode", async (msg) => {
    const table = await prisma.table.findUnique({
      where: { id: msg.tableId },
      include: {
        currentDiningSession: {
          include: { bills: { take: 1, orderBy: { createdAt: "desc" } } },
        },
      },
    });
    if (!table?.currentDiningSession) return { error: "NO_ACTIVE_SESSION" as const };

    const bill = table.currentDiningSession.bills[0];
    if (!bill || bill.billGrandTotalCents <= 0) {
      return { error: "BILL_EMPTY" as const };
    }

    const staffId = await getDevStaffId();
    const joinPin = generateJoinPin();
    const tokenRaw = randomUUID();
    const tokenHash = createHash("sha256").update(tokenRaw).digest("hex");

    const paymentSession = await prisma.paymentSession.create({
      data: {
        diningSessionId: table.currentDiningSession.id,
        billId: bill.id,
        state: "OPEN",
        joinPin,
        openedByStaffId: staffId,
        openedAt: new Date(),
        tokens: {
          create: {
            tokenHash,
            state: "ISSUED",
            issuedAt: new Date(),
            expiresAt: new Date(Date.now() + 4 * 60 * 60 * 1000),
          },
        },
      },
    });

    await prisma.diningSession.update({
      where: { id: table.currentDiningSession.id },
      data: {
        state: "PAYMENT_ACTIVE",
        activePaymentSessionId: paymentSession.id,
      },
    });

    await prisma.bill.update({
      where: { id: bill.id },
      data: { settlementState: "ALLOCATION_OPEN" },
    });

    return {
      payment_session_id: paymentSession.id,
      join_pin: joinPin,
      join_token: tokenRaw,
      guest_url: `${guestWebUrl}/session/${paymentSession.id}/join`,
    };
  });

  bus.register<JoinPaymentSessionCommand, unknown>("command.joinPaymentSession", async (msg) => {
    let paymentSession = msg.paymentSessionId
      ? await prisma.paymentSession.findUnique({ where: { id: msg.paymentSessionId } })
      : null;

    if (!paymentSession && msg.joinPin) {
      paymentSession = await prisma.paymentSession.findFirst({
        where: { joinPin: msg.joinPin, state: { in: ["OPEN", "PARTIALLY_PAID"] } },
      });
    }

    if (!paymentSession && msg.joinToken) {
      const tokenHash = createHash("sha256").update(msg.joinToken).digest("hex");
      const token = await prisma.paymentSessionToken.findFirst({
        where: { tokenHash, state: "ISSUED", expiresAt: { gt: new Date() } },
      });
      if (token) {
        paymentSession = await prisma.paymentSession.findUnique({
          where: { id: token.paymentSessionId },
        });
      }
    }

    if (!paymentSession) return { error: "INVALID_JOIN" as const };

    const guestDevice = await prisma.guestDevice.create({ data: {} });

    const participant = await prisma.participant.create({
      data: {
        paymentSessionId: paymentSession.id,
        guestDeviceId: guestDevice.id,
        displayName: msg.displayName,
        state: "JOINED",
        joinedAt: new Date(),
      },
    });

    deps.billEvents.publish({
      type: "participant.joined",
      paymentSessionId: paymentSession.id,
      billVersion: 0,
      emittedAt: new Date().toISOString(),
      payload: { participant_id: participant.id, display_name: msg.displayName },
    });

    return {
      participant_id: participant.id,
      payment_session_id: paymentSession.id,
      display_name: msg.displayName,
    };
  });

  bus.register<GetPaymentSessionQuery, unknown>("query.getPaymentSession", async (msg) => {
    const session = await prisma.paymentSession.findUnique({
      where: { id: msg.paymentSessionId },
      include: {
        bill: {
          include: {
            lines: { where: { voidedAt: null }, orderBy: { sortOrder: "asc" } },
            allocations: {
              where: { state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } },
              include: { participant: true, allocatableUnit: { include: { billLine: true } } },
            },
          },
        },
        participants: { where: { state: { not: "RELEASED" } } },
      },
    });
    if (!session?.bill) return { notFound: true as const };

    const settlement = computeSettlement(
      session.bill.billGrandTotalCents,
      session.bill.confirmedPaidCents,
      session.bill.allocations.map((a) => ({
        allocationId: a.id,
        participantId: a.participantId,
        amountCents: a.allocatedAmountCents,
        state: a.state as "COMMITTED" | "LOCKED_FOR_CHECKOUT",
      })),
    );

    return {
      payment_session_id: session.id,
      state: session.state,
      join_pin: session.joinPin,
      bill_version: session.bill.billVersion,
      bill: {
        bill_id: session.bill.id,
        bill_grand_total_cents: session.bill.billGrandTotalCents,
        confirmed_paid_cents: session.bill.confirmedPaidCents,
        lines: session.bill.lines.map(formatBillLine),
      },
      settlement,
      participants: session.participants.map((p) => ({
        participant_id: p.id,
        display_name: p.displayName,
        state: p.state,
      })),
      allocations: session.bill.allocations.map((a) => ({
        allocation_id: a.id,
        participant_id: a.participantId,
        participant_name: a.participant.displayName,
        bill_line_id: a.allocatableUnit.billLineId,
        line_name: a.allocatableUnit.billLine.name,
        amount_cents: a.allocatedAmountCents,
        split_mode: a.splitMode,
        state: a.state,
      })),
    };
  });

  bus.register<CreateClaimCommand, unknown>("command.createClaim", async (msg) => {
    const session = await prisma.paymentSession.findUnique({
      where: { id: msg.paymentSessionId },
      include: {
        bill: {
          include: {
            lines: { where: { voidedAt: null } },
            allocations: { where: { state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } } },
          },
        },
      },
    });
    if (!session?.bill) return { notFound: true as const };
    if (session.claimsFrozen) return { error: "CLAIMS_FROZEN" as const };
    if (session.bill.billVersion !== msg.billVersion) {
      return { error: "VERSION_CONFLICT" as const, bill_version: session.bill.billVersion };
    }

    const line = session.bill.lines.find((l) => l.id === msg.billLineId);
    if (!line) return { error: "LINE_NOT_FOUND" as const };

    const unit = await prisma.allocatableUnit.findFirst({
      where: { billLineId: msg.billLineId },
      include: { allocations: { where: { state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } } } },
    });
    if (!unit) return { error: "NOT_SPLITTABLE" as const };

    const alreadyClaimed = unit.allocations.reduce((s, a) => s + a.allocatedAmountCents, 0);
    const available = unit.unitValueCents - alreadyClaimed;
    if (available <= 0) return { error: "ALREADY_CLAIMED" as const };

    const settlement = computeSettlement(
      session.bill.billGrandTotalCents,
      session.bill.confirmedPaidCents,
      session.bill.allocations.map((a) => ({
        allocationId: a.id,
        participantId: a.participantId,
        amountCents: a.allocatedAmountCents,
        state: a.state as "COMMITTED" | "LOCKED_FOR_CHECKOUT",
      })),
    );

    const amountCents = msg.splitMode === "SHARED"
      ? Math.round(available * (msg.shareNumerator ?? 1) / (msg.shareDenominator ?? 1))
      : available;

    const validation = validateAllocationAmount(amountCents, settlement.unclaimedCents);
    if (!validation.ok) return { error: validation.reason };

    const allocation = await prisma.allocation.create({
      data: {
        billId: session.bill.id,
        billVersion: session.bill.billVersion,
        allocatableUnitId: unit.id,
        participantId: msg.participantId,
        splitMode: msg.splitMode,
        shareNumerator: msg.shareNumerator ?? 1,
        shareDenominator: msg.shareDenominator ?? 1,
        allocatedAmountCents: amountCents,
        state: "COMMITTED",
        committedAt: new Date(),
      },
    });

    await recalculateBillTotals(session.bill.id);
    await publishBillUpdate(deps.billEvents, msg.paymentSessionId, session.bill.id);

    return {
      allocation_id: allocation.id,
      amount_cents: amountCents,
      bill_version: session.bill.billVersion + 1,
    };
  });

  bus.register<CallServerCommand, unknown>("command.callServer", async (msg) => {
    const device = msg.guestDeviceId
      ? await prisma.guestDevice.findUnique({ where: { id: msg.guestDeviceId } })
      : await prisma.guestDevice.create({ data: {} });

    if (!device) return { notFound: true as const };

    const signal = await prisma.serviceSignal.create({
      data: {
        tableId: msg.tableId,
        guestDeviceId: device.id,
        signalType: msg.signalType,
        status: "OPEN",
      },
    });

    return { signal_id: signal.id, status: "OPEN" };
  });

  bus.register<ListServiceSignalsQuery, unknown>("query.listServiceSignals", async (msg) => {
    const signals = await prisma.serviceSignal.findMany({
      where: { status: "OPEN", table: { venueId: msg.venueId } },
      include: { table: true },
      orderBy: { createdAt: "desc" },
    });

    return signals.map((s) => ({
      signal_id: s.id,
      table_id: s.tableId,
      table_code: s.table.tableCode,
      signal_type: s.signalType,
      created_at: s.createdAt.toISOString(),
    }));
  });

  bus.register<AckServiceSignalCommand, unknown>("command.ackServiceSignal", async (msg) => {
    const staffId = await getDevStaffId();
    await prisma.serviceSignal.update({
      where: { id: msg.signalId },
      data: { status: "ACKNOWLEDGED", acknowledgedByStaffId: staffId },
    });
    return { acknowledged: true };
  });

  bus.register<CloseDiningSessionCommand, unknown>("command.closeDiningSession", async (msg) => {
    const staffId = await getDevStaffId();
    await prisma.diningSession.update({
      where: { id: msg.diningSessionId },
      data: {
        state: "CLOSED",
        closedAt: new Date(),
        closedByStaffId: staffId,
        closeReason: "NORMAL",
      },
    });
    await prisma.table.update({
      where: { id: msg.tableId },
      data: { currentDiningSessionId: null },
    });
    return { closed: true };
  });

  bus.register<InitiateCombinedCheckoutCommand, unknown>(
    "command.initiateCombinedCheckout",
    async (msg) => {
      if (!deps.combinedCheckout) return { error: "MOLLIE_NOT_CONFIGURED" as const };

      const paymentSession = await prisma.paymentSession.findUnique({
        where: { id: msg.paymentSessionId },
        include: {
          bill: {
            include: {
              allocations: { where: { state: { in: ["COMMITTED", "LOCKED_FOR_CHECKOUT"] } } },
            },
          },
          participants: { where: { state: { not: "RELEASED" } } },
        },
      });

      if (!paymentSession?.bill) return { notFound: true as const };

      const bill = paymentSession.bill;
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

      const pledges = paymentSession.participants.map((p) => ({
        participantId: p.id,
        pledgedCents: bill.allocations
          .filter((a) => a.participantId === p.id)
          .reduce((sum, a) => sum + a.allocatedAmountCents, 0),
        tipCents: 0,
      }));

      const checkoutIntentId = randomUUID();
      const result = await deps.combinedCheckout.initiate({
        paymentSessionId: msg.paymentSessionId,
        checkoutIntentId,
        paymentLeadParticipantId: msg.participantId,
        settlement,
        pledges,
        redirectUrl: msg.redirectUrl,
        tipCents: msg.tipCents,
      });

      const idempotencyKey = `combined-${checkoutIntentId}`;

      await prisma.checkoutIntent.create({
        data: {
          id: checkoutIntentId,
          paymentSessionId: msg.paymentSessionId,
          participantId: msg.participantId,
          billId: bill.id,
          billVersion: bill.billVersion,
          subtotalCents: settlement.remainingCents,
          tipCents: msg.tipCents ?? 0,
          checkoutTotalCents: result.totalCents,
          allocationSnapshotJson: pledges,
          idempotencyKey,
          state: "ACTIVE",
          expiresAt: result.expiresAt,
        },
      });

      await prisma.paymentIntent.create({
        data: {
          checkoutIntentId,
          paymentSessionId: msg.paymentSessionId,
          participantId: msg.participantId,
          restaurantId: bill.restaurantId,
          molliePaymentId: result.molliePaymentId,
          status: "MOLLIE_OPEN",
          mollieCheckoutUrl: result.checkoutUrl,
          amountCents: result.totalCents,
          currency: bill.currency,
          idempotencyKey: `pi-${idempotencyKey}`,
          billVersion: bill.billVersion,
          expiresAt: result.expiresAt,
          metadataJson: { checkout_mode: "COMBINED" },
        },
      });

      deps.billEvents.publish(
        createBillUpdatedEvent(msg.paymentSessionId, bill.billVersion, settlement),
      );

      return {
        checkout_id: checkoutIntentId,
        mollie_payment_id: result.molliePaymentId,
        mollie_checkout_url: result.checkoutUrl,
        total_cents: result.totalCents,
        expires_at: result.expiresAt.toISOString(),
        checkout_mode: "COMBINED" as const,
      };
    },
  );

  bus.register<ReconcileMollieWebhookCommand, unknown>(
    "command.reconcileMollieWebhook",
    async (msg) => {
      if (!deps.mollie) return { error: "MOLLIE_NOT_CONFIGURED" as const };

      const paymentIntent = await prisma.paymentIntent.findFirst({
        where: { molliePaymentId: msg.molliePaymentId },
        include: { paymentSession: { include: { bill: true } } },
      });

      if (paymentIntent?.status === "PAID") {
        return { reconciled: { status: "paid" as const }, duplicate: true };
      }

      const reconciled = await reconcileMollieWebhook(deps.mollie, {
        id: msg.molliePaymentId,
      });

      if (!paymentIntent?.paymentSession.bill) return { ignored: true as const };

      if (reconciled.status === "paid") {
        const bill = paymentIntent.paymentSession.bill;
        const newPaid = bill.confirmedPaidCents + reconciled.amountCents;
        await prisma.bill.update({
          where: { id: bill.id },
          data: {
            confirmedPaidCents: newPaid,
            settlementState: newPaid >= bill.billGrandTotalCents ? "FULLY_PAID" : "PARTIALLY_PAID",
          },
        });
        await prisma.paymentIntent.update({
          where: { id: paymentIntent.id },
          data: { status: "PAID" },
        });
        await prisma.paymentSession.update({
          where: { id: paymentIntent.paymentSessionId },
          data: {
            state: newPaid >= bill.billGrandTotalCents ? "FULLY_PAID" : "PARTIALLY_PAID",
          },
        });

        const settlement = computeSettlement(bill.billGrandTotalCents, newPaid, []);
        deps.billEvents.publish(
          createBillUpdatedEvent(paymentIntent.paymentSessionId, bill.billVersion, settlement),
        );
      }

      return { reconciled };
    },
  );
}
