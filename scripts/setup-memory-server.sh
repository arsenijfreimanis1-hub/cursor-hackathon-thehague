#!/usr/bin/env bash
# One-shot setup: memory logging, backups, launchd, helper, optional Docker.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
ok() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }

echo "=== William Agent — memory & server setup ==="

# Python deps
PYTHON="/opt/homebrew/bin/python3.12"
[[ -x "$PYTHON" ]] || PYTHON="python3.12"
[[ -d .venv ]] || "$PYTHON" -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
ok "Python dependencies"

mkdir -p data logs backups
chmod +x scripts/*.sh

# Env template
[[ -f .env ]] || cp .env.example .env
grep -q '^JARVIS_NOTION_EXPORT_INTERVAL_HOURS=' .env 2>/dev/null || \
  echo "JARVIS_NOTION_EXPORT_INTERVAL_HOURS=12" >> .env

# Nightly SQLite backup (launchd — no Docker required)
PLIST_DST="$HOME/Library/LaunchAgents/com.willy.jarvis-backup.plist"
cp launchd/com.willy.jarvis-backup.plist "$PLIST_DST"
launchctl bootout "gui/$(id -u)/com.willy.jarvis-backup" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null || true
launchctl enable "gui/$(id -u)/com.willy.jarvis-backup" 2>/dev/null || true
./scripts/backup-db.sh
ok "SQLite backup job (3:15 AM daily)"

# Optional Docker stack
if command -v docker >/dev/null 2>&1; then
  docker compose --profile backup up -d 2>/dev/null || true
  DOCKER_PLIST_DST="$HOME/Library/LaunchAgents/com.willy.jarvis-docker.plist"
  cp launchd/com.willy.jarvis-docker.plist "$DOCKER_PLIST_DST"
  launchctl bootout "gui/$(id -u)/com.willy.jarvis-docker" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$DOCKER_PLIST_DST" 2>/dev/null || true
  launchctl enable "gui/$(id -u)/com.willy.jarvis-docker" 2>/dev/null || true
  ok "Docker backup profile (if compose available)"
elif command -v brew >/dev/null 2>&1; then
  if ! docker compose version &>/dev/null; then
    brew install colima docker docker-compose 2>/dev/null || true
    mkdir -p "$HOME/.docker"
    python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".docker" / "config.json"
cfg = json.loads(p.read_text()) if p.is_file() else {}
cfg.setdefault("cliPluginsExtraDirs", [])
extra = "/opt/homebrew/lib/docker/cli-plugins"
if extra not in cfg["cliPluginsExtraDirs"]:
    cfg["cliPluginsExtraDirs"].append(extra)
p.write_text(json.dumps(cfg, indent=2) + "\n")
PY
    colima start --cpu 2 --memory 4 2>/dev/null || brew services start colima 2>/dev/null || true
  fi
  if docker compose version &>/dev/null; then
    docker compose --profile backup up -d 2>/dev/null || true
    DOCKER_PLIST_DST="$HOME/Library/LaunchAgents/com.willy.jarvis-docker.plist"
    cp launchd/com.willy.jarvis-docker.plist "$DOCKER_PLIST_DST"
    launchctl bootout "gui/$(id -u)/com.willy.jarvis-docker" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$DOCKER_PLIST_DST" 2>/dev/null || true
    launchctl enable "gui/$(id -u)/com.willy.jarvis-docker" 2>/dev/null || true
    ok "Docker backup profile + launchd auto-heal"
  else
    warn "Docker optional — launchd backups active"
  fi
fi

# Core services
./scripts/sync-launchd-env.sh
./scripts/install.sh
./scripts/install-helper.sh
ok "JarvisCore + helper (launchd)"

# Permissions (non-blocking)
curl -sf -X POST http://127.0.0.1:8788/permissions/prompt >/dev/null 2>&1 || true

# Notion (skip silently in non-interactive shells)
if ! ./scripts/configure-notion.sh 2>/dev/null; then
  warn "Notion skipped — run ./scripts/configure-notion.sh in Terminal when ready"
fi

# Initialize event log tables
python3 - <<'PY'
import asyncio
from jarvis.services import event_log

async def main():
    epoch = await event_log.ensure_memory_epoch()
    print(f"memory_since={epoch}")

asyncio.run(main())
PY
ok "Interaction event log initialized"

sleep 2
./scripts/server-status.sh

echo ""
ok "Setup complete"
echo "  Chat:  http://127.0.0.1:8787/"
echo "  Admin: http://127.0.0.1:8787/admin"
echo "  Logs:  GET /api/events"
