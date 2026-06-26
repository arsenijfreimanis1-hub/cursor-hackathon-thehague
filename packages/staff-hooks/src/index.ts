import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const defaultBase = "http://localhost:3000/v1";

export type StaffTable = {
  table: {
    table_id: string;
    table_code: string;
    session_state: string;
    qr_url?: string;
  };
  dining_session?: { dining_session_id: string; state: string };
  payment_session_id?: string;
  join_pin?: string;
  bill_total_cents?: number;
};

function authHeaders(token: string | null) {
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : {};
}

export function useStaffTables(accessToken: string | null, baseUrl = defaultBase) {
  return useQuery({
    queryKey: ["staff-tables", accessToken],
    queryFn: async (): Promise<StaffTable[]> => {
      const response = await fetch(`${baseUrl}/staff/tables`, {
        headers: authHeaders(accessToken) as HeadersInit,
      });
      if (!response.ok) throw new Error(`Failed to load tables: ${response.status}`);
      return response.json();
    },
    enabled: Boolean(accessToken),
    refetchInterval: 5000,
  });
}

export function useTableBill(tableId: string | null, accessToken: string | null, baseUrl = defaultBase) {
  return useQuery({
    queryKey: ["table-bill", tableId],
    queryFn: async () => {
      const response = await fetch(`${baseUrl}/staff/tables/${tableId}/bills`, {
        headers: authHeaders(accessToken) as HeadersInit,
      });
      if (!response.ok) throw new Error(`Failed to load bill: ${response.status}`);
      return response.json();
    },
    enabled: Boolean(tableId && accessToken),
  });
}

export function useOpenSession(accessToken: string | null, baseUrl = defaultBase) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { tableId: string; partySize?: number }) => {
      const response = await fetch(`${baseUrl}/staff/tables/${input.tableId}/dining-sessions`, {
        method: "POST",
        headers: authHeaders(accessToken) as HeadersInit,
        body: JSON.stringify({ party_size: input.partySize ?? 2 }),
      });
      if (!response.ok) throw new Error(`Open session failed: ${response.status}`);
      return response.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["staff-tables"] }),
  });
}

export function useAddBillLine(accessToken: string | null, baseUrl = defaultBase) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      tableId: string;
      name: string;
      qty: number;
      unitPriceIncVatCents: number;
      vatRateBps: number;
    }) => {
      const response = await fetch(`${baseUrl}/staff/tables/${input.tableId}/bills/lines`, {
        method: "POST",
        headers: authHeaders(accessToken) as HeadersInit,
        body: JSON.stringify({
          name: input.name,
          qty: input.qty,
          unit_price_inc_vat_cents: input.unitPriceIncVatCents,
          vat_rate_bps: input.vatRateBps,
        }),
      });
      if (!response.ok) throw new Error(`Add line failed: ${response.status}`);
      return response.json();
    },
    onSuccess: (_d, vars) => {
      qc.invalidateQueries({ queryKey: ["table-bill", vars.tableId] });
      qc.invalidateQueries({ queryKey: ["staff-tables"] });
    },
  });
}

export function useActivatePayment(accessToken: string | null, baseUrl = defaultBase) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { tableId: string }) => {
      const response = await fetch(`${baseUrl}/staff/tables/${input.tableId}/payment-sessions`, {
        method: "POST",
        headers: authHeaders(accessToken) as HeadersInit,
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.title ?? `Activate failed: ${response.status}`);
      }
      return response.json() as Promise<{
        payment_session_id: string;
        join_pin: string;
        join_token: string;
        guest_url: string;
      }>;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["staff-tables"] }),
  });
}

export function useCloseTable(accessToken: string | null, baseUrl = defaultBase) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { tableId: string; diningSessionId: string; reason?: string }) => {
      const response = await fetch(`${baseUrl}/staff/tables/${input.tableId}/close`, {
        method: "POST",
        headers: authHeaders(accessToken) as HeadersInit,
        body: JSON.stringify({
          dining_session_id: input.diningSessionId,
          reason: input.reason,
        }),
      });
      if (!response.ok) throw new Error(`Close failed: ${response.status}`);
      return response.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["staff-tables"] }),
  });
}

export function useServiceSignals(accessToken: string | null, baseUrl = defaultBase) {
  return useQuery({
    queryKey: ["service-signals"],
    queryFn: async () => {
      const response = await fetch(`${baseUrl}/staff/service-signals`, {
        headers: authHeaders(accessToken) as HeadersInit,
      });
      if (!response.ok) throw new Error(`Signals failed: ${response.status}`);
      return response.json();
    },
    enabled: Boolean(accessToken),
    refetchInterval: 3000,
  });
}

export function useAckSignal(accessToken: string | null, baseUrl = defaultBase) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (signalId: string) => {
      const response = await fetch(`${baseUrl}/staff/service-signals/${signalId}/ack`, {
        method: "POST",
        headers: authHeaders(accessToken) as HeadersInit,
      });
      if (!response.ok) throw new Error(`Ack failed: ${response.status}`);
      return response.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["service-signals"] }),
  });
}
