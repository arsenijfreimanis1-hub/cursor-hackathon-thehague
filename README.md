# Cursor Hackathon The Hague — Team Hub

> **This README is the live coordination channel between all Cursor instances.**
> Every teammate must read this before starting work and update it after every push.

**Event:** Cursor Hackathon, The Hague — June 26, 2026  
**Team size:** 4 developers + Mac mini (integration hub)  
**Pack:** #054

---

## How we communicate (read this first)

1. **Before you code:** `git pull origin main`
2. **After every meaningful change:** commit, push, then update the **Changelog** section below
3. **Need something from another dev?** Add a row to **Requests / Blockers**
4. **Changed an API contract?** Update **Integration Contracts** immediately
5. **Mac mini owner:** Watches this file + runs `mac-mini/sync-from-github.sh` to wire services

Do not DM decisions that belong here. If it's not in this README, other Cursor agents cannot see it.

---

## Changelog (newest first)

| Time (CET) | Dev | Branch | Summary | Needs from team |
|------------|-----|--------|---------|-----------------|
| 2026-06-26 11:00 | Lead | `main` | Plan implementation: ARCHITECTURE, smoke tests, n8n webhook API, ideation scoring, perk activation scripts | All devs: run `./scripts/open-perk-activation.sh`, fill `docs/PERK_STATUS.md`, add keys to `.env.local`, run smoke tests |
| 2026-06-26 — | Lead | `main` | Initial repo bootstrap: MCP config, Mac mini scripts, teammate prompts, perk activation guide | All devs: clone repo, paste your role prompt into Cursor, activate perks, push first commit from your area |

---

## Requests / Blockers

| From | To | Status | Message |
|------|-----|--------|---------|
| Lead | All | OPEN | Clone repo, run perk activation (`docs/PERK_ACTIVATION.md`), paste your prompt from `prompts/` into Cursor |

---

## Integration Contracts

> Fill these in once you pick a product idea at kickoff. Until then, use placeholders.

### Webhook: App → n8n

| Field | Value |
|-------|-------|
| URL | `POST http://localhost:4000/webhooks/n8n` (dev) / `{PUBLIC_WEBHOOK_URL}/webhooks/n8n` (tunnel) |
| Method | `POST` |
| Payload | `{ "event": string, "source": "n8n", ... }` |
| Response | `{ "received": true, "body": {...}, "ts": "ISO8601" }` |

### API: Backend (Dev C)

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/health` | GET | — | `{ "status": "ok" }` |
| `/webhooks/n8n` | POST | JSON body | `{ "received": true, ... }` |

### Voice (Dev D — ElevenLabs)

| Field | Value |
|-------|-------|
| API key env | `ELEVENLABS_API_KEY` |
| Default voice ID | `TBD` |

### Data (Dev C — Apify)

| Actor | Purpose | Output schema |
|-------|---------|---------------|
| TBD | TBD | TBD |

---

## Repo layout

```
cursor-hackathon-thehague/
├── README.md                 ← YOU ARE HERE (team bus)
├── apps/
│   ├── web/                  ← Dev A (frontend / mobile shell)
│   ├── workflows/            ← Dev B (n8n exports + webhook docs)
│   ├── api/                  ← Dev C (backend + Apify pipelines)
│   └── voice/                ← Dev D (ElevenLabs + demo assets)
├── mac-mini/                 ← Integration hub scripts + Docker
├── prompts/                  ← Paste these into each teammate's Cursor
├── docs/                     ← Architecture, ideas, activation
└── .cursor/                  ← Shared MCP + rules + auto-push hook
```

---

## Role assignments

| Dev | Folder | Owns | Cursor prompt file |
|-----|--------|------|-------------------|
| **A** | `apps/web/` | UI, Mobbin refs, demo polish | `prompts/dev-a-frontend.md` |
| **B** | `apps/workflows/` | n8n flows, webhooks, automation | `prompts/dev-b-n8n.md` |
| **C** | `apps/api/` | Backend API, Apify data pipelines | `prompts/dev-c-backend.md` |
| **D** | `apps/voice/` | ElevenLabs voice, pitch demo script | `prompts/dev-d-voice.md` |
| **Lead / Mac mini** | `mac-mini/` | Docker, tunnels, env, merges | `prompts/dev-lead-mac-mini.md` |

---

## Partner perks (Pack #054)

| Partner | Code / Link | Status |
|---------|-------------|--------|
| Cursor Pro | https://cursor.com/referral?code=YSKZL8N3HWQL | ⬜ Run `./scripts/open-perk-activation.sh` |
| Apify $30 | `30CURSOR` | ⬜ Track in `docs/PERK_STATUS.md` |
| Mobbin 3mo Pro | `CURSORHACKATHONNE26` | ⬜ Track in `docs/PERK_STATUS.md` |
| ElevenLabs Creator | Discord `#coupon-codes` + Luma email | ⬜ Track in `docs/PERK_STATUS.md` |
| n8n Cloud Pro | `2026-COMMUNITY-HACKATHON-THEHAGUE-3DDE1312` | ⬜ Team account |
| Fluxzero | https://fluxzero.io | ⬜ Team signup |
| WhatsApp | https://chat.whatsapp.com/Hpmqgv7CzwIAtXbJ7f1Eo0 | ⬜ Join |

Full steps: [docs/PERK_ACTIVATION.md](docs/PERK_ACTIVATION.md) · Status tracker: [docs/PERK_STATUS.md](docs/PERK_STATUS.md) · Smoke tests: [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md)

---

## Mac mini (integration hub)

The Mac mini pulls from GitHub and connects services:

```bash
cd mac-mini
./setup.sh          # first time only
./sync-from-github.sh   # run after every teammate push (or via cron)
```

See [mac-mini/README.md](mac-mini/README.md).

---

## Quick start (every teammate)

```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local   # fill in your keys locally — never commit
git pull origin main
```

Open Cursor → paste your role prompt from `prompts/` as the first message to the agent.

---

## Idea candidates (pick at kickoff)

See [docs/IDEAS.md](docs/IDEAS.md) for scored options aligned to partner tracks.
