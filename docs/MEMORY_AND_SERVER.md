# Memory, Logging & Local Server

William Agent now persists a unified interaction timeline from deployment time forward.

## What gets logged

Every voice and web chat turn is stored in SQLite (`interaction_events`):

- user message, assistant reply, source, intent, engine
- task id + status, alignment score (0–1) and notes
- integrations: terminal runs, Cursor escalations, worker task outcomes

Memory epoch (`memory_since`) is set automatically on first boot after this upgrade — older history is not backfilled.

View logs: **http://127.0.0.1:8787/admin** → Interaction log section.

API: `GET /api/events?limit=50`

## Alignment evaluation

After each turn, a lightweight heuristic scores whether the reply matched the request. Scores below 0.4 are recorded as `misaligned` struggles in the learning system.

## Cross-session continuity

Recent timeline entries are injected into router prompts (`RECENT ACTIVITY`) alongside FTS memory and conversation history.

## Notion (optional)

Set in `.env`:

```bash
JARVIS_NOTION_API_KEY=secret_...
JARVIS_NOTION_PARENT_PAGE_ID=<page-id-where-child-pages-go>
```

- Significant tasks (failed, misaligned, cursor/code) → screenshot + Notion page
- Scheduler exports event batches every 12h (if ≥5 events)
- Manual export: Admin panel → **Export to Notion** or `POST /api/events/export-notion`

Create a Notion integration at https://www.notion.so/my-integrations and share the parent page with it.

## Sleep mode (voice)

The macOS helper enters **sleep mode** after ~45s of junk partial transcripts or ~50s of background TV/speech without valid commands.

- Speaks: *"Going to sleep, boss. Say hey Willie when you need me."*
- Stops full recognition to save CPU; polls for wake word every ~2.5s
- Menu bar: 💤 sleeping, 🤖 active
- `ensureAwake` / watchdog still runs; saying **hey willy** wakes fully

Rebuild after Swift changes:

```bash
./scripts/install-helper.sh
```

## Local 24/7 server

| Service        | Port  | How                          |
|----------------|-------|------------------------------|
| jarvis-core    | 8787  | launchd `com.willy.jarvis-core` |
| macos-helper   | 8788  | launchd `com.willy.jarvis-helper` |
| Ollama         | 11434 | separate install             |
| Postgres       | 5432  | optional docker profile      |
| Redis          | 6379  | optional docker profile      |
| Caddy HTTP proxy | 8080  | `docker compose --profile proxy` |

Health check:

```bash
./scripts/server-status.sh
```

Optional Docker stack:

```bash
./scripts/docker-stack.sh start   # Postgres, Redis, Caddy proxy, backups
./scripts/docker-stack.sh status
```

Colima starts at login via `brew services`. Docker stack auto-heals via launchd `com.willy.jarvis-docker`.

**Public internet (recommended):** Cloudflare Tunnel — no router port-forward:

```bash
./scripts/configure-tunnel.sh   # paste token from Cloudflare Zero Trust
./scripts/docker-stack.sh restart
```

Set tunnel public hostname service URL to `http://host.docker.internal:8080`. Caddy listens on `0.0.0.0:8080` and proxies to jarvis-core on the host.

```bash
mkdir -p backups
docker compose --profile backup up -d          # nightly SQLite copies
docker compose --profile proxy up -d         # HTTP proxy on :8080 (LAN + tunnel backend)
docker compose --profile public up -d        # + cloudflared when CLOUDFLARE_TUNNEL_TOKEN is set
docker compose --profile postgres up -d      # Postgres (future use)
```

**Security:** jarvis-core/helper stay on `127.0.0.1`. Public access goes through Caddy + Cloudflare. Do not expose 8787/8788 directly without auth.

## Env vars summary

| Variable | Purpose |
|----------|---------|
| `JARVIS_NOTION_API_KEY` | Notion integration token |
| `JARVIS_NOTION_PARENT_PAGE_ID` | Parent page for learning exports |
| `JARVIS_NOTION_EXPORT_INTERVAL_HOURS` | Auto export interval (default 12) |
| `CURSOR_API_KEY` | Cloud reasoning / codegen |
| `CLOUDFLARE_TUNNEL_TOKEN` | Public HTTPS via Cloudflare Tunnel |

## Restart after changes

```bash
./scripts/restart.sh
# or
launchctl kickstart -k gui/$(id -u)/com.willy.jarvis-core
```
