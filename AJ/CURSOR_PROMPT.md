Subject: Cursor Hackathon — your setup (AJ's team)

Hi AJ — this is your own lead prompt. Copy into Cursor on the Mac mini.

---

## You are AJ — Team Lead & Mac Mini Hub

**Hackathon:** Cursor Hackathon, The Hague — June 26, 2026  
**Team:** AJ (you), Justin (frontend), Tarik (API/Apify), Leo (n8n)  
**Product:** Competitor Watchdog  
**Repo:** https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague

### Setup (Mac mini)
```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local          # your Apify + n8n keys
cp mac-mini/.env.example mac-mini/.env
export HACKATHON_DEV_ID=aj
cd mac-mini && ./setup.sh
```

### Your responsibilities
1. **README keeper** — merge conflicts, Changelog accuracy, Integration Contracts
2. **Mac mini hub** — `mac-mini/sync-from-github.sh` after every teammate push
3. **Tunnel** — `./mac-mini/start-tunnel.sh` → put URL in README as `PUBLIC_WEBHOOK_URL`
4. **Integration gate** — `./scripts/connect-services.sh` must show Apify ✅ and n8n ✅ before demo
5. **Merges** — fast-merge teammate PRs to `main` during hackathon

### Your folder
- `AJ/` — your notes
- `mac-mini/` — Docker, tunnel, env (you own this)

### Activated services (your keys in `.env.local`)
| Service | Status | Env vars |
|---------|--------|----------|
| Cursor Pro | ✅ | — |
| Apify | ✅ | `APIFY_TOKEN` |
| Mobbin | ✅ | — |
| n8n Cloud Pro | ✅ | `N8N_API_KEY`, `N8N_BASE_URL` |
| ElevenLabs | ⬜ skip | — |
| Fluxzero | ⬜ skip | — |

### Verify connections now
```bash
./scripts/connect-services.sh
./scripts/smoke-test/run-all.sh
curl http://localhost:4000/integrations/status   # after Tarik starts API
```

### Email teammates
Send each person their file from the repo:
- `Justin/CURSOR_PROMPT.md`
- `Tarik/CURSOR_PROMPT.md`
- `Leo/CURSOR_PROMPT.md`

### Integration contracts you maintain (root README)
Update when anyone changes APIs or webhooks. Current API owner: **Tarik** (`Tarik/api/`).

### Day-of timeline
| Time | Action |
|------|--------|
| 10:00 | Confirm all 4 have pulled latest, API + healthcheck green |
| 14:00 | Core loop working: scrape → alert → dashboard |
| 16:30 | Backup demo video recorded |
| 17:30 | Submit |

After every change: `[aj]` commit → push → update README Changelog.

— You
