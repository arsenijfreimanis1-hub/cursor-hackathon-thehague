import { useStaffTables, useServiceSignals, useAckSignal } from "@rekentafel/staff-hooks";
import type { StaffTable } from "@rekentafel/staff-hooks";
import { Button, Card, QrDisplay, formatEuro } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

const stateColors: Record<string, string> = {
  EMPTY: "var(--color-empty, #e5e7eb)",
  SEATED: "var(--color-seated, #fef3c7)",
  PAYMENT_ACTIVE: "var(--color-payment, #dbeafe)",
  CLOSED: "var(--color-closed, #d1fae5)",
};

export function FloorGrid({
  accessToken,
  onSelectTable,
  onLogout,
}: {
  accessToken: string;
  onSelectTable: (table: StaffTable) => void;
  onLogout: () => void;
}) {
  const { data: tables, isLoading, error } = useStaffTables(accessToken, API_BASE);
  const { data: signals } = useServiceSignals(accessToken, API_BASE);
  const ack = useAckSignal(accessToken, API_BASE);

  return (
    <main className="staff-layout">
      <header className="staff-header">
        <div>
          <h1>Vloerplan</h1>
          <p className="muted">QR-codes per tafel — tik voor details</p>
        </div>
        <Button variant="secondary" onClick={onLogout}>
          Uitloggen
        </Button>
      </header>

      {(signals as { signal_id: string; table_code: string; signal_type: string }[] | undefined)?.length ? (
        <Card title="Service signalen">
          {(signals as { signal_id: string; table_code: string; signal_type: string }[]).map((s) => (
            <div key={s.signal_id} className="signal-row">
              <span>Tafel {s.table_code}: {s.signal_type}</span>
              <Button variant="secondary" onClick={() => ack.mutate(s.signal_id)}>
                Bevestig
              </Button>
            </div>
          ))}
        </Card>
      ) : null}

      {isLoading && <p>Laden…</p>}
      {error && (
        <Card title="Geen tafels">
          <p>
            Configureer <code>DEV_VENUE_ID</code> en seed data, of gebruik de mock server.
          </p>
        </Card>
      )}

      <div className="floor-grid">
        {(tables ?? []).map((row) => (
          <button
            key={row.table.table_id}
            type="button"
            className="table-card-btn"
            style={{ background: stateColors[row.table.session_state] ?? "#fff" }}
            onClick={() => onSelectTable(row)}
          >
            <Card>
              <p className="table-card__code">{row.table.table_code}</p>
              <p className="muted">{row.table.session_state}</p>
              {(row.bill_total_cents ?? 0) > 0 && (
                <p>{formatEuro(row.bill_total_cents ?? 0)}</p>
              )}
              {row.join_pin && <p className="pin">PIN: {row.join_pin}</p>}
              {row.table.qr_url ? (
                <QrDisplay url={row.table.qr_url} label={row.table.table_code} />
              ) : (
                <p>Geen QR URL</p>
              )}
            </Card>
          </button>
        ))}
      </div>
    </main>
  );
}
