# Cursor SDK Skill

William uses the **Cursor Agent SDK** (`@cursor/sdk`) as a tool — not the Cursor IDE app. Willy never needs to open Cursor to change William's code.

## When to use

| Task | Tool | Entry point |
|------|------|-------------|
| Edit William's own code (jarvis-core) | `self_modify.propose()` | Voice/chat: "improve yourself: …" |
| General code in workspace | `cursor_agent.run()` | Router escalation or build pipeline |
| Quick reasoning | `cursor_agent.run_reasoning()` | Fact/reason intents |
| Autonomous fix loop | `improve_run.start()` | "run improve loop for 30 minutes" |

## SDK invocation rules

1. **Local runtime** (default): edits files on the Mac mini at `JARVIS_WORKSPACE_DIR`.
2. **Cloud runtime**: requires `repo_url` + `branch` — used by compute fleet for parallel slices.
3. Always inject MCP servers from `mcp_config.load_mcp_servers()`.
4. Load domain skills into the prompt via `skills.load_skills_block(domains=…)`.
5. For jarvis-core self-changes: use sandbox branch (`sandbox/YYYYMMDD-HHMMSS`), never commit directly to main without merge gate.

## Self-modify voice/chat phrases

- `improve yourself: add dark mode to admin`
- `self-modify: fix the minis touch mapping`
- `change your code to …`
- `fix yourself: …`

William creates a sandbox branch, runs Cursor SDK, and merges when full access is on (or queues approval).

## Response style

- Voice/messaging: one short sentence summarizing what changed.
- Web chat: brief summary + branch name if sandboxed.
- Never tell Willy to "open Cursor" — William runs the SDK internally.

## Prerequisites

- `CURSOR_API_KEY` in `.env` or environment
- Repo initialized at workspace_dir (`self_modify.ensure_repo()`)

## Not this skill

- Opening apps on screen → `system_control`
- Terminal one-liners → `terminal.execute`
- External project builds → `build_pipeline` (uses Cursor SDK per slice)
