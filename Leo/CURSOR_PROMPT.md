Subject: Cursor Hackathon — your setup (AJ's team)

Hi Leo,

We're building **Competitor Watchdog** — one product, four people. Copy everything below into Cursor as your first message.

---

## You are Leo — n8n Automation & Pitch

**Hackathon:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ (lead/infra), Justin (frontend), Tarik (API/Apify), Leo (you)  
**Product:** Competitor Watchdog — monitor competitor prices/reviews, alert on changes  
**Repo:** https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague

### Setup
```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local
export HACKATHON_DEV_ID=leo
git pull origin main
```

n8n Cloud Pro voucher: `2026-COMMUNITY-HACKATHON-THEHAGUE-3DDE1312` (Pro + Monthly).  
Guide: https://n8n.notion.site/voucher-code

### Your folder
Work in **`Leo/workflows/`**. Export every workflow JSON to `exports/` after saving in n8n.

### Your job today
1. Import `Leo/workflows/exports/00-healthcheck-webhook.json` — verify n8n → API path works
2. Build **`01-schedule-scrape`** — cron trigger → Apify actor → POST snapshot to Tarik's API
3. Build **`02-diff-alert`** — on new data, detect price change → POST to `/webhooks/n8n`:
   ```json
   { "event": "price_change", "competitorId": "...", "field": "price", "oldValue": "€10", "newValue": "€12" }
   ```
4. Own **`docs/PITCH.md`** — 3-minute demo script for the team

### Webhook URLs
| Environment | URL |
|-------------|-----|
| Local (Tarik's laptop) | `http://localhost:4000/webhooks/n8n` |
| Mac mini tunnel | Ask AJ for `PUBLIC_WEBHOOK_URL` in README |

### Activated perks you use
- **n8n Cloud Pro** — primary tool
- **Apify** — trigger actors from n8n HTTP nodes (credentials in n8n UI, not git)

ElevenLabs & Fluxzero: **not activated** — skip unless AJ says otherwise.

### Team coordination
After every workflow save: export JSON → pull → update root **`README.md`** Changelog as `leo` → push.

| Person | Coordinate on |
|--------|---------------|
| **Tarik** | API endpoints, snapshot payload shape |
| **Justin** | Which alert fields show on dashboard |
| **AJ** | Public webhook URL for n8n |

### Definition of done
- Healthcheck workflow passes end-to-end
- At least one automated scrape → alert flow working in demo
- `docs/PITCH.md` drafted
- README updated with your webhook URLs

Start: import healthcheck workflow, test against Tarik's API, read `docs/PRODUCT.md`.

— AJ
