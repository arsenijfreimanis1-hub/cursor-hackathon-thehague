import { useParams } from "@tanstack/react-router";
import { useTableLanding } from "@rekentafel/guest-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { Badge, Button, Card, formatEuro, PageShell } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function TableLandingPage() {
  const t = useT();
  const { restaurantSlug, tableCode } = useParams({ from: "/t/$restaurantSlug/$tableCode" });
  const { data, isLoading, error } = useTableLanding({
    restaurantSlug,
    tableCode,
    baseUrl: API_BASE,
  });

  if (isLoading) {
    return (
      <PageShell title={t("guest.welcome.title")} subtitle={t("common.loading")} headerExtra={<LanguageSwitcher />}>
        <Card flat><p className="muted">{t("common.loading")}</p></Card>
      </PageShell>
    );
  }

  if (error || !data) {
    return (
      <PageShell title={t("guest.table.notFound")} headerExtra={<LanguageSwitcher />}>
        <Card><p>{t("guest.table.notFoundBody")}</p></Card>
      </PageShell>
    );
  }

  const table = data.table as { table_code: string; session_state: string };
  const restaurant = data.restaurant as { name: string };
  const hint = data.payment_session_hint as { payment_session_id: string } | null;
  const paymentActive = table.session_state === "READY_TO_PAY" && hint;
  const stateLabel = t(`state.${table.session_state}`);

  return (
    <PageShell
      title={restaurant.name}
      subtitle={t("guest.table.welcome")}
      headerExtra={<LanguageSwitcher />}
      footer={
        paymentActive ? (
          <Button onClick={() => { window.location.href = `/session/${hint.payment_session_id}/join`; }}>
            {t("guest.table.joinBill")}
          </Button>
        ) : undefined
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

      <Card title={t("guest.table.menuTitle")} subtitle={t("guest.table.menuSubtitle")}>
        <div className="landing-menu-preview">
          <span>Huisgemaakte soep / Soup</span>
          <strong>{formatEuro(650)}</strong>
        </div>
        <div className="landing-menu-preview">
          <span>Verse pasta / Pasta</span>
          <strong>{formatEuro(1450)}</strong>
        </div>
        <div className="landing-menu-preview">
          <span>Tiramisu</span>
          <strong>{formatEuro(750)}</strong>
        </div>
      </Card>
    </PageShell>
  );
}
