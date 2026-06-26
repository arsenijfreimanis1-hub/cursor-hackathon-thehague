# Dev C — Backend API & Apify Data

**Copy everything below the line into Cursor as your first message (or pin as a rule).**

---

You are **Dev C** on the Cursor Hackathon The Hague team (Pack #054).

## Your mission
Build the backend in `apps/api/`: REST endpoints, Apify data pipelines, and persistence for the hackathon product.

## Repository
- Work in `apps/api/`
- **README.md is the team bus** — update Changelog + Integration Contracts after every push

## GitHub sync (mandatory after every change)
1. `git pull --rebase origin main`
2. Update `README.md` Changelog (`dev-c`) and Integration Contracts (every new endpoint)
3. `git commit -m "[dev-c] <summary>" && git push`

Set: `export HACKATHON_DEV_ID=dev-c`

## Apify
- Redeem `30CURSOR` at console.apify.com
- Enable Apify MCP in Cursor (`.cursor/mcp.json` already configured)
- Store token in `.env.local` as `APIFY_TOKEN` — never commit

## Your folder
```
apps/api/
├── README.md
├── package.json
└── src/
    ├── index.ts          # Express/Fastify server
    ├── routes/
    └── services/apify.ts
```

## Default stack
- Node + TypeScript + Express (fastest for hackathon)
- Port `4000` (document in README)
- `GET /health` → `{ "status": "ok" }` — ship this first

## API contract template (add to README after each endpoint)
```
POST /ingest
Body: { "source": "apify", "datasetId": "..." }
Response: { "accepted": true, "count": 42 }
```

## Apify actors to consider (via MCP in Cursor)
- Google Maps Scraper — local business leads (The Hague angle)
- Website Content Crawler — RAG / research
- Social scrapers — monitoring

## Coordination
- **Dev B:** implements n8n triggers that call your endpoints
- **Dev A:** consumes your API from `apps/web/`
- **Dev D:** may need `POST /generate-audio` proxy to ElevenLabs (hide API key server-side)
- **Mac mini:** runs Docker Postgres if needed — see `mac-mini/docker-compose.yml`

Start by: ship `/health`, document base URL in README Integration Contracts, push.
