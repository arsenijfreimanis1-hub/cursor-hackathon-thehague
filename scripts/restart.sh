#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN="gui/$(id -u)"
CORE="com.willy.jarvis-core"
HELPER="com.willy.jarvis-helper"

restart_one() {
  local label="$1"
  local plist="$HOME/Library/LaunchAgents/${label}.plist"
  if [[ ! -f "$plist" ]]; then
    echo "Missing plist: $plist"
    echo "Run: ./scripts/install.sh"
    return 1
  fi
  if ! launchctl kickstart -k "$DOMAIN/$label" 2>/dev/null; then
    echo "Kickstart failed for $label, bootstrapping..."
    launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$plist"
    launchctl enable "$DOMAIN/$label" 2>/dev/null || true
    launchctl kickstart "$DOMAIN/$label"
  fi
  echo "Restarted $label"
}

TARGET="${1:-both}"
case "$TARGET" in
  jarvis|core) restart_one "$CORE" ;;
  helper) restart_one "$HELPER" ;;
  both|*)
    restart_one "$HELPER"
    restart_one "$CORE"
    ;;
esac

sleep 2
echo ""
echo "Health: http://127.0.0.1:8787/api/health"
curl -s http://127.0.0.1:8787/api/health | python3 -m json.tool 2>/dev/null || echo "JarvisCore not responding yet"
