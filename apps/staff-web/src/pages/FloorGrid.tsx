import { useStaffTables, useServiceSignals, useAckSignal } from "@rekentafel/staff-hooks";
import type { StaffTable } from "@rekentafel/staff-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { Button, Card, formatEuro, Spinner } from "@rekentafel/ui-core";
import { API_BASE } from "../config";

const stateClass: Record<string, string> = {
  DORMANT: "floor-table--dormant",
  SEATED: "floor-table--seated",
  ORDERED: "floor-table--ordered",
  READY_TO_PAY: "floor-table--ready",
  PAID: "floor-table--paid",
  CLOSED: "floor-table--closed",
};

const stateSwatch: Record<string, string> = {
  DORMANT: "#d6d3d1",
  SEATED: "#fcd34d",
  ORDERED: "#fb923c",
  READY_TO_PAY: "#60a5fa",
  PAID: "#34d399",
  CLOSED: "#6ee7b7",
};

const STATE_KEYS = ["DORMANT", "SEATED", "ORDERED", "READY_TO_PAY", "PAID", "CLOSED"] as const;

export function FloorGrid({
  accessToken,
  onSelectTable,
  onOpenQr,
  onLogout,
}: {
  accessToken: string;
  onSelectTable: (table: StaffTable) => void;
  onOpenQr: () => void;
  onLogout: () => void;
}) {
  const t = useT();
  const { data: tables, isLoading, error } = useStaffTables(accessToken, API_BASE);
  const { data: signals } = useServiceSignals(accessToken, API_BASE);
  const ack = useAckSignal(accessToken, API_BASE);

  const openSignals = signals as
    | { signal_id: string; table_code: string; signal_type: string }[]
    | undefined;

  return (
    <main className="staff-layout staff-layout--floor">
      <header className="staff-topbar">
        <div className="staff-topbar__brand">
          <span className="staff-topbar__logo">{t("staff.floor.brand")}</span>
          <h1>{t("staff.floor.title")}</h1>
          <p>{(tables ?? []).length} {t("staff.floor.tables")}</p>
        </div>
        <div className="staff-topbar__actions">
          <LanguageSwitcher />
          <Button variant="ghost" size="sm" onClick={onOpenQr}>
            {t("staff.floor.qr")}
          </Button>
          <Button variant="secondary" size="sm" onClick={onLogout}>
            {t("staff.floor.logout")}
          </Button>
        </div>
      </header>

      {openSignals?.length ? (
        <div className="signals-inbox">
          <Card
            title={t("staff.floor.signals")}
            subtitle={`${openSignals.length} ${openSignals.length > 1 ? t("staff.floor.signalsOpenPlural") : t("staff.floor.signalsOpen")}`}
          >
            {openSignals.map((s) => (
              <div key={s.signal_id} className="signal-row">
                <span className="signal-row__text">
                  <span className="signal-row__table">{s.table_code}</span>
                  {" · "}
                  {t(`signal.${s.signal_type}`)}
                </span>
                <Button variant="secondary" size="sm" onClick={() => ack.mutate(s.signal_id)}>
                  {t("common.ok")}
                </Button>
              </div>
            ))}
          </Card>
        </div>
      ) : null}

      {isLoading && <Spinner />}
      {error && (
        <Card title={t("staff.floor.noConnection")}>
          <p className="muted">{t("staff.floor.noConnectionBody")}</p>
          <code className="rt-network-banner__url">{API_BASE}</code>
          <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.8125rem" }}>
            {t("staff.floor.noConnectionHint")}
          </p>
          <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
            {t("common.retry")}
          </Button>
        </Card>
      )}

      <div className="floor-plan-wrap">
        <div className="floor-plan">
          {(tables ?? []).map((row) => {
            const state = row.table.session_state;
            const label = t(`state.${state}`);
            return (
              <button
                key={row.table.table_id}
                type="button"
                className={`floor-table ${stateClass[state] ?? ""}`}
                style={{
                  left: `${row.table.pos_x ?? 50}%`,
                  top: `${row.table.pos_y ?? 50}%`,
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
      </div>

      <ul className="floor-legend">
        {STATE_KEYS.map((key) => (
          <li key={key}>
            <span className="legend-swatch" style={{ background: stateSwatch[key] }} />
            {t(`state.${key}`)}
          </li>
        ))}
      </ul>
    </main>
  );
}
