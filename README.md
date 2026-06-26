# Cursor Hackathon The Hague — Team Hub

> **This README is the live coordination channel between all Cursor instances.**
> Every teammate must read this before starting work and update it after every push.

**Event:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ · Justin · Tarik · Leo — **equal developers**, one product  
**Product:** **Competitor Watchdog** — [docs/PRODUCT.md](docs/PRODUCT.md)  
**Cursor prompt (same for everyone):** [CURSOR_PROMPT.md](CURSOR_PROMPT.md)  
**Pack:** #054

---

## Rekentafel MVP (Mac mini demo)

Bill-splitting restaurant demo built on this repo — **guest QR web + waiter app + Mollie test payments**.

| App | Port | URL (LAN) |
|-----|------|-----------|
| Guest web | 5173 | `http://<VITE_LAN_HOST>:5173` |
| Staff / waiter | 5174 | `http://<VITE_LAN_HOST>:5174` |
| API | 3000 | `http://<VITE_LAN_HOST>:3000/v1` |

**Start on Mac mini** (repo path: `/Users/willy/jarvis-core`, not `~/cursor-hackathon-thehague`):

```bash
cd /Users/willy/jarvis-core
./scripts/rekentafel-poc.sh
```

Leave that terminal open. Optional guest env only: `./scripts/write-guest-env.sh` then `pnpm dev:guest`.

---

## How we communicate

1. **Before you code:** `git pull origin main`
2. **After every meaningful change:** commit, push, update **Changelog** below
3. **Blockers:** add to **Requests / Blockers**
4. **API changes:** update **Integration Contracts** immediately
5. **Mac mini:** whoever is on it runs `mac-mini/sync-from-github.sh` after pushes

---

## Changelog (newest first)

| Time (CET) | Who | Summary | Needs |
|------------|-----|---------|-------|
| 2026-06-26 15:30 | Willy | Merged Rekentafel MVP monorepo (guest/staff web, API, waiter Capacitor, QR demo, i18n) | MacBook: clone + `pnpm install` + see Rekentafel section |
| 2026-06-26 12:30 | AJ | Unified `CURSOR_PROMPT.md` for all devs (no role split); Mobbin MCP added; equal developer model | Everyone: paste `CURSOR_PROMPT.md`, use own keys in `.env.local` |
| 2026-06-26 12:00 | AJ | Member folders, Competitor Watchdog, integration API | — |

---

## Requests / Blockers

| From | To | Status | Message |
|------|-----|--------|---------|
| AJ | All | OPEN | Pull latest, paste **`CURSOR_PROMPT.md`** into Cursor, add **your own** keys to `.env.local` |

---

## Team folders (organization only — no fixed roles)

| Folder | Use for |
|--------|---------|
| `AJ/` | AJ's notes and work |
| `Justin/` | Justin's notes and work |
| `Tarik/` | Tarik's notes and work |
| `Leo/` | Leo's notes and work |

Shared code: `Tarik/api/`, `Justin/web/`, `Leo/workflows/`, `mac-mini/`, **`apps/`** (Rekentafel). Anyone can edit anywhere — update README when you do.

---

## Integration Contracts

### API base URL
- Rekentafel dev: `http://localhost:3000/v1`
- Watchdog dev: `http://localhost:4000`
- Tunnel: `PUBLIC_WEBHOOK_URL` / `PUBLIC_BASE_URL` in `.env` (Mac mini)

### Endpoints (shared API in `Tarik/api/`)

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
git clone git@github.com:arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env
pnpm install
git pull origin main
```

Open Cursor → paste **`CURSOR_PROMPT.md`** → enable Hooks in settings.

---

## Mac mini (AJ)

```bash
cd mac-mini && ./setup.sh && ./sync-from-github.sh
./start-tunnel.sh   # copy URL → README + .env
./scripts/rekentafel-poc.sh   # Rekentafel demo stack
```
