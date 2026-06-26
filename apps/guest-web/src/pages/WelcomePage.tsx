import { Link } from "@tanstack/react-router";
import { LanguageSwitcher, NetworkBanner, useT } from "@rekentafel/i18n";
import { Card, PageShell } from "@rekentafel/ui-core";

const LAN_HOST = import.meta.env.VITE_LAN_HOST;

export function WelcomePage() {
  const t = useT();

  return (
    <PageShell
      title={t("guest.welcome.title")}
      subtitle={t("guest.welcome.subtitle")}
      headerExtra={<LanguageSwitcher />}
    >
      <NetworkBanner port={5173} variant="guest" lanHost={LAN_HOST} />

      <div className="landing-hero">
        <p className="landing-hero__venue">{t("guest.welcome.venue")}</p>
        <span className="landing-hero__table">{t("guest.welcome.scanQr")}</span>
      </div>

      <Card title={t("guest.welcome.howTitle")}>
        <ol className="welcome-steps">
          <li>{t("guest.welcome.step1")}</li>
          <li>{t("guest.welcome.step2")}</li>
          <li>{t("guest.welcome.step3")}</li>
          <li>{t("guest.welcome.step4")}</li>
        </ol>
      </Card>

      <Card title={t("guest.welcome.demoTitle")} subtitle={t("guest.welcome.demoSubtitle")}>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          {t("guest.welcome.demoBody")}
        </p>
        <Link
          to="/t/$restaurantSlug/$tableCode"
          params={{ restaurantSlug: "demo-bistro", tableCode: "T01" }}
          className="welcome-demo-link"
        >
          {t("guest.welcome.demoLink")}
        </Link>
      </Card>
    </PageShell>
  );
}
