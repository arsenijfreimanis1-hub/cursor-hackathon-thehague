#!/usr/bin/env bash
# One-shot setup for William's always-on screen observer + Notion relay.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== William Screen Observer setup ==="

if [[ -f "$ROOT/scripts/configure-notion.sh" ]]; then
  "$ROOT/scripts/configure-notion.sh" || echo "Notion not configured yet — screen summaries stay local until configured."
fi

source .venv/bin/activate 2>/dev/null || true

echo "Building JarvisHelper with ScreenWatcher..."
(cd "$ROOT/macos-helper" && swift build -c release)

echo "Seeding Notion Observer agent..."
python3 "$ROOT/scripts/seed-notion-observer-agent.py"

echo "Ensuring screen observer tables..."
python3 - <<'PY'
import asyncio
from jarvis.services import screen_observer, notion_sync

async def main():
    await screen_observer.ensure_tables()
    if notion_sync.configured():
        r = await notion_sync.ensure_screen_database()
        print("Notion screen database:", r)
    else:
        print("Notion not configured — skipping database setup")

asyncio.run(main())
PY

ENV_FILE="$ROOT/.env"
grep -q '^JARVIS_SCREEN_WATCH_ENABLED=' "$ENV_FILE" 2>/dev/null || echo 'JARVIS_SCREEN_WATCH_ENABLED=true' >> "$ENV_FILE"
grep -q '^JARVIS_SCREEN_CAPTURE_INTERVAL_SECONDS=' "$ENV_FILE" 2>/dev/null || echo 'JARVIS_SCREEN_CAPTURE_INTERVAL_SECONDS=10' >> "$ENV_FILE"
grep -q '^JARVIS_SCREEN_OBSERVER_INTERVAL_SECONDS=' "$ENV_FILE" 2>/dev/null || echo 'JARVIS_SCREEN_OBSERVER_INTERVAL_SECONDS=60' >> "$ENV_FILE"

if [[ -f "$ROOT/scripts/sync-launchd-env.sh" ]]; then
  "$ROOT/scripts/sync-launchd-env.sh"
fi

if [[ -f "$ROOT/scripts/install-helper.sh" ]]; then
  "$ROOT/scripts/install-helper.sh"
fi

if [[ -f "$ROOT/scripts/restart.sh" ]]; then
  "$ROOT/scripts/restart.sh" core
  "$ROOT/scripts/restart.sh" helper
fi

echo ""
echo "IMPORTANT: Grant Screen Recording to JarvisHelper in System Settings → Privacy & Security."
echo "Verify: curl -s http://127.0.0.1:8787/api/screen/status | python3 -m json.tool"
echo "Done."
