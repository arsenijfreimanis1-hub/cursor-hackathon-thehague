# William Agent (JarvisCore)

Local-first Alexa-like personal agent for Willy's Mac mini — voice, memory, hybrid AI, and background work.

## Quick start

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

Open **http://127.0.0.1:8787** for the control panel.

## What William does

- **Voice** — wake word ("Hey Willy"), 90s conversation mode, TTS replies via macOS helper (:8788)
- **Hybrid brain** — local Ollama for fast chat, web research for facts, Cursor cloud for hard reasoning/code
- **Long-term memory** — remember/recall across sessions, auto-compress idle conversations
- **Background jobs** — queue research while you keep talking; proactive "Done, boss" when finished
- **Self-learning** — failure lessons injected into every prompt; periodic learning report
- **Mac control** — apps, Spotify/YouTube, terminal maintenance, screenshots + vision
- **Approvals** — sensitive actions, desktop input, self-modify merges

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

## Routing

| Intent | Engine | Behavior |
|--------|--------|----------|
| chat | Ollama + memory | Fast voice replies with session + long-term context |
| fact / reason | Web research → Ollama / Cursor | Search-first; fail closed if unverified |
| code | Cursor SDK | Complex builds, refactors, multi-file work |
| action | Orchestrator + worker | Deferred background tasks with proactive speak |
| remember / recall | Memory store / FTS | "Remember that…" and "do you recall…" |
| system | macOS control | Apps, music, windows |
| terminal | Shell | Maintenance commands (with full-access gate) |

## Integrations

| Integration | Setup |
|---|---|
| WhatsApp | `./scripts/install-openclaw-bridge.sh` |
| Cursor SDK | Copy `.env.example` → `.env`, add `CURSOR_API_KEY` from [dashboard](https://cursor.com/dashboard/integrations) |
| Netatmo | `./scripts/setup-netatmo-tunnel.sh` |
| Voice wake word | External mic required — Mac mini has no built-in microphone |
| Vision model | `ollama pull moondream` |

## API highlights

- `POST /api/chat` — main brain (supports `session_id` for voice follow-ups)
- `GET /api/memory` — long-term memory entries
- `POST /api/memory/compress` — summarize idle sessions into memory
- `GET /api/learning/report` — self-learning report
- `GET /api/sessions/active` — current conversation state

## Skills

Operational skills live in `jarvis/skills/*.md` and are injected into every prompt automatically.
