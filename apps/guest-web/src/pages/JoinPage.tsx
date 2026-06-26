import { useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { useJoinSession } from "@rekentafel/guest-hooks";
import { LanguageSwitcher, useT } from "@rekentafel/i18n";
import { Button, Card, Field, PageShell } from "@rekentafel/ui-core";

import { API_BASE } from "../config";

export function JoinPage() {
  const t = useT();
  const { paymentSessionId } = useParams({ from: "/session/$paymentSessionId/join" });
  const navigate = useNavigate();
  const join = useJoinSession(API_BASE);
  const [displayName, setDisplayName] = useState("");

  return (
    <PageShell
      title={t("guest.join.title")}
      subtitle={t("guest.join.subtitle")}
      headerExtra={<LanguageSwitcher />}
    >
      <Card className="join-card">
        <div className="join-icon" aria-hidden>👋</div>
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            join.mutate(
              {
                payment_session_id: paymentSessionId,
                display_name: displayName || "Gast",
              },
              {
                onSuccess: () => {
                  navigate({ to: "/session/$paymentSessionId", params: { paymentSessionId } });
                },
              },
            );
          }}
        >
          <Field label={t("guest.join.name")}>
            <input
              className="rt-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t("guest.join.namePlaceholder")}
              autoComplete="name"
              autoFocus
            />
          </Field>
          {join.error && <p className="error">{join.error.message}</p>}
          <Button type="submit" disabled={join.isPending}>
            {join.isPending ? t("guest.join.busy") : t("guest.join.submit")}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
