import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

const defaultBase = "http://localhost:3000/v1";

export type UseTableLandingOptions = {
  restaurantSlug: string;
  tableCode: string;
  baseUrl?: string;
};

export function useTableLanding({ restaurantSlug, tableCode, baseUrl = defaultBase }: UseTableLandingOptions) {
  return useQuery({
    queryKey: ["table-landing", restaurantSlug, tableCode],
    queryFn: async () => {
      const response = await fetch(`${baseUrl}/t/${restaurantSlug}/${tableCode}`);
      if (!response.ok) throw new Error(`Table lookup failed: ${response.status}`);
      return response.json();
    },
    enabled: Boolean(restaurantSlug && tableCode),
  });
}

export function useJoinSession(baseUrl = defaultBase) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      payment_session_id?: string;
      join_pin?: string;
      join_token?: string;
      display_name: string;
    }) => {
      const response = await fetch(`${baseUrl}/payment-sessions/join`, {
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

export function usePaymentSession(paymentSessionId: string, baseUrl = defaultBase) {
  const participantId = getParticipantId(paymentSessionId);
  return useQuery({
    queryKey: ["payment-session", paymentSessionId],
    queryFn: async () => {
      const response = await fetch(`${baseUrl}/payment-sessions/${paymentSessionId}`, {
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
  baseUrl = defaultBase,
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!paymentSessionId) return;
    const source = new EventSource(`${baseUrl}/payment-sessions/${paymentSessionId}/events`);

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
  }, [paymentSessionId, baseUrl]);
}

export function useClaimItem(baseUrl = defaultBase) {
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

      const response = await fetch(
        `${baseUrl}/payment-sessions/${input.paymentSessionId}/claims`,
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

export function useCombinedCheckout(baseUrl = defaultBase) {
  return useMutation({
    mutationFn: async (input: {
      paymentSessionId: string;
      tipCents?: number;
      redirectUrl?: string;
    }) => {
      const participantId = getParticipantId(input.paymentSessionId);
      if (!participantId) throw new Error("Not joined");

      const response = await fetch(
        `${baseUrl}/payment-sessions/${input.paymentSessionId}/checkout`,
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

export function useCallServer(baseUrl = defaultBase) {
  return useMutation({
    mutationFn: async (input: { tableId: string }) => {
      const response = await fetch(`${baseUrl}/tables/${input.tableId}/service-signals`, {
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
