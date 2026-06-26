import { useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useTableLanding, TableLookupError } from "@rekentafel/guest-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { Badge, Button, Card, formatEuro, PageShell } from "@rekentafel/ui-core";
import { API_BASE } from "../config";
import { CallWaiterButton } from "../components/CallWaiterButton";

type MenuCategory = {
  category_id: string;
  name: string;
  items: {
    item_id: string;
    name: string;
    description: string | null;
    price_inc_vat_cents: number;
  }[];
};

export function TableLandingPage() {
  const t = useT();
  const { restaurantSlug, tableCode } = useParams({ from: "/t/$restaurantSlug/$tableCode" });
  const { data, isLoading, error } = useTableLanding({
    restaurantSlug,
    tableCode,
    baseUrl: API_BASE,
  });
  const [waiterCalled, setWaiterCalled] = useState(false);

  if (isLoading) {
    return (
      <PageShell title={t("guest.welcome.title")} subtitle={t("common.loading")} headerExtra={<LanguageSwitcher />}>
        <Card flat><p className="muted">{t("common.loading")}</p></Card>
      </PageShell>
    );
  }

  if (error || !data) {
    const unreachable =
      error instanceof TableLookupError ? error.code === "UNREACHABLE" : true;
    return (
      <PageShell
        title={unreachable ? t("guest.table.apiDown") : t("guest.table.notFound")}
        headerExtra={<LanguageSwitcher />}
      >
        <Card>
          <p>{unreachable ? t("guest.table.apiDownBody") : t("guest.table.notFoundBody")}</p>
          <code className="rt-network-banner__url">{API_BASE}/t/{restaurantSlug}/{tableCode}</code>
          {unreachable ? (
            <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.8125rem" }}>
              {t("guest.table.apiDownHint")}
            </p>
          ) : null}
          <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
            {t("common.retry")}
          </Button>
        </Card>
      </PageShell>
    );
  }

  const table = data.table as { table_code: string; session_state: string };
  const restaurant = data.restaurant as { name: string };
  const hint = data.payment_session_hint as { payment_session_id: string } | null;
  const menu = data.menu as { categories: MenuCategory[] };
  const paymentActive = table.session_state === "READY_TO_PAY" && hint;
  const stateLabel = t(`state.${table.session_state}`);

  return (
    <PageShell
      title={restaurant.name}
      subtitle={t("guest.table.welcome")}
      headerExtra={<LanguageSwitcher />}
      footer={
        <div className="landing-footer-actions">
          {paymentActive ? (
            <Button onClick={() => { window.location.href = `/session/${hint.payment_session_id}/join`; }}>
              {t("guest.table.joinBill")}
            </Button>
          ) : null}
          <CallWaiterButton sent={waiterCalled} onCall={() => setWaiterCalled(true)} />
        </div>
      }
    >
      <div className="landing-hero">
        <p className="landing-hero__venue">{restaurant.name}</p>
        <span className="landing-hero__table">
          {t("guest.welcome.scanQr")} · {table.table_code}
        </span>
      </div>

      <Card title={t("guest.table.status")}>
        <Badge variant={paymentActive ? "success" : "muted"} dot>
          {stateLabel}
        </Badge>
        <p className="muted" style={{ marginTop: "1rem" }}>
          {paymentActive ? t("guest.table.paymentReady") : t("guest.table.waiting")}
        </p>
      </Card>

      <Card title={t("guest.table.serviceTitle")} subtitle={t("guest.table.serviceSubtitle")}>
        <CallWaiterButton sent={waiterCalled} onCall={() => setWaiterCalled(true)} />
      </Card>

      {menu.categories.map((category) => (
        <Card key={category.category_id} title={category.name} subtitle={t("guest.table.menuBrowse")}>
          {category.items.map((item) => (
            <div key={item.item_id} className="landing-menu-preview">
              <div>
                <span>{item.name}</span>
                {item.description ? (
                  <p className="muted" style={{ margin: "0.2rem 0 0", fontSize: "0.8125rem" }}>
                    {item.description}
                  </p>
                ) : null}
              </div>
              <strong>{formatEuro(item.price_inc_vat_cents)}</strong>
            </div>
          ))}
        </Card>
      ))}
    </PageShell>
  );
}
