# API (Tarik)

```bash
cp ../../.env.example ../../.env.local
npm install
npm run dev
```

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness |
| `GET /integrations/status` | Apify + n8n connection check |
| `GET/POST /competitors` | Competitor CRUD (in-memory MVP) |
| `GET/POST /competitors/:id/snapshots` | Scrape results |
| `GET /alerts` | Change alerts |
| `POST /webhooks/n8n` | n8n events from Leo's workflows |

Document changes in root `README.md` Integration Contracts.

