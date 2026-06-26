import { useState } from "react";
import { useNavigate, useParams } from "@tanstack/react-router";
import { useJoinSession } from "@rekentafel/guest-hooks";
import { Button, Card } from "@rekentafel/ui-core";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3000/v1";

export function JoinPage() {
  const { paymentSessionId } = useParams({ from: "/session/$paymentSessionId/join" });
  const navigate = useNavigate();
  const join = useJoinSession(API_BASE);
  const [displayName, setDisplayName] = useState("");
  const [joinPin, setJoinPin] = useState("");

  return (
    <main className="main stack">
      <header className="hero">
        <h1>Deelnemen</h1>
        <p className="muted">Voer de pincode in van uw bediening</p>
      </header>

      <Card title="Pincode">
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            join.mutate(
              {
                payment_session_id: paymentSessionId,
                join_pin: joinPin,
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
          <label>
            Uw naam
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Gast 1"
            />
          </label>
          <label>
            Pincode
            <input
              value={joinPin}
              onChange={(e) => setJoinPin(e.target.value)}
              placeholder="6 cijfers"
              inputMode="numeric"
              maxLength={6}
            />
          </label>
          {join.error && <p className="error">{join.error.message}</p>}
          <Button type="submit" disabled={join.isPending || joinPin.length < 6}>
            {join.isPending ? "Bezig…" : "Deelnemen"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
