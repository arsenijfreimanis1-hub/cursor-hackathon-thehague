import { useState } from "react";
import { Button, Card } from "@rekentafel/ui-core";

export function LoginShell({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState("waiter@demo.rekentafel.nl");
  const [password, setPassword] = useState("demo");

  return (
    <main className="staff-layout">
      <Card title="Rekentafel Staff">
        <form
          className="login-form"
          onSubmit={(e) => {
            e.preventDefault();
            onLogin("dev-staff-token");
          }}
        >
          <label>
            E-mail
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          </label>
          <label>
            Wachtwoord
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
          </label>
          <Button type="submit">Inloggen</Button>
          <p className="muted">Dev login — geen echte auth in MVP scaffold.</p>
        </form>
      </Card>
    </main>
  );
}
