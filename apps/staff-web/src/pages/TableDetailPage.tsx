import { useState } from "react";
import {
  useActivatePayment,
  useAddBillLine,
  useCloseTable,
  useOpenSession,
  useTableBill,
  useUpdateTableState,
  SESSION_STATE_LABELS,
} from "@rekentafel/staff-hooks";
import type { StaffTable } from "@rekentafel/staff-hooks";
import { Button, Card, QrDisplay, formatEuro } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function TableDetailPage({
  table,
  accessToken,
  onBack,
}: {
  table: StaffTable;
  accessToken: string;
  onBack: () => void;
}) {
  const tableId = table.table.table_id;
  const sessionState = table.table.session_state;
  const pollBill = sessionState === "READY_TO_PAY";
  const { data: billData, refetch } = useTableBill(tableId, accessToken, API_BASE, pollBill);
  const openSession = useOpenSession(accessToken, API_BASE);
  const updateState = useUpdateTableState(accessToken, API_BASE);
  const addLine = useAddBillLine(accessToken, API_BASE);
  const activate = useActivatePayment(accessToken, API_BASE);
  const closeTable = useCloseTable(accessToken, API_BASE);

  const [partySize, setPartySize] = useState(table.dining_session?.party_size ?? 4);
  const [name, setName] = useState("");
  const [qty, setQty] = useState(1);
  const [price, setPrice] = useState("");
  const [vat, setVat] = useState<900 | 2100>(900);
  const [activation, setActivation] = useState<{
    join_pin: string;
    payment_session_id: string;
    guest_url: string;
  } | null>(null);

  const diningSessionId = table.dining_session?.dining_session_id;
  const currentState = (billData?.state as string | undefined) ?? sessionState;
  const bill = billData?.bill as {
    bill_id: string;
    bill_grand_total_cents: number;
    confirmed_paid_cents?: number;
    lines: { name: string; line_total_inc_vat_cents: number }[];
  } | null;
  const allocationSummary = (billData?.allocation_summary ??
    table.allocation_summary) as
    | { name: string; claimed_by: string; line_total_inc_vat_cents: number; unclaimed_cents: number }[]
    | undefined;

  const canAddLines = ["SEATED", "ORDERED", "READY_TO_PAY"].includes(currentState);
  const canActivate = currentState === "ORDERED" || currentState === "SEATED";
  const canClose = currentState === "PAID" || currentState === "READY_TO_PAY" || currentState === "ORDERED";

  return (
    <main className="staff-layout">
      <header className="staff-header">
        <div>
          <Button variant="secondary" onClick={onBack}>
            ← Terug
          </Button>
          <h1>Tafel {table.table.table_code}</h1>
          <p className="muted">
            Status: {SESSION_STATE_LABELS[currentState] ?? currentState}
            {table.table.seats ? ` · ${table.table.seats} stoelen` : ""}
          </p>
        </div>
      </header>

      <div className="detail-grid">
        <Card title="Sessie">
          {currentState === "DORMANT" && (
            <div className="stack">
              <label>
                Aantal gasten
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={partySize}
                  onChange={(e) => setPartySize(Number(e.target.value))}
                />
              </label>
              <Button
                onClick={() => openSession.mutate({ tableId, partySize })}
                disabled={openSession.isPending}
              >
                Tafel openen
              </Button>
            </div>
          )}
          {currentState !== "DORMANT" && diningSessionId && (
            <div className="stack">
              <label>
                Aantal gasten
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={partySize}
                  onChange={(e) => setPartySize(Number(e.target.value))}
                  onBlur={() =>
                    updateState.mutate({ tableId, partySize })
                  }
                />
              </label>
              {canClose && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    closeTable.mutate({ tableId, diningSessionId, reason: "Normal close" })
                  }
                >
                  Tafel sluiten
                </Button>
              )}
            </div>
          )}
        </Card>

        <Card title="QR-code voor gasten">
          {table.table.qr_url && (
            <>
              <QrDisplay url={table.table.qr_url} label={table.table.table_code} />
              <p className="muted">Gasten scannen — geen app download nodig</p>
            </>
          )}
        </Card>

        {canAddLines && (
          <Card title="Rekening invoeren">
            <form
              className="stack"
              onSubmit={(e) => {
                e.preventDefault();
                const cents = Math.round(parseFloat(price.replace(",", ".")) * 100);
                addLine.mutate(
                  {
                    tableId,
                    name,
                    qty,
                    unitPriceIncVatCents: cents,
                    vatRateBps: vat,
                  },
                  {
                    onSuccess: () => {
                      setName("");
                      setPrice("");
                      refetch();
                    },
                  },
                );
              }}
            >
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Gerecht"
                required
              />
              <div className="row">
                <input
                  type="number"
                  value={qty}
                  onChange={(e) => setQty(Number(e.target.value))}
                  min={1}
                  style={{ width: 60 }}
                />
                <input
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="Prijs €"
                  required
                />
                <select value={vat} onChange={(e) => setVat(Number(e.target.value) as 900 | 2100)}>
                  <option value={900}>9% BTW</option>
                  <option value={2100}>21% BTW</option>
                </select>
              </div>
              <Button type="submit" disabled={addLine.isPending}>
                Toevoegen
              </Button>
            </form>

            {bill && (
              <ul className="bill-lines">
                {bill.lines.map((line, i) => (
                  <li key={i}>
                    {line.name} — {formatEuro(line.line_total_inc_vat_cents)}
                  </li>
                ))}
              </ul>
            )}
            <p>
              <strong>Totaal: {formatEuro(bill?.bill_grand_total_cents ?? 0)}</strong>
            </p>
          </Card>
        )}

        {canActivate && currentState !== "READY_TO_PAY" && (
          <Card title="Betaling activeren">
            <p className="muted">Gasten kunnen pas deelnemen na activatie.</p>
            <Button
              disabled={activate.isPending || (bill?.bill_grand_total_cents ?? 0) <= 0}
              onClick={() =>
                activate.mutate({ tableId }, { onSuccess: (result) => setActivation(result) })
              }
            >
              Activeer betaling
            </Button>
            {activation && (
              <div className="activation-info">
                <p>
                  <strong>Pincode: {activation.join_pin}</strong>
                </p>
                <p className="muted">Deel deze code met gasten</p>
              </div>
            )}
          </Card>
        )}

        {(currentState === "READY_TO_PAY" || table.join_pin) && (
          <Card title="Betaling actief">
            <p>
              <strong>Pincode: {table.join_pin ?? activation?.join_pin ?? "—"}</strong>
            </p>
            <p className="muted">Gasten scannen QR → voeren pincode in</p>
            {bill?.confirmed_paid_cents ? (
              <p>Betaald: {formatEuro(bill.confirmed_paid_cents)}</p>
            ) : null}
          </Card>
        )}

        {currentState === "READY_TO_PAY" && allocationSummary && allocationSummary.length > 0 && (
          <Card title="Live verdeling">
            <p className="muted">Wie heeft wat geclaimd — ververst elke 2 seconden</p>
            <ul className="split-monitor">
              {allocationSummary.map((line) => (
                <li key={line.name + line.claimed_by} className="split-monitor__row">
                  <div>
                    <strong>{line.name}</strong>
                    <span className="muted"> {formatEuro(line.line_total_inc_vat_cents)}</span>
                  </div>
                  <span
                    className={
                      line.claimed_by === "Vrij" ? "split-monitor__free" : "split-monitor__claimed"
                    }
                  >
                    {line.claimed_by}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {currentState === "PAID" && (
          <Card title="Volledig betaald">
            <p>Rekening is voldaan. Sluit de tafel om plaats te maken voor nieuwe gasten.</p>
          </Card>
        )}
      </div>
    </main>
  );
}
