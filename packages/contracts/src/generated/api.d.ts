/**
 * OpenAPI-generated path types (Phase 0 stub).
 * Regenerate: pnpm --filter @rekentafel/contracts generate:types
 */
export interface paths {
  "/payment-sessions/join": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["JoinPaymentSessionRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["JoinPaymentSessionResponse"];
          };
        };
      };
    };
  };
  "/staff/tables/{table_id}/payment-sessions": {
    post: {
      responses: {
        201: {
          content: {
            "application/json": components["schemas"]["ActivatePaymentResponse"];
          };
        };
      };
    };
  };
}

export interface components {
  schemas: {
    JoinPaymentSessionRequest: {
      payment_session_id: string;
      token: string;
      token_type: "secret" | "pin";
      display_name: string;
    };
    JoinPaymentSessionResponse: {
      participant_id: string;
      participant_token: string;
      payment_session: components["schemas"]["PaymentSessionDetail"];
    };
    ActivatePaymentResponse: {
      payment_session_id: string;
      join_pin: string;
      token: string;
      join_url?: string;
      expires_at: string;
      bill: components["schemas"]["Bill"];
    };
    PaymentSessionDetail: {
      payment_session_id: string;
      restaurant_id: string;
      table_id: string;
      bill_id: string;
      status: "OPEN" | "CLOSED" | "EXPIRED";
      expires_at: string;
      bill: components["schemas"]["Bill"];
      participants: components["schemas"]["Participant"][];
      settlement: components["schemas"]["BillSettlement"];
    };
    Bill: {
      bill_id: string;
      dining_session_id?: string;
      bill_version: number;
      currency: "EUR";
      lines: components["schemas"]["BillLine"][];
      bill_grand_total_cents: number;
      service_charge_cents?: number;
      settlement?: components["schemas"]["BillSettlement"];
    };
    BillLine: {
      line_id: string;
      kind: "MENU_ITEM" | "SERVICE_CHARGE" | "DISCOUNT" | "ROUNDING_ADJ" | "MANUAL_MISC";
      name: string;
      qty: number;
      unit_price_inc_vat_cents: number;
      vat_rate_bps: number;
      line_total_inc_vat_cents: number;
      splittable?: boolean;
    };
    BillSettlement: {
      state: components["schemas"]["TableBillSettlementState"];
      bill_grand_total_cents: number;
      confirmed_paid_cents: number;
      remaining_cents: number;
      unclaimed_cents: number;
      allocated_cents: number;
    };
    TableBillSettlementState:
      | "BILL_DRAFT"
      | "ALLOCATION_OPEN"
      | "ALLOCATION_FROZEN"
      | "CHECKOUT_IN_PROGRESS"
      | "PARTIALLY_PAID"
      | "FULLY_PAID"
      | "CLOSED"
      | "VOID";
    Participant: {
      participant_id: string;
      display_name: string;
      state: components["schemas"]["ParticipantState"];
      allocated_cents?: number;
      paid_cents?: number;
    };
    ParticipantState:
      | "JOINED"
      | "ALLOCATING"
      | "CHECKOUT_LOCKED"
      | "PAYMENT_PENDING"
      | "PAID"
      | "PAYMENT_FAILED"
      | "RELEASED"
      | "OVERRIDDEN";
  };
}
