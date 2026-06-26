import cors from "cors";
import express from "express";
import { checkApify } from "./services/apify";
import { checkN8n } from "./services/n8n";
import { store } from "./store";

const app = express();
const port = Number(process.env.API_PORT ?? 4000);

app.use(cors());
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "competitor-watchdog-api", ts: new Date().toISOString() });
});

app.get("/integrations/status", async (_req, res) => {
  const apifyToken = process.env.APIFY_TOKEN;
  const n8nKey = process.env.N8N_API_KEY;
  const n8nBase = process.env.N8N_BASE_URL;

  const apify = apifyToken ? await checkApify(apifyToken) : { ok: false, error: "APIFY_TOKEN not set" };
  const n8n = n8nKey && n8nBase ? await checkN8n(n8nBase, n8nKey) : { ok: false, error: "N8N_API_KEY or N8N_BASE_URL not set" };

  res.json({
    product: "Competitor Watchdog",
    apify: { connected: apify.ok, username: apify.username, error: apify.error },
    n8n: { connected: n8n.ok, error: n8n.error },
    elevenlabs: { connected: false, note: "Not activated yet — optional stretch" },
    fluxzero: { connected: false, note: "Not using" },
    ts: new Date().toISOString(),
  });
});

app.get("/competitors", (_req, res) => {
  res.json({ competitors: store.listCompetitors() });
});

app.post("/competitors", (req, res) => {
  const { name, url, niche } = req.body as { name?: string; url?: string; niche?: string };
  if (!name || !url) return res.status(400).json({ error: "name and url required" });
  const c = store.addCompetitor(name, url, niche ?? "general");
  res.status(201).json(c);
});

app.get("/competitors/:id/snapshots", (req, res) => {
  res.json({ snapshots: store.getSnapshots(req.params.id) });
});

app.post("/competitors/:id/snapshots", (req, res) => {
  const { prices = [], reviews = [] } = req.body as { prices?: { label: string; value: string }[]; reviews?: { text: string; rating?: number }[] };
  const s = store.addSnapshot(req.params.id, prices, reviews);
  res.status(201).json(s);
});

app.get("/alerts", (_req, res) => {
  res.json({ alerts: store.listAlerts() });
});

app.post("/webhooks/n8n", (req, res) => {
  console.log("[n8n webhook]", JSON.stringify(req.body));
  const body = req.body as { event?: string; competitorId?: string; field?: string; oldValue?: string; newValue?: string };
  if (body.event === "price_change" && body.competitorId && body.field) {
    store.addAlert(body.competitorId, body.field, body.oldValue ?? "", body.newValue ?? "");
  }
  res.json({ received: true, body: req.body, ts: new Date().toISOString() });
});

app.listen(port, () => {
  console.log(`Competitor Watchdog API on http://localhost:${port}`);
});
