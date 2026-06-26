/**
 * Typed API client stub generated from packages/contracts/openapi.yaml.
 * Phase 0: guest join + staff activate-payment only.
 */

import type { paths } from "./generated/api.js";

export type JoinPaymentSessionRequest =
  paths["/payment-sessions/join"]["post"]["requestBody"]["content"]["application/json"];
export type JoinPaymentSessionResponse =
  paths["/payment-sessions/join"]["post"]["responses"]["200"]["content"]["application/json"];
export type ActivatePaymentResponse =
  paths["/staff/tables/{table_id}/payment-sessions"]["post"]["responses"]["201"]["content"]["application/json"];

export type RekentafelClientOptions = {
  baseUrl?: string;
  fetch?: typeof fetch;
};

export class RekentafelClient {
  private readonly baseUrl: string;
  private readonly fetchFn: typeof fetch;

  constructor(options: RekentafelClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? "http://localhost:3000/v1";
    this.fetchFn = options.fetch ?? fetch;
  }

  async joinPaymentSession(
    body: JoinPaymentSessionRequest,
    idempotencyKey?: string,
  ): Promise<JoinPaymentSessionResponse> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const response = await this.fetchFn(`${this.baseUrl}/payment-sessions/join`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`joinPaymentSession failed: ${response.status}`);
    }

    return (await response.json()) as JoinPaymentSessionResponse;
  }

  async activatePaymentMode(
    tableId: string,
    accessToken: string,
    body?: { ttl_seconds?: number },
    idempotencyKey?: string,
  ): Promise<ActivatePaymentResponse> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    };
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    const response = await this.fetchFn(
      `${this.baseUrl}/staff/tables/${tableId}/payment-sessions`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(body ?? {}),
      },
    );

    if (!response.ok) {
      throw new Error(`activatePaymentMode failed: ${response.status}`);
    }

    return (await response.json()) as ActivatePaymentResponse;
  }
}

export { RekentafelClient as default };
