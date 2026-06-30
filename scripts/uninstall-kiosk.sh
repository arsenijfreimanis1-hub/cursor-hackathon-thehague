#!/usr/bin/env bash
# Stop and remove WilliamKiosk — JarvisHelper menubar app is the single UI.
set -euo pipefail

UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"
LABEL="com.willy.william-kiosk"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
pkill -f "WilliamKiosk.app/Contents/MacOS/WilliamKiosk" 2>/dev/null || true
pkill -f ".build/release/WilliamKiosk" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"

echo "WilliamKiosk removed. Use JarvisHelper menubar + http://127.0.0.1:8787/ for controls."
