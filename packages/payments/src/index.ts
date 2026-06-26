import { createMollieClient, type Payment } from "@mollie/api-client";
import type { MoneyCents } from "@rekentafel/shared-types";
import {
  quoteCombinedCheckout,
  type BillSettlementSnapshot,
  type CombinedCheckoutPledge,
} from "@rekentafel/split-engine";

export type MollieClient = ReturnType<typeof createMollieClient>;

export type MollieConfig = {
  apiKey: string;
  webhookUrl: string;
};

export type CreatePaymentInput = {
  amountCents: MoneyCents;
  description: string;
  redirectUrl: string;
  metadata: Record<string, string>;
  idempotencyKey?: string;
};

export type CreatePaymentResult = {
  molliePaymentId: string;
  checkoutUrl: string;
  expiresAt: Date;
};

export class MolliePaymentsAdapter {
  private readonly client: MollieClient;

  constructor(private readonly config: MollieConfig) {
    this.client = createMollieClient({ apiKey: config.apiKey });
  }

  async createPayment(input: CreatePaymentInput): Promise<CreatePaymentResult> {
    const payment = await this.client.payments.create({
      amount: {
        currency: "EUR",
        value: (input.amountCents / 100).toFixed(2),
      },
      description: input.description,
      redirectUrl: input.redirectUrl,
      webhookUrl: this.config.webhookUrl,
      metadata: input.metadata,
    });

    const checkoutUrl = payment.getCheckoutUrl();
    if (!checkoutUrl) {
      throw new Error("Mollie payment missing checkout URL");
    }

    return {
      molliePaymentId: payment.id,
      checkoutUrl,
      expiresAt: payment.expiresAt ? new Date(payment.expiresAt) : new Date(Date.now() + 15 * 60_000),
    };
  }

  async getPayment(molliePaymentId: string): Promise<Payment> {
    return this.client.payments.get(molliePaymentId);
  }
}

export type CombinedCheckoutInput = {
  paymentSessionId: string;
  checkoutIntentId: string;
  paymentLeadParticipantId: string;
  settlement: BillSettlementSnapshot;
  pledges: CombinedCheckoutPledge[];
  redirectUrl: string;
  tipCents?: MoneyCents;
};

export type CombinedCheckoutResult = CreatePaymentResult & {
  quote: ReturnType<typeof quoteCombinedCheckout>;
  totalCents: MoneyCents;
};

/**
 * Combined checkout orchestrator: one Mollie payment settles the table's
 * remaining balance while guest claims remain visible for audit/split display.
 */
export class CombinedCheckoutService {
  constructor(private readonly mollie: MolliePaymentsAdapter) {}

  quote(settlement: BillSettlementSnapshot, pledges: CombinedCheckoutPledge[]) {
    return quoteCombinedCheckout(settlement, pledges);
  }

  async initiate(input: CombinedCheckoutInput): Promise<CombinedCheckoutResult> {
    const quote = quoteCombinedCheckout(input.settlement, input.pledges);
    const extraTip = input.tipCents ?? 0;
    const totalCents = quote.checkoutTotalCents + extraTip;

    const result = await this.mollie.createPayment({
      amountCents: totalCents,
      description: `Rekentafel table payment (${input.paymentSessionId.slice(0, 8)})`,
      redirectUrl: input.redirectUrl,
      metadata: {
        payment_session_id: input.paymentSessionId,
        checkout_intent_id: input.checkoutIntentId,
        checkout_mode: "COMBINED",
        payment_lead_participant_id: input.paymentLeadParticipantId,
        participant_ids: quote.participantIds.join(","),
      },
    });

    return { ...result, quote, totalCents };
  }
}

export type MollieWebhookPayload = {
  id: string;
};

export function parseMollieWebhookBody(body: unknown): MollieWebhookPayload | null {
  if (typeof body !== "object" || body === null) return null;
  const id = "id" in body && typeof body.id === "string" ? body.id : null;
  if (!id) return null;
  return { id };
}

export type WebhookReconcileResult = {
  molliePaymentId: string;
  status: "paid" | "failed" | "open" | "canceled" | "expired";
  amountCents: MoneyCents;
};

export async function reconcileMollieWebhook(
  adapter: MolliePaymentsAdapter,
  payload: MollieWebhookPayload,
): Promise<WebhookReconcileResult> {
  const payment = await adapter.getPayment(payload.id);
  const amountCents = Math.round(Number(payment.amount.value) * 100);

  const statusMap: Record<string, WebhookReconcileResult["status"]> = {
    paid: "paid",
    failed: "failed",
    open: "open",
    canceled: "canceled",
    expired: "expired",
  };

  return {
    molliePaymentId: payment.id,
    status: statusMap[payment.status] ?? "open",
    amountCents,
  };
}

export function createPaymentsFromEnv(env: NodeJS.ProcessEnv = process.env): {
  mollie: MolliePaymentsAdapter;
  combinedCheckout: CombinedCheckoutService;
} {
  const apiKey = env.MOLLIE_API_KEY;
  const webhookUrl = env.MOLLIE_WEBHOOK_URL ?? "http://localhost:3000/v1/webhooks/mollie";
  if (!apiKey) {
    throw new Error("MOLLIE_API_KEY is required");
  }
  const mollie = new MolliePaymentsAdapter({ apiKey, webhookUrl });
  return { mollie, combinedCheckout: new CombinedCheckoutService(mollie) };
}
