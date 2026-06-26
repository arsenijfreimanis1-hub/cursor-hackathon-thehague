Subject: Cursor Hackathon — your setup (AJ's team)

Hi Justin,

We're building **Competitor Watchdog** — one product, four people. Copy everything below into Cursor as your first message.

---

## You are Justin — Frontend

**Hackathon:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ (lead/infra), Justin (you), Tarik (API/Apify), Leo (n8n)  
**Product:** Competitor Watchdog — monitor competitor prices/reviews, alert on changes  
**Repo:** https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague

### Setup
```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local
export HACKATHON_DEV_ID=justin
git pull origin main
```

Open this folder in Cursor. Enable **Hooks** in settings (auto-push on agent stop).

### Your folder
Work only in **`Justin/web/`** unless you document a cross-cutting change in root `README.md` first.

### Your job today
Build the dashboard for Competitor Watchdog:
1. List competitors (`GET http://localhost:4000/competitors`)
2. Alerts feed (`GET http://localhost:4000/alerts`)
3. Add competitor form (`POST /competitors`)
4. Polish with Mobbin Pro (code already redeemed: `CURSORHACKATHONNE26`)

Stack: Vite + React + TypeScript + Tailwind. API base: `import.meta.env.VITE_API_URL || 'http://localhost:4000'`

### Team coordination — README is the bus
After **every** meaningful change:
1. `git pull --rebase origin main`
2. Update root **`README.md`** → Changelog (newest first): time, `justin`, what you built, what you need
3. `git commit -m "[justin] <summary>" && git push`

### Who to coordinate with
| Person | Owns | You need from them |
|--------|------|-------------------|
| **Tarik** | `Tarik/api/` | API running on :4000, stable JSON shapes |
| **Leo** | `Leo/workflows/` | Webhook events that populate `/alerts` |
| **AJ** | `mac-mini/`, README | `PUBLIC_WEBHOOK_URL` when tunnel is up |

### Integration contracts (do not change without updating README)
- `GET /competitors` → `{ competitors: [...] }`
- `GET /alerts` → `{ alerts: [...] }`
- `POST /competitors` → `{ name, url, niche? }`

### Definition of done
- Dashboard shows live data from Tarik's API
- Demo looks intentional (not default Vite boilerplate)
- README Changelog updated

Start: read `docs/PRODUCT.md`, scaffold `Justin/web/`, push initial commit.

— AJ
