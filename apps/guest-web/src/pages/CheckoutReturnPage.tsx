import { useSearch } from "@tanstack/react-router";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { Button, Card, MoneyHero, PageShell } from "@rekentafel/ui-core";
import { usePaymentSession } from "@rekentafel/guest-hooks";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function CheckoutReturnPage() {
  const t = useT();
  const search = useSearch({ from: "/checkout/return" }) as { session?: string };
  const sessionId = search.session ?? "";
  const { data } = usePaymentSession(sessionId, API_BASE);

  const settlement = data?.settlement as { remaining_cents?: number } | undefined;
  const paid = settlement?.remaining_cents === 0;

  return (
    <PageShell
      title={paid ? t("guest.checkout.thanks") : t("guest.checkout.received")}
      subtitle={paid ? t("guest.checkout.paid") : t("guest.checkout.processing")}
      headerExtra={<LanguageSwitcher />}
      footer={
        sessionId ? (
          <Button onClick={() => { window.location.href = `/session/${sessionId}`; }}>
            {t("guest.checkout.back")}
          </Button>
        ) : undefined
      }
    >
      <Card className="success-card">
        <div className="success-icon" aria-hidden>{paid ? "✓" : "⏳"}</div>
        {paid ? (
          <>
            <p style={{ fontSize: "1.0625rem", margin: "0 0 1rem" }}>{t("guest.checkout.successBody")}</p>
            <MoneyHero label={t("guest.bill.remaining")} amountCents={0} />
          </>
        ) : (
          <>
            <p style={{ margin: "0 0 1rem" }}>{t("guest.checkout.pendingBody")}</p>
            {settlement && (
              <MoneyHero
                label={t("guest.bill.remaining")}
                amountCents={settlement.remaining_cents ?? 0}
              />
            )}
          </>
        )}
      </Card>
    </PageShell>
  );
}
