# William Agent (JarvisCore)

Local-first 24/7 personal agent daemon for Willy's Mac mini.

## Quick start

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

Open **http://127.0.0.1:8787** for the control panel.

## What it does (Phase 1)

- FastAPI daemon on port 8787 (LAN-local only)
- SQLite task queue and approval inbox
- Local Ollama inference via `llama3.2:3b`
- `launchd` service for 24/7 uptime

## Manual run (dev)

```bash
source .venv/bin/activate
uvicorn jarvis.main:app --host 127.0.0.1 --port 8787 --reload
```

## Service control

```bash
launchctl kickstart -k gui/$(id -u)/com.willy.jarvis-core   # restart
launchctl bootout gui/$(id -u)/com.willy.jarvis-core        # stop
```

## Next phases

- Cursor SDK escalation for heavy codegen
- Full mouse/keyboard control (Accessibility permissions)
- Self-modification loop with approval gates

## Integrations

| Integration | Setup |
|---|---|
| WhatsApp | `./scripts/install-openclaw-bridge.sh` |
| Cursor SDK | Copy `.env.example` → `.env`, add `CURSOR_API_KEY` from [dashboard](https://cursor.com/dashboard/integrations) |
| Netatmo (later) | `./scripts/setup-netatmo-tunnel.sh` |
| macOS helper | `./scripts/install-helper.sh` |
| Vision model | `ollama pull moondream` (for desktop screen analysis) |

## Routing

- Simple questions → local Ollama (`llama3.2:3b`, free)
- Complex codegen → Cursor SDK (`composer-2.5`, uses Premium)
- Self-changes → sandbox git branch → approval → merge to `main`
- Morning briefing → daily at 08:00 Europe/Amsterdam
