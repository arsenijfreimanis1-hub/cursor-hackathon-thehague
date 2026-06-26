import { useStaffTables, useServiceSignals, useAckSignal, SESSION_STATE_LABELS, SIGNAL_TYPE_LABELS } from "@rekentafel/staff-hooks";
import type { StaffTable } from "@rekentafel/staff-hooks";
import { Button, Card, formatEuro } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

const stateColors: Record<string, string> = {
  DORMANT: "#e5e7eb",
  SEATED: "#fef3c7",
  ORDERED: "#fde68a",
  READY_TO_PAY: "#dbeafe",
  PAID: "#bbf7d0",
  CLOSED: "#d1fae5",
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

  const openSignals = signals as
    | { signal_id: string; table_code: string; signal_type: string }[]
    | undefined;

  return (
    <main className="staff-layout staff-layout--floor">
      <header className="staff-header">
        <div>
          <h1>Vloerplan</h1>
          <p className="muted">Tik op een tafel voor details</p>
        </div>
        <Button variant="secondary" onClick={onLogout}>
          Uitloggen
        </Button>
      </header>

      {openSignals?.length ? (
        <div className="signals-inbox">
          <Card title="Service signalen">
          {openSignals.map((s) => (
            <div key={s.signal_id} className="signal-row">
              <span>
                Tafel {s.table_code}: {SIGNAL_TYPE_LABELS[s.signal_type] ?? s.signal_type}
              </span>
              <Button variant="secondary" onClick={() => ack.mutate(s.signal_id)}>
                Bevestig
              </Button>
            </div>
          ))}
          </Card>
        </div>
      ) : null}

      {isLoading && <p>Laden…</p>}
      {error && (
        <Card title="Geen tafels">
          <p>
            Configureer <code>DEV_VENUE_ID</code> en seed data, of start de API.
          </p>
        </Card>
      )}

      <div className="floor-plan">
        {(tables ?? []).map((row) => {
          const state = row.table.session_state;
          const label = SESSION_STATE_LABELS[state] ?? state;
          return (
            <button
              key={row.table.table_id}
              type="button"
              className="floor-table"
              style={{
                left: `${row.table.pos_x ?? 50}%`,
                top: `${row.table.pos_y ?? 50}%`,
                background: stateColors[state] ?? "#fff",
              }}
              onClick={() => onSelectTable(row)}
            >
              <span className="floor-table__code">{row.table.table_code}</span>
              <span className="floor-table__state">{label}</span>
              {(row.bill_total_cents ?? 0) > 0 && (
                <span className="floor-table__total">{formatEuro(row.bill_total_cents ?? 0)}</span>
              )}
              {(row.pending_signals ?? 0) > 0 && (
                <span className="floor-table__badge">{row.pending_signals}</span>
              )}
            </button>
          );
        })}
      </div>

      <ul className="floor-legend">
        {Object.entries(SESSION_STATE_LABELS).map(([key, label]) => (
          <li key={key}>
            <span className="legend-swatch" style={{ background: stateColors[key] }} />
            {label}
          </li>
        ))}
      </ul>
    </main>
  );
}
