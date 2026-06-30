#!/usr/bin/env bash
# User-initiated permission setup — triggers macOS TCC dialogs (run once).
# For automated bootstrap without popup spam, use bootstrap-permissions.sh instead.
set -euo pipefail

echo "Requesting permissions from JarvisHelper (user-initiated TCC prompts)…"
curl -sf -X POST http://127.0.0.1:8788/permissions/prompt >/dev/null 2>&1 || true
echo "Opening System Settings…"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition" 2>/dev/null || true
echo ""
echo "Enable JarvisHelper for:"
echo "  • Accessibility (enables native dialog clicking — no screen recording needed)"
echo "  • Screen Recording (ScreenWatcher capture — NOT Notion)"
echo "  • Microphone"
echo "  • Speech Recognition"
echo ""
echo "Then restart helper:"
echo "  launchctl kickstart -k gui/\$(id -u)/com.willy.jarvis-helper"
