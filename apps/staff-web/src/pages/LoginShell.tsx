import { useState } from "react";
import { LanguageSwitcher, NetworkBanner, useT } from "@rekentafel/i18n";
import { Button, Card, Field } from "@rekentafel/ui-core";
import { LAN_HOST } from "../config";

export function LoginShell({ onLogin }: { onLogin: (token: string) => void }) {
  const t = useT();
  const [email, setEmail] = useState("waiter@demo.rekentafel.nl");
  const [password, setPassword] = useState("demo");

  return (
    <main className="login-screen">
      <div className="login-brand">
        <div className="login-brand__mark">RT</div>
        <h1>{t("staff.login.title")}</h1>
        <p>{t("staff.login.subtitle")}</p>
        <LanguageSwitcher className="login-lang" />
      </div>

      <NetworkBanner port={5174} variant="staff" lanHost={LAN_HOST} />

      <Card title={t("staff.login.title")}>
        <form
          className="login-form"
          onSubmit={(e) => {
            e.preventDefault();
            onLogin("dev-staff-token");
          }}
        >
          <Field label={t("staff.login.email")}>
            <input
              className="rt-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              autoComplete="username"
            />
          </Field>
          <Field label={t("staff.login.password")}>
            <input
              className="rt-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit">{t("staff.login.submit")}</Button>
          <p className="muted" style={{ textAlign: "center", fontSize: "0.8125rem" }}>
            {t("staff.login.demo")}
          </p>
        </form>
      </Card>
    </main>
  );
}
