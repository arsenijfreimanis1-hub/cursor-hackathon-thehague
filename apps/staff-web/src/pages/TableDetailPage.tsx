import { useState } from "react";
import {
  useActivatePayment,
  useAddBillLine,
  useCloseTable,
  useOpenSession,
  useTableBill,
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
  const { data: billData, refetch } = useTableBill(tableId, accessToken, API_BASE);
  const openSession = useOpenSession(accessToken, API_BASE);
  const addLine = useAddBillLine(accessToken, API_BASE);
  const activate = useActivatePayment(accessToken, API_BASE);
  const closeTable = useCloseTable(accessToken, API_BASE);

  const [name, setName] = useState("");
  const [qty, setQty] = useState(1);
  const [price, setPrice] = useState("");
  const [vat, setVat] = useState<900 | 2100>(900);
  const [activation, setActivation] = useState<{
    join_pin: string;
    payment_session_id: string;
    guest_url: string;
  } | null>(null);

  const sessionState = table.table.session_state;
  const diningSessionId = table.dining_session?.dining_session_id;
  const bill = billData?.bill as {
    bill_id: string;
    bill_grand_total_cents: number;
    lines: { name: string; line_total_inc_vat_cents: number }[];
  } | null;

  return (
    <main className="staff-layout">
      <header className="staff-header">
        <div>
          <Button variant="secondary" onClick={onBack}>← Terug</Button>
          <h1>Tafel {table.table.table_code}</h1>
          <p className="muted">Status: {sessionState}</p>
        </div>
      </header>

      <div className="detail-grid">
        <Card title="QR-code">
          {table.table.qr_url && (
            <QrDisplay url={table.table.qr_url} label={table.table.table_code} />
          )}
        </Card>

        <Card title="Sessie">
          {sessionState === "EMPTY" && (
            <Button
              onClick={() => openSession.mutate({ tableId, partySize: 4 })}
              disabled={openSession.isPending}
            >
              Open tafel
            </Button>
          )}
          {sessionState !== "EMPTY" && diningSessionId && (
            <Button
              variant="secondary"
              onClick={() =>
                closeTable.mutate({ tableId, diningSessionId, reason: "Normal close" })
              }
            >
              Sluit tafel
            </Button>
          )}
        </Card>

        {(sessionState === "SEATED" || sessionState === "PAYMENT_ACTIVE") && (
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
              <Button type="submit" disabled={addLine.isPending}>Toevoegen</Button>
            </form>

            {bill && (
              <ul className="bill-lines">
                {bill.lines.map((line, i) => (
                  <li key={i}>{line.name} — {formatEuro(line.line_total_inc_vat_cents)}</li>
                ))}
              </ul>
            )}
            <p><strong>Totaal: {formatEuro(bill?.bill_grand_total_cents ?? 0)}</strong></p>
          </Card>
        )}

        {sessionState === "SEATED" && (
          <Card title="Betaling activeren">
            <p className="muted">Gasten kunnen pas deelnemen na activatie.</p>
            <Button
              disabled={activate.isPending || (bill?.bill_grand_total_cents ?? 0) <= 0}
              onClick={() =>
                activate.mutate(
                  { tableId },
                  { onSuccess: (result) => setActivation(result) },
                )
              }
            >
              Activeer betaling
            </Button>
            {activation && (
              <div className="activation-info">
                <p><strong>Pincode: {activation.join_pin}</strong></p>
                <p className="muted">Deel deze code met gasten</p>
              </div>
            )}
          </Card>
        )}

        {(sessionState === "PAYMENT_ACTIVE" || table.join_pin) && (
          <Card title="Betaling actief">
            <p><strong>Pincode: {table.join_pin ?? activation?.join_pin ?? "—"}</strong></p>
            <p className="muted">Gasten scannen QR → voeren pincode in</p>
          </Card>
        )}
      </div>
    </main>
  );
}
