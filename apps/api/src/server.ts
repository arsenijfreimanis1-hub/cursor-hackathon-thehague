import "./env.js";
import Fastify from "fastify";
import cors from "@fastify/cors";
import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createMessageBus } from "./flux/bus.js";
import { registerHandlers } from "./flux/handlers.js";
import { BillEventBus, formatSseMessage } from "@rekentafel/realtime";
import {
  CombinedCheckoutService,
  MolliePaymentsAdapter,
  parseMollieWebhookBody,
} from "@rekentafel/payments";

const PORT = Number(process.env.API_PORT ?? 3000);
const billEvents = new BillEventBus();
const QR_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../../../data/qr-codes");
const QR_FILES = new Set(["T01.png", "T02.png", "T03.png", "T04.png", "rekentafel-qr-sheet.pdf"]);

const mollieApiKey = process.env.MOLLIE_API_KEY;
const mollie =
  mollieApiKey
    ? new MolliePaymentsAdapter({
        apiKey: mollieApiKey,
        webhookUrl: process.env.MOLLIE_WEBHOOK_URL ?? `http://localhost:${PORT}/v1/webhooks/mollie`,
      })
    : undefined;

const combinedCheckout = mollie ? new CombinedCheckoutService(mollie) : undefined;

const bus = createMessageBus();
registerHandlers(bus, { billEvents, mollie, combinedCheckout });

const app = Fastify({ logger: true });
await app.register(cors, { origin: true });

function ctx() {
  return { requestId: randomUUID() };
}

function participantId(request: { headers: Record<string, string | string[] | undefined> }): string | null {
  const id = request.headers["x-participant-id"];
  return typeof id === "string" ? id : null;
}

function requireStaff(request: { headers: Record<string, string | string[] | undefined> }) {
  const auth = request.headers.authorization;
  if (typeof auth !== "string" || !auth.startsWith("Bearer ")) return false;
  return true;
}

app.get("/v1/health", async () => ({ status: "ok" }));

// --- Guest: table QR landing ---
app.get<{
  Params: { restaurant_slug: string; table_code: string };
}>("/v1/t/:restaurant_slug/:table_code", async (request, reply) => {
  const result = await bus.dispatch(
    {
      type: "query.resolveTableQr",
      restaurantSlug: request.params.restaurant_slug,
      tableCode: request.params.table_code,
    },
    ctx(),
  );
  if (result && typeof result === "object" && "notFound" in result) {
    return reply.status(404).send({ title: "Table not found", status: 404 });
  }
  return result;
});

// --- Guest: join payment session ---
app.post<{
  Body: {
    payment_session_id?: string;
    join_token?: string;
    join_pin?: string;
    display_name: string;
  };
}>("/v1/payment-sessions/join", async (request, reply) => {
  const result = await bus.dispatch(
    {
      type: "command.joinPaymentSession",
      paymentSessionId: request.body.payment_session_id,
      joinToken: request.body.join_token,
      joinPin: request.body.join_pin,
      displayName: request.body.display_name,
    },
    ctx(),
  );
  if (result && typeof result === "object" && "error" in result) {
    return reply.status(401).send({ title: "Invalid join credentials", status: 401 });
  }
  return result;
});

// --- Guest: get payment session ---
app.get<{ Params: { payment_session_id: string } }>(
  "/v1/payment-sessions/:payment_session_id",
  async (request, reply) => {
    const result = await bus.dispatch(
      {
        type: "query.getPaymentSession",
        paymentSessionId: request.params.payment_session_id,
        participantId: participantId(request) ?? undefined,
      },
      ctx(),
    );
    if (result && typeof result === "object" && "notFound" in result) {
      return reply.status(404).send({ title: "Not found", status: 404 });
    }
    return result;
  },
);

// --- Guest: SSE events ---
app.get<{ Params: { payment_session_id: string } }>(
  "/v1/payment-sessions/:payment_session_id/events",
  async (request, reply) => {
    const { payment_session_id } = request.params;
    reply.raw.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });

    const unsubscribe = billEvents.subscribe(payment_session_id, (event) => {
      reply.raw.write(formatSseMessage(event));
    });

    request.raw.on("close", () => unsubscribe());
  },
);

// --- Guest: create claim ---
app.post<{
  Params: { payment_session_id: string };
  Body: {
    bill_line_id: string;
    split_mode?: "ITEM" | "SHARED";
    share_numerator?: number;
    share_denominator?: number;
  };
}>("/v1/payment-sessions/:payment_session_id/claims", async (request, reply) => {
  const pid = participantId(request);
  if (!pid) return reply.status(401).send({ title: "Participant auth required", status: 401 });

  const billVersion = Number(request.headers["if-match-bill-version"] ?? 0);

  const result = await bus.dispatch(
    {
      type: "command.createClaim",
      paymentSessionId: request.params.payment_session_id,
      participantId: pid,
      billLineId: request.body.bill_line_id,
      splitMode: request.body.split_mode ?? "ITEM",
      shareNumerator: request.body.share_numerator,
      shareDenominator: request.body.share_denominator,
      billVersion,
    },
    ctx(),
  );

  if (result && typeof result === "object" && "error" in result) {
    if (result.error === "VERSION_CONFLICT") {
      return reply.status(409).send({ title: "Bill version conflict", status: 409, ...result });
    }
    return reply.status(422).send({ title: String(result.error), status: 422 });
  }
  return reply.status(201).send(result);
});

// --- Guest: combined checkout ---
app.post<{
  Params: { payment_session_id: string };
  Body: { tip_cents?: number; redirect_url?: string; checkout_mode?: string };
}>("/v1/payment-sessions/:payment_session_id/checkout", async (request, reply) => {
  const pid = participantId(request);
  if (!pid) return reply.status(401).send({ title: "Participant auth required", status: 401 });

  const mode = request.body?.checkout_mode ?? "COMBINED";
  if (mode !== "COMBINED") {
    return reply.status(501).send({ title: "Individual checkout not in MVP", status: 501 });
  }

  const redirectUrl =
    request.body?.redirect_url ??
    `${process.env.GUEST_WEB_URL ?? "http://localhost:5173"}/checkout/return`;

  const result = await bus.dispatch(
    {
      type: "command.initiateCombinedCheckout",
      paymentSessionId: request.params.payment_session_id,
      participantId: pid,
      tipCents: request.body?.tip_cents,
      redirectUrl,
    },
    ctx(),
  );

  if (result && typeof result === "object" && "notFound" in result) {
    return reply.status(404).send({ title: "Payment session not found", status: 404 });
  }
  if (result && typeof result === "object" && "error" in result) {
    return reply.status(503).send({ title: "Mollie not configured", status: 503 });
  }
  return reply.status(201).send(result);
});

// --- Guest: call server ---
app.post<{
  Params: { table_id: string };
  Body: { signal_type?: string; guest_device_id?: string };
}>("/v1/tables/:table_id/service-signals", async (request, reply) => {
  const result = await bus.dispatch(
    {
      type: "command.callServer",
      tableId: request.params.table_id,
      guestDeviceId: request.body.guest_device_id,
      signalType: (request.body.signal_type as "ASSISTANCE" | "READY_TO_ORDER") ?? "ASSISTANCE",
    },
    ctx(),
  );
  return reply.status(201).send(result);
});

// --- Staff: floor (live snapshot) ---
app.get("/v1/staff/floor", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  const venueId = process.env.DEV_VENUE_ID;
  if (!venueId) return reply.status(503).send({ title: "DEV_VENUE_ID not configured", status: 503 });
  return bus.dispatch({ type: "query.listStaffFloor", venueId }, ctx());
});

app.get("/v1/staff/floor/stream", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  const venueId = process.env.DEV_VENUE_ID;
  if (!venueId) return reply.status(503).send({ title: "DEV_VENUE_ID not configured", status: 503 });

  reply.raw.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });

  const sendSnapshot = async () => {
    const floor = await bus.dispatch({ type: "query.listStaffFloor", venueId }, ctx());
    reply.raw.write(`event: floor\ndata: ${JSON.stringify(floor)}\n\n`);
  };

  await sendSnapshot();
  const interval = setInterval(() => {
    sendSnapshot().catch(() => undefined);
  }, 2000);

  request.raw.on("close", () => clearInterval(interval));
});

// --- Staff: tables ---
app.get("/v1/staff/tables", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  const venueId = process.env.DEV_VENUE_ID;
  if (!venueId) return reply.status(503).send({ title: "DEV_VENUE_ID not configured", status: 503 });
  return bus.dispatch({ type: "query.listStaffTables", venueId }, ctx());
});

// --- Staff: open dining session ---
app.post<{ Params: { table_id: string }; Body: { party_size?: number } }>(
  "/v1/staff/tables/:table_id/dining-sessions",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const result = await bus.dispatch(
      { type: "command.openDiningSession", tableId: request.params.table_id, partySize: request.body.party_size },
      ctx(),
    );
    if (result && typeof result === "object" && "notFound" in result) {
      return reply.status(404).send({ title: "Table not found", status: 404 });
    }
    return reply.status(201).send(result);
  },
);

// --- Staff: get table bill ---
app.get<{ Params: { table_id: string } }>(
  "/v1/staff/tables/:table_id/bills",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const result = await bus.dispatch(
      { type: "query.getTableBill", tableId: request.params.table_id },
      ctx(),
    );
    return result;
  },
);

// --- Staff: add bill line ---
app.post<{
  Params: { table_id: string };
  Body: {
    name: string;
    qty: number;
    unit_price_inc_vat_cents: number;
    vat_rate_bps: number;
    line_kind?: string;
    splittable?: boolean;
  };
}>("/v1/staff/tables/:table_id/bills/lines", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  const result = await bus.dispatch(
    {
      type: "command.addBillLine",
      tableId: request.params.table_id,
      name: request.body.name,
      qty: request.body.qty,
      unitPriceIncVatCents: request.body.unit_price_inc_vat_cents,
      vatRateBps: request.body.vat_rate_bps,
      lineKind: request.body.line_kind as "MENU_ITEM" | "SERVICE_CHARGE" | "MANUAL_MISC" | undefined,
      splittable: request.body.splittable,
    },
    ctx(),
  );
  if (result && typeof result === "object" && "error" in result) {
    return reply.status(422).send({ title: String(result.error), status: 422 });
  }
  return reply.status(201).send(result);
});

// --- Staff: activate payment mode ---
app.post<{ Params: { table_id: string } }>(
  "/v1/staff/tables/:table_id/payment-sessions",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const result = await bus.dispatch(
      { type: "command.activatePaymentMode", tableId: request.params.table_id },
      ctx(),
    );
    if (result && typeof result === "object" && "error" in result) {
      if (result.error === "BILL_EMPTY") {
        return reply.status(422).send({ title: "Bill total must be > €0", status: 422 });
      }
      return reply.status(422).send({ title: String(result.error), status: 422 });
    }
    return reply.status(201).send(result);
  },
);

// --- Staff: update table layout ---
app.patch<{
  Params: { table_id: string };
  Body: { pos_x: number; pos_y: number };
}>(
  "/v1/staff/tables/:table_id/layout",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const venueId = process.env.DEV_VENUE_ID;
    if (!venueId) return reply.status(503).send({ title: "DEV_VENUE_ID not configured", status: 503 });
    const result = await bus.dispatch(
      {
        type: "command.updateTableLayout",
        venueId,
        tableId: request.params.table_id,
        posX: request.body.pos_x,
        posY: request.body.pos_y,
      },
      ctx(),
    );
    if (result && typeof result === "object" && "notFound" in result) {
      return reply.status(404).send({ title: "Table not found", status: 404 });
    }
    return result;
  },
);

// --- Staff: update table session state ---
app.patch<{
  Params: { table_id: string };
  Body: { state?: string; party_size?: number };
}>(
  "/v1/staff/tables/:table_id/state",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const result = await bus.dispatch(
      {
        type: "command.updateTableState",
        tableId: request.params.table_id,
        state: request.body.state as
          | "SEATED"
          | "ORDERED"
          | "READY_TO_PAY"
          | "PAID"
          | "CLOSED"
          | undefined,
        partySize: request.body.party_size,
      },
      ctx(),
    );
    if (result && typeof result === "object" && "error" in result) {
      return reply.status(422).send({ title: String(result.error), status: 422, ...result });
    }
    return result;
  },
);

// --- Staff: close table ---
app.post<{ Params: { table_id: string }; Body: { dining_session_id: string; reason?: string } }>(
  "/v1/staff/tables/:table_id/close",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    const result = await bus.dispatch(
      {
        type: "command.closeDiningSession",
        tableId: request.params.table_id,
        diningSessionId: request.body.dining_session_id,
        reason: request.body.reason,
      },
      ctx(),
    );
    return result;
  },
);

// --- Staff: service signals ---
app.get("/v1/staff/service-signals", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  const venueId = process.env.DEV_VENUE_ID;
  if (!venueId) return reply.status(503).send({ title: "DEV_VENUE_ID not configured", status: 503 });
  return bus.dispatch({ type: "query.listServiceSignals", venueId }, ctx());
});

app.post<{ Params: { signal_id: string } }>(
  "/v1/staff/service-signals/:signal_id/ack",
  async (request, reply) => {
    if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
    return bus.dispatch({ type: "command.ackServiceSignal", signalId: request.params.signal_id }, ctx());
  },
);

// --- Admin: printable QR codes ---
app.get("/v1/admin/qr-codes", async (request, reply) => {
  if (!requireStaff(request)) return reply.status(401).send({ title: "Unauthorized", status: 401 });
  return {
    files: [...QR_FILES],
    download_base: "/v1/admin/qr-codes",
    hint: "Run pnpm generate:qr or ./scripts/rekentafel-poc.sh on the server first.",
  };
});

app.get<{ Params: { file: string } }>("/v1/admin/qr-codes/:file", async (request, reply) => {
  const file = request.params.file;
  if (!QR_FILES.has(file)) {
    return reply.status(404).send({ title: "File not found", status: 404 });
  }
  try {
    const buf = await readFile(resolve(QR_DIR, file));
    const type = file.endsWith(".pdf") ? "application/pdf" : "image/png";
    return reply
      .header("Content-Type", type)
      .header("Content-Disposition", `attachment; filename="${file}"`)
      .send(buf);
  } catch {
    return reply.status(404).send({
      title: "QR file not generated yet",
      status: 404,
      detail: "Run ./scripts/rekentafel-poc.sh or pnpm generate:qr on the Mac mini.",
    });
  }
});

// --- Mollie webhook ---
app.post("/v1/webhooks/mollie", async (request, reply) => {
  const payload = parseMollieWebhookBody(request.body);
  if (!payload) return reply.status(400).send({ title: "Invalid webhook body", status: 400 });

  await bus.dispatch(
    { type: "command.reconcileMollieWebhook", molliePaymentId: payload.id },
    { ...ctx(), actor: { type: "webhook" } },
  );

  return reply.status(200).send({ received: true });
});

app.listen({ port: PORT, host: "0.0.0.0" }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});

console.log(`Rekentafel API listening on http://localhost:${PORT}/v1`);
