#!/usr/bin/env bash
# Optional screenpipe bridge — installs screenpipe and enables JARVIS_SCREENPIPE_BRIDGE_ENABLED.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"

echo "=== screenpipe bridge (optional) ==="
echo "Install screenpipe from https://github.com/mediar-ai/screenpipe or https://screenpipe.com"
echo "Then enable Notion connection in screenpipe Settings → Connections."

if ! grep -q '^JARVIS_SCREENPIPE_BRIDGE_ENABLED=' "$ENV_FILE" 2>/dev/null; then
  echo 'JARVIS_SCREENPIPE_BRIDGE_ENABLED=true' >> "$ENV_FILE"
else
  sed -i '' 's/^JARVIS_SCREENPIPE_BRIDGE_ENABLED=.*/JARVIS_SCREENPIPE_BRIDGE_ENABLED=true/' "$ENV_FILE" 2>/dev/null \
    || sed -i 's/^JARVIS_SCREENPIPE_BRIDGE_ENABLED=.*/JARVIS_SCREENPIPE_BRIDGE_ENABLED=true/' "$ENV_FILE"
fi

grep -q '^JARVIS_SCREENPIPE_BASE_URL=' "$ENV_FILE" 2>/dev/null || echo 'JARVIS_SCREENPIPE_BASE_URL=http://127.0.0.1:3030' >> "$ENV_FILE"

if [[ -f "$ROOT/scripts/sync-launchd-env.sh" ]]; then
  "$ROOT/scripts/sync-launchd-env.sh"
fi
if [[ -f "$ROOT/scripts/restart.sh" ]]; then
  "$ROOT/scripts/restart.sh" core
fi
echo "Bridge enabled. Start screenpipe, then verify: curl http://127.0.0.1:8787/api/screen/status"
