#!/usr/bin/env node
/** Zero-dependency server for smoke tests when npm deps not installed. */
import http from "node:http";

const port = Number(process.env.API_PORT ?? 4000);

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "hackathon-api-smoke", ts: new Date().toISOString() }));
    return;
  }

  if (req.method === "POST" && req.url === "/webhooks/n8n") {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      let parsed = {};
      try { parsed = JSON.parse(body || "{}"); } catch { /* ignore */ }
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ received: true, body: parsed, ts: new Date().toISOString() }));
    });
    return;
  }

  res.writeHead(404);
  res.end("not found");
});

server.listen(port, () => console.log(`smoke server :${port}`));
