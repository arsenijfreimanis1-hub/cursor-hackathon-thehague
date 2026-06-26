Subject: Cursor Hackathon — your setup (AJ's team)

Hi Tarik,

We're building **Competitor Watchdog** — one product, four people. Copy everything below into Cursor as your first message.

---

## You are Tarik — Backend & Apify

**Hackathon:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ (lead/infra), Justin (frontend), Tarik (you), Leo (n8n)  
**Product:** Competitor Watchdog — monitor competitor prices/reviews, alert on changes  
**Repo:** https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague

### Setup
```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local   # add APIFY_TOKEN, N8N_API_KEY, N8N_BASE_URL
export HACKATHON_DEV_ID=tarik
cd Tarik/api && npm install && npm run dev
```

Apify MCP is preconfigured in `.cursor/mcp.json` — OAuth on first use in chat.

### Your folder
Work in **`Tarik/api/`**. Apify scraping logic goes in `src/services/apify.ts`.

### Your job today
1. Keep API running on port **4000**
2. Verify integrations: `GET /integrations/status` (Apify + n8n connectivity)
3. Wire Apify actors for competitor scraping (Google Maps / website crawler)
4. Endpoints Justin & Leo depend on:
   - `GET/POST /competitors`
   - `GET/POST /competitors/:id/snapshots`
   - `GET /alerts`
   - `POST /webhooks/n8n` (Leo sends events here)

### Activated perks you use
- **Apify** — token in `.env.local` as `APIFY_TOKEN`
- **n8n** — `N8N_API_KEY` + `N8N_BASE_URL` (e.g. `https://your.app.n8n.cloud`)

Test connections: `./scripts/connect-services.sh` from repo root.

### Team coordination
After every change: pull → update root **`README.md`** Changelog as `tarik` → commit `[tarik] ...` → push.

| Person | Needs from you |
|--------|----------------|
| **Justin** | Stable API on :4000, document any schema changes in README |
| **Leo** | Webhook payload docs, snapshot POST endpoint |
| **AJ** | `/integrations/status` green before demo |

### Apify actors to try (via MCP in Cursor)
- `compass/crawler-google-places` or Google Maps scraper — local competitors in The Hague
- `apify/website-content-crawler` — competitor product pages

### Definition of done
- `/integrations/status` shows Apify connected
- At least 1 demo competitor with real scraped snapshot data
- README Integration Contracts updated

Start: `npm run dev`, hit `/integrations/status`, read `docs/PRODUCT.md`.

— AJ
