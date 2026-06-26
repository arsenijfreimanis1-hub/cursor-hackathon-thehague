import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

const defaultBase = "http://localhost:3000/v1";

function resolveBase(baseUrl?: string): string {
  if (baseUrl) return baseUrl;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return `http://${host}:3000/v1`;
    }
  }
  return defaultBase;
}

async function apiFetch(url: string, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    throw new TableLookupError(
      "UNREACHABLE",
      err instanceof Error ? err.message : "Network error",
    );
  } finally {
    clearTimeout(timeout);
  }
}

export class TableLookupError extends Error {
  readonly code: "NOT_FOUND" | "UNREACHABLE" | "HTTP";

  constructor(code: "NOT_FOUND" | "UNREACHABLE" | "HTTP", message: string) {
    super(message);
    this.name = "TableLookupError";
    this.code = code;
  }
}

export type UseTableLandingOptions = {
  restaurantSlug: string;
  tableCode: string;
  baseUrl?: string;
};

export function useTableLanding({ restaurantSlug, tableCode, baseUrl }: UseTableLandingOptions) {
  const base = resolveBase(baseUrl);
  return useQuery({
    queryKey: ["table-landing", restaurantSlug, tableCode, base],
    queryFn: async () => {
      const response = await apiFetch(`${base}/t/${restaurantSlug}/${tableCode}`);
      if (response.status === 404) {
        throw new TableLookupError("NOT_FOUND", "Table not found");
      }
      if (!response.ok) {
        throw new TableLookupError("HTTP", `Table lookup failed: ${response.status}`);
      }
      return response.json();
    },
    enabled: Boolean(restaurantSlug && tableCode),
    retry: 1,
  });
}

export function useJoinSession(baseUrl?: string) {
  const base = resolveBase(baseUrl);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      payment_session_id?: string;
      join_pin?: string;
      join_token?: string;
      display_name: string;
    }) => {
      const response = await apiFetch(`${base}/payment-sessions/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      });
      if (!response.ok) throw new Error(`Join failed: ${response.status}`);
      return response.json() as Promise<{
        participant_id: string;
        payment_session_id: string;
        display_name: string;
      }>;
    },
    onSuccess: (data) => {
      localStorage.setItem(`participant_${data.payment_session_id}`, data.participant_id);
      queryClient.invalidateQueries({ queryKey: ["payment-session", data.payment_session_id] });
    },
  });
}

export function getParticipantId(paymentSessionId: string): string | null {
  return localStorage.getItem(`participant_${paymentSessionId}`);
}

export function usePaymentSession(paymentSessionId: string, baseUrl?: string) {
  const base = resolveBase(baseUrl);
  const participantId = getParticipantId(paymentSessionId);
  return useQuery({
    queryKey: ["payment-session", paymentSessionId, base],
    queryFn: async () => {
      const response = await apiFetch(`${base}/payment-sessions/${paymentSessionId}`, {
        headers: participantId ? { "X-Participant-Id": participantId } : {},
      });
      if (!response.ok) throw new Error(`Session fetch failed: ${response.status}`);
      return response.json();
    },
    enabled: Boolean(paymentSessionId),
    refetchInterval: 5000,
  });
}

export function useBillEvents(
  paymentSessionId: string,
  onEvent: (event: { type: string; payload: Record<string, unknown> }) => void,
  baseUrl?: string,
) {
  const base = resolveBase(baseUrl);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!paymentSessionId) return;
    const source = new EventSource(`${base}/payment-sessions/${paymentSessionId}/events`);

    const handler = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        onEventRef.current(data);
      } catch {
        /* ignore parse errors */
      }
    };

    source.addEventListener("bill.updated", handler);
    source.addEventListener("participant.joined", handler);
    source.addEventListener("message", handler);

    return () => source.close();
  }, [paymentSessionId, base]);
}

export function useClaimItem(baseUrl?: string) {
  const base = resolveBase(baseUrl);
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      paymentSessionId: string;
      billLineId: string;
      billVersion: number;
      splitMode?: "ITEM" | "SHARED";
    }) => {
      const participantId = getParticipantId(input.paymentSessionId);
      if (!participantId) throw new Error("Not joined");

      const response = await apiFetch(
        `${base}/payment-sessions/${input.paymentSessionId}/claims`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Participant-Id": participantId,
            "If-Match-Bill-Version": String(input.billVersion),
          },
          body: JSON.stringify({
            bill_line_id: input.billLineId,
            split_mode: input.splitMode ?? "ITEM",
          }),
        },
      );
      if (!response.ok) throw new Error(`Claim failed: ${response.status}`);
      return response.json();
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["payment-session", vars.paymentSessionId] });
    },
  });
}

export function useCombinedCheckout(baseUrl?: string) {
  const base = resolveBase(baseUrl);
  return useMutation({
    mutationFn: async (input: {
      paymentSessionId: string;
      tipCents?: number;
      redirectUrl?: string;
    }) => {
      const participantId = getParticipantId(input.paymentSessionId);
      if (!participantId) throw new Error("Not joined");

      const response = await apiFetch(
        `${base}/payment-sessions/${input.paymentSessionId}/checkout`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Participant-Id": participantId,
          },
          body: JSON.stringify({
            checkout_mode: "COMBINED",
            tip_cents: input.tipCents ?? 0,
            redirect_url: input.redirectUrl,
          }),
        },
      );
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.title ?? `Checkout failed: ${response.status}`);
      }
      return response.json() as Promise<{
        mollie_checkout_url: string;
        total_cents: number;
        checkout_mode: string;
      }>;
    },
  });
}

export function useCallServer(baseUrl?: string) {
  const base = resolveBase(baseUrl);
  return useMutation({
    mutationFn: async (input: { tableId: string }) => {
      const response = await apiFetch(`${base}/tables/${input.tableId}/service-signals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signal_type: "ASSISTANCE" }),
      });
      if (!response.ok) throw new Error(`Call server failed: ${response.status}`);
      return response.json();
    },
  });
}

export function useGuestSession(paymentSessionId: string) {
  const [joined, setJoined] = useState(() => Boolean(getParticipantId(paymentSessionId)));
  return { joined, setJoined, participantId: getParticipantId(paymentSessionId) };
}
