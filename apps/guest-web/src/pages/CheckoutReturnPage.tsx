import { useSearch } from "@tanstack/react-router";
import { Button, Card, formatEuro } from "@rekentafel/ui-core";
import { usePaymentSession } from "@rekentafel/guest-hooks";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function CheckoutReturnPage() {
  const search = useSearch({ from: "/checkout/return" }) as { session?: string };
  const sessionId = search.session ?? "";
  const { data } = usePaymentSession(sessionId, API_BASE);

  const settlement = data?.settlement as { remaining_cents?: number } | undefined;
  const paid = settlement?.remaining_cents === 0;

  return (
    <main className="main stack">
      <Card title={paid ? "Betaling gelukt!" : "Betaling ontvangen"}>
        {paid ? (
          <>
            <p>De rekening is volledig betaald. Bedankt!</p>
            {settlement && <p>Resterend: {formatEuro(settlement.remaining_cents ?? 0)}</p>}
          </>
        ) : (
          <>
            <p>Uw betaling wordt verwerkt. Het kan even duren voordat de rekening is bijgewerkt.</p>
            {settlement && (
              <p className="muted">Nog te betalen: {formatEuro(settlement.remaining_cents ?? 0)}</p>
            )}
          </>
        )}
        {sessionId && (
          <Button onClick={() => { window.location.href = `/session/${sessionId}`; }}>
            Terug naar rekening
          </Button>
        )}
      </Card>
    </main>
  );
}
