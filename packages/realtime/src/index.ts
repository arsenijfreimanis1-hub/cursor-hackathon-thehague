import type { BillSettlementSnapshot } from "@rekentafel/split-engine";

export type RealtimeEventType =
  | "bill.updated"
  | "participant.joined"
  | "allocation.changed"
  | "checkout.started"
  | "payment.confirmed"
  | "session.closed";

export type RealtimeEvent<T extends RealtimeEventType = RealtimeEventType> = {
  type: T;
  paymentSessionId: string;
  billVersion: number;
  emittedAt: string;
  payload: Record<string, unknown>;
};

export type BillUpdatedPayload = {
  settlement: BillSettlementSnapshot;
};

export function createBillUpdatedEvent(
  paymentSessionId: string,
  billVersion: number,
  settlement: BillSettlementSnapshot,
): RealtimeEvent<"bill.updated"> {
  return {
    type: "bill.updated",
    paymentSessionId,
    billVersion,
    emittedAt: new Date().toISOString(),
    payload: { settlement },
  };
}

export function formatSseMessage(event: RealtimeEvent): string {
  return `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
}

type Subscriber = (event: RealtimeEvent) => void;

/** In-process pub/sub for MVP; swap for Redis in production. */
export class BillEventBus {
  private readonly subscribers = new Map<string, Set<Subscriber>>();

  subscribe(paymentSessionId: string, handler: Subscriber): () => void {
    const set = this.subscribers.get(paymentSessionId) ?? new Set();
    set.add(handler);
    this.subscribers.set(paymentSessionId, set);
    return () => {
      set.delete(handler);
      if (set.size === 0) this.subscribers.delete(paymentSessionId);
    };
  }

  publish(event: RealtimeEvent): void {
    const set = this.subscribers.get(event.paymentSessionId);
    if (!set) return;
    for (const handler of set) handler(event);
  }
}
