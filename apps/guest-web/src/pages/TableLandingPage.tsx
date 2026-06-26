import { useParams } from "@tanstack/react-router";
import { useTableLanding } from "@rekentafel/guest-hooks";
import { Button, Card, formatEuro } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function TableLandingPage() {
  const { restaurantSlug, tableCode } = useParams({ from: "/t/$restaurantSlug/$tableCode" });
  const { data, isLoading, error } = useTableLanding({
    restaurantSlug,
    tableCode,
    baseUrl: API_BASE,
  });

  if (isLoading) return <main className="main"><p>Laden…</p></main>;
  if (error || !data) {
    return (
      <main className="main">
        <Card title="Tafel niet gevonden">
          <p>Controleer de QR-code of vraag uw bediening.</p>
        </Card>
      </main>
    );
  }

  const table = data.table as { table_code: string; session_state: string };
  const restaurant = data.restaurant as { name: string };
  const hint = data.payment_session_hint as { payment_session_id: string } | null;

  return (
    <main className="main stack">
      <header className="hero">
        <h1>{restaurant.name}</h1>
        <p className="muted">Tafel {table.table_code}</p>
      </header>

      <Card title="Status">
        <p>Sessie: {table.session_state}</p>
        {hint ? (
          <>
            <p>Betaling actief — vraag de pincode aan uw bediening.</p>
            <Button onClick={() => {
              window.location.href = `/session/${hint.payment_session_id}/join`;
            }}>
              Deelnemen aan rekening
            </Button>
          </>
        ) : (
          <p className="muted">Menu bekijken of de bediening roepen.</p>
        )}
      </Card>

      <Card title="Menu (preview)">
        <p className="muted">Menu-items worden geladen zodra de zaak is gekoppeld.</p>
        <p>Voorbeeldprijs: {formatEuro(850)}</p>
      </Card>
    </main>
  );
}
