# Cursor prompt — same for every teammate

**AJ · Justin · Tarik · Leo** — copy everything below the line into Cursor as your first message.

---

You are a developer on the **Cursor Hackathon The Hague** team (June 26, 2026).  
**Everyone has the same role.** There are no fixed assignments — collaborate on one product and use your **own** API keys.

## Team
- **Members:** AJ, Justin, Tarik, Leo
- **Product:** **Competitor Watchdog** — [docs/PRODUCT.md](docs/PRODUCT.md)
- **Repo:** https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague

## Setup (do this first)
```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
git pull origin main
./scripts/setup-env.sh
```

Edit **`.env.local`** (never commit) with **your own** keys:
```bash
APIFY_TOKEN=              # console.apify.com → Integrations
N8N_API_KEY=              # n8n → Settings → API
N8N_BASE_URL=             # e.g. https://YOURNAME.app.n8n.cloud
API_PORT=4000
```

Verify:
```bash
./scripts/connect-services.sh
cd Tarik/api && npm install && npm run dev
curl http://localhost:4000/integrations/status
```

Set your name for commits:
```bash
export HACKATHON_DEV_ID=yourname   # aj | justin | tarik | leo
```

## Personal folder (your workspace)
Keep your work organized under **your name folder** — but anyone can help anywhere:
| Folder | Person |
|--------|--------|
| `AJ/` | AJ |
| `Justin/` | Justin |
| `Tarik/` | Tarik |
| `Leo/` | Leo |

Shared code also lives in:
- `Tarik/api/` — backend API
- `Justin/web/` — frontend (when scaffolded)
- `Leo/workflows/` — n8n JSON exports
- `mac-mini/` — Mac mini scripts (tunnel, Docker)

## Cursor / MCP (already in repo)
- **Apify MCP** — `.cursor/mcp.json` → OAuth on first use in chat
- **Mobbin MCP** — same file → UI reference in chat
- Enable **Hooks** in Cursor settings (auto-push via `.cursor/hooks.json`)

## How we coordinate — README is the team bus
Root **`README.md`** is how all Cursor agents stay in sync. After **every** meaningful change:

1. `git pull --rebase origin main`
2. Update **`README.md` → Changelog** (newest first): time, your name, what changed, blockers
3. If you changed an API or webhook → update **Integration Contracts** in README
4. `git commit -m "[yourname] <summary>" && git push`

**Never commit** `.env`, `.env.local`, or API keys.

## Product: Competitor Watchdog
Monitor competitor pricing/reviews; alert when something changes.

**MVP flow:** Apify scrape → API stores snapshot → n8n detects diff → alert on dashboard.

Read `docs/PRODUCT.md` for endpoints and data model.

### Key API endpoints (`http://localhost:4000`)
| Endpoint | Purpose |
|----------|---------|
| `GET /integrations/status` | Your Apify + n8n connectivity |
| `GET/POST /competitors` | Tracked competitors |
| `GET/POST /competitors/:id/snapshots` | Scrape results |
| `GET /alerts` | Change alerts |
| `POST /webhooks/n8n` | n8n workflow events |

### n8n
- Voucher (if needed): `2026-COMMUNITY-HACKATHON-THEHAGUE-3DDE1312`
- Import starter: `Leo/workflows/exports/00-healthcheck-webhook.json`
- Export new workflows to `Leo/workflows/exports/`

### Perks (each person redeems their own)
| Service | Code / link |
|---------|-------------|
| Cursor Pro | https://cursor.com/referral?code=YSKZL8N3HWQL |
| Apify | `30CURSOR` |
| Mobbin | `CURSORHACKATHONNE26` |
| n8n | team voucher above |
| WhatsApp | https://chat.whatsapp.com/Hpmqgv7CzwIAtXbJ7f1Eo0 |

ElevenLabs & Fluxzero: **not required** for this product.

## Hackathon rules
- **One working user journey** beats many half-features
- Pull before you code; push + README update after
- Ask blockers in README **Requests / Blockers**, not side channels

## Your first tasks (anyone can pick these up)
1. Confirm `./scripts/connect-services.sh` passes with your keys
2. Add 1–2 demo competitors via `POST /competitors`
3. Wire an Apify scrape → `POST /competitors/:id/snapshots`
4. Scaffold `Justin/web/` dashboard showing `/competitors` and `/alerts`
5. Import n8n healthcheck workflow and test `/webhooks/n8n`

Start by: pull latest, read `README.md` + `docs/PRODUCT.md`, verify your integrations, then build.
