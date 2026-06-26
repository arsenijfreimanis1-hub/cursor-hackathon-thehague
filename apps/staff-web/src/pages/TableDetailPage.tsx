import { useState } from "react";
import {
  useActivatePayment,
  useAddBillLine,
  useCloseTable,
  useOpenSession,
  useRestaurantMenu,
  useTableBill,
  useUpdateTableState,
} from "@rekentafel/staff-hooks";
import type { StaffTable } from "@rekentafel/staff-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import {
  Badge,
  Button,
  Card,
  Field,
  formatEuro,
  PinDisplay,
  QrDisplay,
} from "@rekentafel/ui-core";
import { API_BASE } from "../config";

export function TableDetailPage({
  table,
  accessToken,
  onBack,
}: {
  table: StaffTable;
  accessToken: string;
  onBack: () => void;
}) {
  const t = useT();
  const tableId = table.table.table_id;
  const sessionState = table.table.session_state;
  const pollBill = sessionState === "READY_TO_PAY";
  const { data: billData, refetch } = useTableBill(tableId, accessToken, API_BASE, pollBill);
  const openSession = useOpenSession(accessToken, API_BASE);
  const updateState = useUpdateTableState(accessToken, API_BASE);
  const addLine = useAddBillLine(accessToken, API_BASE);
  const activate = useActivatePayment(accessToken, API_BASE);
  const closeTable = useCloseTable(accessToken, API_BASE);
  const restaurantSlug = table.table.restaurant_slug ?? "demo-bistro";
  const { data: menuData } = useRestaurantMenu(restaurantSlug, API_BASE);

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
  const activePin = table.join_pin ?? activation?.join_pin;

  const claimLabel = (claimedBy: string) =>
    claimedBy === "Vrij" ? t("split.free") : claimedBy;

  return (
    <main className="staff-layout">
      <div className="detail-back" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Button variant="ghost" size="sm" onClick={onBack}>
          {t("staff.table.back")}
        </Button>
        <LanguageSwitcher />
      </div>

      <header className="detail-header">
        <h1>
          {table.table.table_code}
        </h1>
        <p>
          <Badge
            variant={currentState === "READY_TO_PAY" ? "warning" : currentState === "PAID" ? "success" : "muted"}
            dot
          >
            {t(`state.${currentState}`)}
          </Badge>
          {table.table.seats ? ` · ${table.table.seats} ${t("common.seats")}` : ""}
        </p>
      </header>

      <div className="detail-grid">
        <Card title={t("staff.table.partySize")}>
          {currentState === "DORMANT" && (
            <div className="stack">
              <Field label={t("staff.table.partySize")}>
                <input
                  className="rt-input"
                  type="number"
                  min={1}
                  max={20}
                  value={partySize}
                  onChange={(e) => setPartySize(Number(e.target.value))}
                />
              </Field>
              <Button
                onClick={() => openSession.mutate({ tableId, partySize })}
                disabled={openSession.isPending}
              >
                {t("staff.table.guests")}
              </Button>
            </div>
          )}
          {currentState !== "DORMANT" && diningSessionId && (
            <div className="stack">
              <Field label={t("staff.table.partySize")}>
                <input
                  className="rt-input"
                  type="number"
                  min={1}
                  max={20}
                  value={partySize}
                  onChange={(e) => setPartySize(Number(e.target.value))}
                  onBlur={() => updateState.mutate({ tableId, partySize })}
                />
              </Field>
              {canClose && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    closeTable.mutate({ tableId, diningSessionId, reason: "Normal close" })
                  }
                >
                  {t("staff.table.close")}
                </Button>
              )}
            </div>
          )}
        </Card>

        {table.table.qr_url && (
          <Card title={t("staff.table.qrTitle")} subtitle={t("staff.table.qrSubtitle")}>
            <QrDisplay url={table.table.qr_url} label={table.table.table_code} />
          </Card>
        )}

        {canAddLines && menuData?.categories.length ? (
          <Card title={t("staff.table.menuTitle")} subtitle={t("staff.table.menuSubtitle")}>
            {menuData.categories.map((category) => (
              <div key={category.category_id} className="staff-menu-category">
                <h3 className="staff-menu-category__title">{category.name}</h3>
                <div className="staff-menu-grid">
                  {category.items.map((item) => (
                    <Button
                      key={item.item_id}
                      variant="secondary"
                      size="sm"
                      className="staff-menu-item"
                      onClick={() =>
                        addLine.mutate(
                          {
                            tableId,
                            name: item.name,
                            qty: 1,
                            unitPriceIncVatCents: item.price_inc_vat_cents,
                            vatRateBps: item.vat_rate_bps,
                          },
                          { onSuccess: () => refetch() },
                        )
                      }
                    >
                      <span>{item.name}</span>
                      <span>{formatEuro(item.price_inc_vat_cents)}</span>
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </Card>
        ) : null}

        {canAddLines && (
          <Card title={t("staff.table.billTitle")} subtitle={t("staff.table.billSubtitle")}>
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
              <Field label={t("staff.table.dish")}>
                <input
                  className="rt-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("staff.table.dishPlaceholder")}
                  required
                />
              </Field>
              <div className="row">
                <input
                  className="rt-input"
                  type="number"
                  value={qty}
                  onChange={(e) => setQty(Number(e.target.value))}
                  min={1}
                  style={{ maxWidth: "4rem" }}
                  aria-label="Qty"
                />
                <input
                  className="rt-input"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder={t("staff.table.pricePlaceholder")}
                  required
                />
                <select
                  className="rt-input"
                  value={vat}
                  onChange={(e) => setVat(Number(e.target.value) as 900 | 2100)}
                  style={{ maxWidth: "5rem" }}
                >
                  <option value={900}>9%</option>
                  <option value={2100}>21%</option>
                </select>
              </div>
              <Button type="submit" disabled={addLine.isPending}>
                {t("staff.table.add")}
              </Button>
            </form>

            {bill && bill.lines.length > 0 && (
              <ul className="bill-lines">
                {bill.lines.map((line, i) => (
                  <li key={i}>
                    <span>{line.name}</span>
                    <span>{formatEuro(line.line_total_inc_vat_cents)}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="total-line">
              {t("staff.table.total")} {formatEuro(bill?.bill_grand_total_cents ?? 0)}
            </p>
          </Card>
        )}

        {canActivate && (
          <Card title={t("staff.table.payTitle")} subtitle={t("staff.table.paySubtitle")}>
            <Button
              disabled={activate.isPending || (bill?.bill_grand_total_cents ?? 0) <= 0}
              onClick={() =>
                activate.mutate({ tableId }, { onSuccess: (result) => setActivation(result) })
              }
            >
              {t("staff.table.activate")}
            </Button>
            {activation && (
              <div className="activation-info">
                <p className="muted" style={{ margin: "0 0 0.5rem" }}>
                  {t("staff.table.sharePin")}
                </p>
                <PinDisplay pin={activation.join_pin} />
              </div>
            )}
          </Card>
        )}

        {(currentState === "READY_TO_PAY" || activePin) && (
          <Card title={t("staff.table.liveTitle")} subtitle={t("staff.table.liveSubtitle")}>
            {activePin && <PinDisplay pin={activePin} />}
            {bill?.confirmed_paid_cents ? (
              <p style={{ textAlign: "center", marginTop: "1rem" }}>
                {t("staff.table.paidAmount")} <strong>{formatEuro(bill.confirmed_paid_cents)}</strong>
              </p>
            ) : null}
          </Card>
        )}

        {currentState === "READY_TO_PAY" && allocationSummary && allocationSummary.length > 0 && (
          <Card title={t("staff.table.splitTitle")} subtitle={t("staff.table.splitSubtitle")}>
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
                    {claimLabel(line.claimed_by)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {currentState === "PAID" && (
          <Card title={t("staff.table.paidTitle")}>
            <p style={{ margin: 0 }}>{t("staff.table.paidBody")}</p>
          </Card>
        )}
      </div>
    </main>
  );
}
