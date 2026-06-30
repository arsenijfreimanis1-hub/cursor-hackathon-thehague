# William / Jarvis

Personal voice agent and Mac mini automation stack: FastAPI backend (`jarvis/`), macOS helper, launchd services, and local tooling.

**Project path:** `/Users/willy/jarvis-core`

## Quick start

```bash
cd /Users/willy/jarvis-core
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
./scripts/setup-all.sh   # permissions, helper, launchd — see script for flags
```

Agent API default: `http://127.0.0.1:8787` · Helper: `http://127.0.0.1:8788`

## Layout

| Path | Purpose |
|------|---------|
| `jarvis/` | William agent (FastAPI, services, static UI) |
| `macos-helper/` | Swift helper (wake word, screen, input) |
| `openclaw-bridge/` | OpenClaw gateway bridge |
| `launchd/` | plist templates |
| `scripts/` | Install, voice, docker stack, backups |
| `docs/SYSTEMS_MAP.md` | Architecture map |
| `docs/MEMORY_AND_SERVER.md` | Memory and server notes |

## Docker (optional)

```bash
docker compose --profile redis up -d    # optional Redis
docker compose --profile backup up -d   # nightly jarvis.db copy to backups/
```

## Related project

**Spliit / Rekentafel** (restaurant bill-splitting MVP) lives separately at `/Users/willy/Projects/spliit` — not in this repo.

## Config

Copy `.env.example` to `.env`. Keys use `JARVIS_` prefix where applicable (see `jarvis/config.py`).
