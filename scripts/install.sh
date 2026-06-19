#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="/opt/homebrew/bin/python3.12"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3.12"
fi

if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

PLIST_SRC="launchd/com.willy.jarvis-core.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.willy.jarvis-core.plist"

mkdir -p logs data
cp "$PLIST_SRC" "$PLIST_DST"

launchctl bootout "gui/$(id -u)/com.willy.jarvis-core" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.willy.jarvis-core"
launchctl kickstart -k "gui/$(id -u)/com.willy.jarvis-core"

echo "JarvisCore installed. Panel: http://127.0.0.1:8787"
