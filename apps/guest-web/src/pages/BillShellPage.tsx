import { useCallback } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import {
  useBillEvents,
  useClaimItem,
  useCombinedCheckout,
  useGuestSession,
  usePaymentSession,
} from "@rekentafel/guest-hooks";
import { Button, Card, formatEuro } from "@rekentafel/ui-core";
import { useQueryClient } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

type BillLine = {
  line_id: string;
  name: string;
  line_total_inc_vat_cents: number;
  splittable: boolean;
};

type Allocation = {
  allocation_id: string;
  participant_name: string;
  line_name: string;
  amount_cents: number;
};

export function BillShellPage() {
  const { paymentSessionId } = useParams({ from: "/session/$paymentSessionId" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { joined } = useGuestSession(paymentSessionId);
  const { data, isLoading, error } = usePaymentSession(paymentSessionId, API_BASE);
  const claim = useClaimItem(API_BASE);
  const checkout = useCombinedCheckout(API_BASE);

  useBillEvents(
    paymentSessionId,
    useCallback(() => {
      queryClient.invalidateQueries({ queryKey: ["payment-session", paymentSessionId] });
    }, [queryClient, paymentSessionId]),
    API_BASE,
  );

  if (!joined) {
    navigate({ to: "/session/$paymentSessionId/join", params: { paymentSessionId } });
    return null;
  }

  if (isLoading) return <main className="main"><p>Laden…</p></main>;
  if (error || !data) {
    return (
      <main className="main">
        <Card title="Fout"><p>Kon rekening niet laden.</p></Card>
      </main>
    );
  }

  const bill = data.bill as {
    bill_id: string;
    bill_grand_total_cents: number;
    confirmed_paid_cents: number;
    lines: BillLine[];
  };
  const settlement = data.settlement as {
    remaining_cents: number;
    unclaimed_cents: number;
    allocated_cents: number;
  };
  const participants = data.participants as { participant_id: string; display_name: string }[];
  const allocations = (data.allocations ?? []) as Allocation[];
  const billVersion = data.bill_version as number;

  return (
    <main className="main stack">
      <header className="hero">
        <h1>Rekening</h1>
        <p className="muted">
          Resterend: <strong>{formatEuro(settlement.remaining_cents)}</strong>
        </p>
      </header>

      <Card title="Deelnemers">
        <div className="chip-row">
          {participants.map((p) => (
            <span key={p.participant_id} className="chip">{p.display_name}</span>
          ))}
        </div>
      </Card>

      <Card title="Gerechten">
        <ul className="bill-lines">
          {bill.lines.map((line) => {
            const claimed = allocations.filter((a) => a.line_name === line.name);
            return (
              <li key={line.line_id} className="bill-line">
                <div>
                  <strong>{line.name}</strong>
                  <span>{formatEuro(line.line_total_inc_vat_cents)}</span>
                </div>
                {claimed.length > 0 ? (
                  <p className="muted">
                    Geclaimd door: {claimed.map((c) => c.participant_name).join(", ")}
                  </p>
                ) : line.splittable ? (
                  <Button
                    variant="secondary"
                    disabled={claim.isPending}
                    onClick={() =>
                      claim.mutate({
                        paymentSessionId,
                        billLineId: line.line_id,
                        billVersion,
                      })
                    }
                  >
                    Claim
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
        <p className="muted">
          Totaal: {formatEuro(bill.bill_grand_total_cents)} ·
          Betaald: {formatEuro(bill.confirmed_paid_cents)} ·
          Ongeclaimd: {formatEuro(settlement.unclaimed_cents)}
        </p>
      </Card>

      <Card title="Gecombineerd afrekenen">
        <p className="muted">
          Iedereen claimt apart. Eén persoon betaalt het resterende bedrag in één Mollie-betaling.
        </p>
        <Button
          disabled={checkout.isPending || settlement.remaining_cents <= 0}
          onClick={() =>
            checkout.mutate(
              {
                paymentSessionId,
                redirectUrl: `${window.location.origin}/checkout/return?session=${paymentSessionId}`,
              },
              {
                onSuccess: (result) => {
                  if (result.mollie_checkout_url) {
                    window.location.href = result.mollie_checkout_url;
                  }
                },
              },
            )
          }
        >
          {checkout.isPending
            ? "Bezig…"
            : `Betaal ${formatEuro(settlement.remaining_cents)} via Mollie`}
        </Button>
        {checkout.error && <p className="error">{checkout.error.message}</p>}
      </Card>
    </main>
  );
}
