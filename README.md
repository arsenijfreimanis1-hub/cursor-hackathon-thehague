# Cursor Hackathon The Hague — Team Hub

> **This README is the live coordination channel between all Cursor instances.**
> Every teammate must read this before starting work and update it after every push.

**Event:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ · Justin · Tarik · Leo (+ Mac mini hub)  
**Product:** **Competitor Watchdog** — [docs/PRODUCT.md](docs/PRODUCT.md)  
**Pack:** #054

---

## How we communicate

1. **Before you code:** `git pull origin main`
2. **After every meaningful change:** commit, push, update **Changelog** below
3. **Blockers:** add to **Requests / Blockers**
4. **API changes:** update **Integration Contracts** immediately
5. **AJ:** runs `mac-mini/sync-from-github.sh` after pushes

---

## Changelog (newest first)

| Time (CET) | Who | Summary | Needs |
|------------|-----|---------|-------|
| 2026-06-26 12:00 | AJ | Team restructure: `AJ/` `Justin/` `Tarik/` `Leo/` folders, Competitor Watchdog locked, integration API, email-ready prompts | Everyone: pull, read your `CURSOR_PROMPT.md`, add keys to `.env.local`, run `./scripts/connect-services.sh` |
| 2026-06-26 11:00 | AJ | Architecture, smoke tests, ideation scoring | — |
| 2026-06-26 — | AJ | Initial repo bootstrap | — |

---

## Requests / Blockers

| From | To | Status | Message |
|------|-----|--------|---------|
| AJ | All | OPEN | Pull latest, paste your `CURSOR_PROMPT.md` into Cursor, verify perks in `.env.local` |

---

## Team & folders

| Person | Folder | Owns |
|--------|--------|------|
| **AJ** | `AJ/` + `mac-mini/` | Infra, tunnel, README, merges, integration tests |
| **Justin** | `Justin/web/` | Dashboard UI (Mobbin) |
| **Tarik** | `Tarik/api/` | REST API, Apify scraping |
| **Leo** | `Leo/workflows/` | n8n automation, pitch script |

**Cursor prompts (email to teammates):** `Justin/CURSOR_PROMPT.md` · `Tarik/CURSOR_PROMPT.md` · `Leo/CURSOR_PROMPT.md` · `AJ/CURSOR_PROMPT.md`

---

## Integration Contracts

### API base URL
- Dev: `http://localhost:4000`
- Tunnel: `PUBLIC_WEBHOOK_URL` in `.env.local` (AJ sets from Mac mini)

### Endpoints (Tarik)

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/health` | GET | — | `{ status, service, ts }` |
| `/integrations/status` | GET | — | Apify + n8n connection status |
| `/competitors` | GET | — | `{ competitors: [...] }` |
| `/competitors` | POST | `{ name, url, niche? }` | competitor object |
| `/competitors/:id/snapshots` | GET/POST | `{ prices[], reviews[] }` | snapshot |
| `/alerts` | GET | — | `{ alerts: [...] }` |
| `/webhooks/n8n` | POST | see Leo's workflow | `{ received: true }` |

### n8n → API webhook payload (Leo)
```json
{
  "event": "price_change",
  "competitorId": "comp_1",
  "field": "price",
  "oldValue": "€10",
  "newValue": "€12"
}
```

---

## Partner perks

| Partner | Status |
|---------|--------|
| Cursor Pro | ✅ Activated |
| Apify | ✅ Activated |
| Mobbin | ✅ Activated |
| n8n Cloud Pro | ✅ Activated |
| ElevenLabs | ⬜ Not yet — optional stretch |
| Fluxzero | ⬜ Not using |
| WhatsApp | https://chat.whatsapp.com/Hpmqgv7CzwIAtXbJ7f1Eo0 |

Verify: `./scripts/connect-services.sh` · Tracker: [docs/PERK_STATUS.md](docs/PERK_STATUS.md)

---

## Quick start

```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local   # add APIFY_TOKEN, N8N_API_KEY, N8N_BASE_URL
git pull origin main
```

Open Cursor → paste your `CURSOR_PROMPT.md` → enable Hooks in settings.

---

## Mac mini (AJ)

```bash
cd mac-mini && ./setup.sh && ./sync-from-github.sh
./start-tunnel.sh   # copy URL → README + .env.local
```
