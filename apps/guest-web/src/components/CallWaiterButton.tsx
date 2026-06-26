import { useT } from "@rekentafel/i18n";
import { Button } from "@rekentafel/ui-core";

export function CallWaiterButton({
  block = true,
  sent,
  onCall,
}: {
  block?: boolean;
  sent: boolean;
  onCall: () => void;
}) {
  const t = useT();

  return (
    <div className="guest-call-waiter">
      <Button
        variant={sent ? "secondary" : "primary"}
        className={block ? "guest-call-waiter__btn" : undefined}
        onClick={onCall}
        disabled={sent}
      >
        {sent ? t("guest.table.callWaiterSent") : t("guest.table.callWaiter")}
      </Button>
      {sent ? (
        <p className="guest-call-waiter__hint muted">{t("guest.table.callWaiterHint")}</p>
      ) : null}
    </div>
  );
}
