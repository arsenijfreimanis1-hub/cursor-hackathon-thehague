#!/usr/bin/env bash
# Keep William awake — run manually or via cron every 5 min.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

kick() {
  local label="$1"
  launchctl kickstart -k "${DOMAIN}/${label}" 2>/dev/null \
    || launchctl bootstrap "${DOMAIN}" "$HOME/Library/LaunchAgents/${label}.plist" 2>/dev/null \
    || true
}

curl -sf http://127.0.0.1:8787/api/voice/ensure-awake >/dev/null 2>&1 \
  || kick com.willy.jarvis-core

HEALTH=$(curl -sf http://127.0.0.1:8787/api/health 2>/dev/null || echo '{}')
HELPER_OK=$(echo "$HEALTH" | python3 -c "import json,sys; h=json.load(sys.stdin); print('yes' if h.get('macos_helper',{}).get('ok') else 'no')" 2>/dev/null || echo no)
HEALTHY=$(echo "$HEALTH" | python3 -c "import json,sys; h=json.load(sys.stdin); m=h.get('macos_helper',{}); print('yes' if m.get('healthy') else 'no')" 2>/dev/null || echo no)

if [[ "$HELPER_OK" != "yes" || "$HEALTHY" != "yes" ]]; then
  PERMS_PENDING=$(echo "$HEALTH" | python3 -c "import json,sys; h=json.load(sys.stdin); p=h.get('macos_helper',{}).get('permissions',{}); print('yes' if p.get('microphone') in ('undetermined','denied') or p.get('speech') in ('undetermined','denied','restricted') else 'no')" 2>/dev/null || echo no)
  if [[ "$PERMS_PENDING" != "yes" ]]; then
    kick com.willy.jarvis-helper
    sleep 2
    curl -sf -X POST http://127.0.0.1:8787/api/voice/ensure-awake >/dev/null 2>&1 || true
  fi
fi

echo "William ensure-awake done (helper_ok=$HELPER_OK healthy=$HEALTHY)"
