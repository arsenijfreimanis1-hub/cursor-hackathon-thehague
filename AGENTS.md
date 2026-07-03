# AGENTS.md

## Cursor Cloud specific instructions

### Scope: William Agent (Jarvis)
This repo contains two unrelated products. These notes cover **William Agent / Jarvis** —
the self-improving Python FastAPI agent in `jarvis/` (the "agent" product). The other product
(Rekentafel bill-splitting monorepo under `apps/` + `packages/`, and the Competitor Watchdog
idea) is out of scope here.

### Environment
- Python 3.12 with a virtualenv at `.venv` (gitignored). The update script creates it and installs
  `requirements.txt` + `requirements-dev.txt`. `self_modify.py` and the launchd plists expect the
  interpreter at `.venv/bin/python`.
- Runtime config is read from env vars prefixed `JARVIS_` or from a repo-root `.env` (see
  `.env.example`). SQLite state lives at `data/jarvis.db` (gitignored, auto-created on boot).

### Run / test / lint (agent)
- Tests: `.venv/bin/python -m pytest` (config in `pytest.ini`, tests in `tests/`).
- Run dev server: `.venv/bin/python -m uvicorn jarvis.main:app --host 127.0.0.1 --port 8787`.
  Chat UI at `/`, admin/control panel at `/admin`, health at `/api/health`.
- There is no separate lint config for the Python agent; `compileall` is used as the self-check
  (`self_modify.run_tests` runs `python -m compileall jarvis`). The root `pnpm lint`/CI is for the
  unrelated Rekentafel monorepo, not this agent.

### Non-obvious caveats
- The agent boots fully on Linux (DB, scheduler, worker, REST API, static UIs all work), but its
  optional integrations are **not reachable in the cloud VM**: Ollama (`:11434`), the macOS helper
  (`:8788`), the OpenClaw gateway, and the Cursor API key. `/api/health` will report these as
  `ok: false` — this is expected, not a setup failure.
- Because no LLM backend is present, `/api/chat` and LLM-backed agent invocation return
  `"Agent unavailable: All connection attempts failed"` and the created task is marked `failed`.
  The message→task→worker→event-log pipeline still runs. To get real chat replies, run Ollama
  locally or set a valid `CURSOR_API_KEY` in `.env`.
- Fully offline flows that need no external services: creating a specialist agent from an explicit
  spec via `POST /api/agents` (omit `authoring_prompt`), then `GET /api/agents`. Using
  `authoring_prompt` requires the Cursor backend.
- `macos-helper/` (Swift) and the voice/screen-observer features only run on macOS; ignore them on Linux.

See `docs/MEMORY_AND_SERVER.md` for the full service/port map and env-var reference.
