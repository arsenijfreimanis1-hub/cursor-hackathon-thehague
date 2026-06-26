import cors from "cors";
import express from "express";

const app = express();
const port = Number(process.env.API_PORT ?? 4000);

app.use(cors());
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "hackathon-api", ts: new Date().toISOString() });
});

app.post("/webhooks/n8n", (req, res) => {
  console.log("[n8n webhook]", JSON.stringify(req.body));
  res.json({ received: true, body: req.body, ts: new Date().toISOString() });
});

app.listen(port, () => {
  console.log(`API listening on http://localhost:${port}`);
});
