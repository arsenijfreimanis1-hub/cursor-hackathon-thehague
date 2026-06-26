import { useCallback } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import {
  useBillEvents,
  useClaimItem,
  useCombinedCheckout,
  useGuestSession,
  usePaymentSession,
} from "@rekentafel/guest-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import {
  BillItem,
  Button,
  Card,
  Chip,
  formatEuro,
  MoneyHero,
  PageShell,
  ProgressBar,
  Spinner,
} from "@rekentafel/ui-core";
import { useQueryClient } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

type BillLine = {
  line_id: string;
  name: string;
  line_total_inc_vat_cents: number;
  splittable: boolean;
};

type Allocation = {
  allocation_id: string;
  participant_name: string;
  line_name: string;
  amount_cents: number;
};

export function BillShellPage() {
  const t = useT();
  const { paymentSessionId } = useParams({ from: "/session/$paymentSessionId" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { joined } = useGuestSession(paymentSessionId);
  const { data, isLoading, error } = usePaymentSession(paymentSessionId, API_BASE);
  const claim = useClaimItem(API_BASE);
  const checkout = useCombinedCheckout(API_BASE);

  useBillEvents(
    paymentSessionId,
    useCallback(() => {
      queryClient.invalidateQueries({ queryKey: ["payment-session", paymentSessionId] });
    }, [queryClient, paymentSessionId]),
    API_BASE,
  );

  if (!joined) {
    navigate({ to: "/session/$paymentSessionId/join", params: { paymentSessionId } });
    return null;
  }

  if (isLoading) {
    return (
      <PageShell title={t("guest.bill.title")} subtitle={t("guest.bill.live")} headerExtra={<LanguageSwitcher />}>
        <Spinner />
      </PageShell>
    );
  }

  if (error || !data) {
    return (
      <PageShell title={t("guest.bill.title")} headerExtra={<LanguageSwitcher />}>
        <Card><p>{t("guest.bill.loadError")}</p></Card>
      </PageShell>
    );
  }

  const bill = data.bill as {
    bill_id: string;
    bill_grand_total_cents: number;
    confirmed_paid_cents: number;
    lines: BillLine[];
  };
  const settlement = data.settlement as {
    remaining_cents: number;
    unclaimed_cents: number;
    allocated_cents: number;
  };
  const participants = data.participants as { participant_id: string; display_name: string }[];
  const allocations = (data.allocations ?? []) as Allocation[];
  const billVersion = data.bill_version as number;
  const paidPercent =
    bill.bill_grand_total_cents > 0
      ? Math.round((bill.confirmed_paid_cents / bill.bill_grand_total_cents) * 100)
      : 0;
  const participantLabel =
    participants.length === 1 ? t("guest.bill.participants") : t("guest.bill.participantsPlural");

  return (
    <PageShell
      title={t("guest.bill.title")}
      subtitle={`${participants.length} ${participantLabel}`}
      headerExtra={<LanguageSwitcher />}
      footer={
        <Button
          disabled={checkout.isPending || settlement.remaining_cents <= 0}
          onClick={() =>
            checkout.mutate(
              {
                paymentSessionId,
                redirectUrl: `${window.location.origin}/checkout/return?session=${paymentSessionId}`,
              },
              {
                onSuccess: (result) => {
                  if (result.mollie_checkout_url) {
                    window.location.href = result.mollie_checkout_url;
                  }
                },
              },
            )
          }
        >
          {checkout.isPending
            ? t("guest.bill.checkoutBusy")
            : settlement.remaining_cents <= 0
              ? t("guest.bill.checkoutPaid")
              : t("guest.bill.checkoutPay", { amount: formatEuro(settlement.remaining_cents) })}
        </Button>
      }
    >
      <Card flat>
        <MoneyHero
          label={t("guest.bill.remaining")}
          amountCents={settlement.remaining_cents}
          sub={`${t("guest.bill.total")} ${formatEuro(bill.bill_grand_total_cents)}`}
        />
        <ProgressBar percent={paidPercent} />
        <div className="bill-stats">
          <div>
            <span className="bill-stat__value">{formatEuro(bill.confirmed_paid_cents)}</span>
            <span className="bill-stat__label">{t("guest.bill.paid")}</span>
          </div>
          <div>
            <span className="bill-stat__value">{formatEuro(settlement.allocated_cents)}</span>
            <span className="bill-stat__label">{t("guest.bill.claimed")}</span>
          </div>
          <div>
            <span className="bill-stat__value">{formatEuro(settlement.unclaimed_cents)}</span>
            <span className="bill-stat__label">{t("guest.bill.free")}</span>
          </div>
        </div>
      </Card>

      <Card title={t("guest.bill.whoAtTable")}>
        <div className="chip-row">
          {participants.map((p) => (
            <Chip key={p.participant_id} name={p.display_name} />
          ))}
        </div>
      </Card>

      <Card title={t("guest.bill.dishes")} subtitle={t("guest.bill.dishesHint")}>
        {bill.lines.map((line) => {
          const claimed = allocations.filter((a) => a.line_name === line.name);
          const claimedBy = claimed.map((c) => c.participant_name).join(", ");
          return (
            <BillItem
              key={line.line_id}
              name={line.name}
              priceCents={line.line_total_inc_vat_cents}
              meta={
                claimed.length > 0
                  ? t("guest.bill.claimedBy", { name: claimedBy })
                  : line.splittable
                    ? t("guest.bill.stillFree")
                    : undefined
              }
              action={
                claimed.length === 0 && line.splittable ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={claim.isPending}
                    onClick={() =>
                      claim.mutate({
                        paymentSessionId,
                        billLineId: line.line_id,
                        billVersion,
                      })
                    }
                  >
                    {t("guest.bill.claim")}
                  </Button>
                ) : undefined
              }
            />
          );
        })}
      </Card>

      {checkout.error && (
        <Card flat>
          <p className="error">{checkout.error.message}</p>
        </Card>
      )}

      <p className="muted" style={{ fontSize: "0.8125rem", textAlign: "center" }}>
        {t("guest.bill.checkoutHint")}
      </p>
    </PageShell>
  );
}
