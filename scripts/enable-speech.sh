#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${WILLIAM_VOICE_BACKEND:-$(awk -F= '/^WILLIAM_VOICE_BACKEND=/{print $2}' "$ROOT/.env" 2>/dev/null | tail -n1)}"

if [[ "$BACKEND" == "local_openwakeword_whisper" ]]; then
  echo "William Agent is set to the local offline voice stack."
  echo ""
  echo "Only microphone permission is required for the helper."
  echo "Speech Recognition / Siri / Dictation are not needed."
  echo ""
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || \
    open "/System/Applications/System Settings.app" 2>/dev/null || true
  echo "Then run:"
  echo "  $ROOT/scripts/grant-voice-permissions.sh"
  echo "  $ROOT/scripts/install-helper.sh"
  exit 0
fi

echo "William Agent needs Siri AND Dictation enabled on macOS."
echo ""
echo "Opening System Settings…"
echo ""

open "x-apple.systempreferences:com.apple.Keyboard-Settings.extension?Dictation" 2>/dev/null || \
  open "/System/Applications/System Settings.app" 2>/dev/null || true

sleep 1
open "x-apple.systempreferences:com.apple.Siri-Settings.extension" 2>/dev/null || true

echo "Enable BOTH:"
echo "  1. System Settings → Keyboard → Dictation → ON"
echo "  2. System Settings → Apple Intelligence & Siri → ON (or Siri → Enable)"
echo ""
echo "Then grant permissions when prompted:"
echo "  $ROOT/scripts/grant-voice-permissions.sh"
echo ""
echo "Restart helper:"
echo "  launchctl kickstart -k gui/\$(id -u)/com.willy.jarvis-helper"
