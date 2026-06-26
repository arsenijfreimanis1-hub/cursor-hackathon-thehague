import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { randomUUID } from "node:crypto";
import type {
  ActivatePaymentResponse,
  JoinPaymentSessionRequest,
  JoinPaymentSessionResponse,
} from "@rekentafel/contracts";

const PORT = Number(process.env.MOCK_PORT ?? 3100);
const BASE_PATH = "/v1";

const mockPaymentSessionId = "11111111-1111-4111-8111-111111111111";
const mockTableId = "22222222-2222-4222-8222-222222222222";
const mockBillId = "33333333-3333-4333-8333-333333333333";
const mockDiningSessionId = "44444444-4444-4444-8444-444444444444";
const mockRestaurantId = "55555555-5555-4555-8555-555555555555";
const joinToken = "mock-secret-token-482917";
const joinPin = "482917";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function handleJoinPaymentSession(body: JoinPaymentSessionRequest): Response {
  const tokenValid =
    (body.token_type === "secret" && body.token === joinToken) ||
    (body.token_type === "pin" && body.token === joinPin);

  if (body.payment_session_id !== mockPaymentSessionId || !tokenValid) {
    return jsonResponse(
      {
        type: "https://api.rekentafel.nl/errors/invalid-token",
        title: "Invalid payment session token or PIN",
        status: 401,
        code: "PIN_LOCKED",
      },
      401,
    );
  }

  const response: JoinPaymentSessionResponse = {
    participant_id: randomUUID(),
    participant_token: "mock-participant-jwt",
    payment_session: {
      payment_session_id: mockPaymentSessionId,
      restaurant_id: mockRestaurantId,
      table_id: mockTableId,
      bill_id: mockBillId,
      status: "OPEN",
      expires_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      bill: {
        bill_id: mockBillId,
        dining_session_id: mockDiningSessionId,
        bill_version: 1,
        currency: "EUR",
        bill_grand_total_cents: 8640,
        service_charge_cents: 640,
        lines: [
          {
            line_id: randomUUID(),
            kind: "MENU_ITEM",
            name: "Bitterballen",
            qty: 2,
            unit_price_inc_vat_cents: 850,
            vat_rate_bps: 900,
            line_total_inc_vat_cents: 1700,
            splittable: false,
          },
        ],
        settlement: {
          state: "ALLOCATION_OPEN",
          bill_grand_total_cents: 8640,
          confirmed_paid_cents: 0,
          remaining_cents: 8640,
          unclaimed_cents: 8640,
          allocated_cents: 0,
        },
      },
      participants: [
        {
          participant_id: randomUUID(),
          display_name: body.display_name,
          state: "JOINED",
          allocated_cents: 0,
          paid_cents: 0,
        },
      ],
      settlement: {
        state: "ALLOCATION_OPEN",
        bill_grand_total_cents: 8640,
        confirmed_paid_cents: 0,
        remaining_cents: 8640,
        unclaimed_cents: 8640,
        allocated_cents: 0,
      },
    },
  };

  return jsonResponse(response, 200);
}

function handleActivatePaymentMode(tableId: string): Response {
  if (tableId !== mockTableId) {
    return jsonResponse(
      {
        type: "https://api.rekentafel.nl/errors/not-found",
        title: "Table not found",
        status: 404,
      },
      404,
    );
  }

  const response: ActivatePaymentResponse = {
    payment_session_id: mockPaymentSessionId,
    join_pin: joinPin,
    token: joinToken,
    join_url: `https://pay.rekentafel.nl/join/${mockPaymentSessionId}`,
    expires_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    bill: {
      bill_id: mockBillId,
      dining_session_id: mockDiningSessionId,
      bill_version: 1,
      currency: "EUR",
      bill_grand_total_cents: 8640,
      service_charge_cents: 640,
      lines: [
        {
          line_id: randomUUID(),
          kind: "MENU_ITEM",
          name: "Bitterballen",
          qty: 2,
          unit_price_inc_vat_cents: 850,
          vat_rate_bps: 900,
          line_total_inc_vat_cents: 1700,
        },
      ],
      settlement: {
        state: "ALLOCATION_OPEN",
        bill_grand_total_cents: 8640,
        confirmed_paid_cents: 0,
        remaining_cents: 8640,
        unclaimed_cents: 8640,
        allocated_cents: 0,
      },
    },
  };

  return jsonResponse(response, 201);
}

async function handleRequest(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname.replace(BASE_PATH, "") || "/";

  if (request.method === "GET" && path === "/health") {
    return jsonResponse({ status: "ok" });
  }

  if (request.method === "POST" && path === "/payment-sessions/join") {
    const body = (await request.json()) as JoinPaymentSessionRequest;
    return handleJoinPaymentSession(body);
  }

  const activateMatch = path.match(
    /^\/staff\/tables\/([^/]+)\/payment-sessions$/,
  );
  if (request.method === "POST" && activateMatch) {
    return handleActivatePaymentMode(activateMatch[1]!);
  }

  return jsonResponse(
    {
      type: "https://api.rekentafel.nl/errors/not-found",
      title: "Not found",
      status: 404,
    },
    404,
  );
}

const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
  const host = req.headers.host ?? `localhost:${PORT}`;
  const url = `http://${host}${req.url ?? "/"}`;
  const headers = new Headers();

  for (const [key, value] of Object.entries(req.headers)) {
    if (value !== undefined) {
      headers.set(key, Array.isArray(value) ? value.join(",") : String(value));
    }
  }

  const body =
    req.method === "POST" || req.method === "PUT" || req.method === "PATCH"
      ? await new Promise<Buffer>((resolve, reject) => {
          const chunks: Buffer[] = [];
          req.on("data", (chunk: Buffer) => chunks.push(chunk));
          req.on("end", () => resolve(Buffer.concat(chunks)));
          req.on("error", reject);
        })
      : undefined;

  const request = new Request(url, {
    method: req.method,
    headers,
    body: body?.length ? body.toString("utf8") : undefined,
  });

  const response = await handleRequest(request);
  res.statusCode = response.status;
  response.headers.forEach((value, key) => {
    res.setHeader(key, value);
  });
  res.end(Buffer.from(await response.arrayBuffer()));
});

server.listen(PORT, () => {
  console.log(`Rekentafel MSW mock server listening on http://localhost:${PORT}${BASE_PATH}`);
  console.log(`Join token: ${joinToken} | PIN: ${joinPin}`);
});

export { handleRequest, server };
