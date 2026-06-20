#!/usr/bin/env bash
# Grant permissions for William Agent (run once, approve in System Settings)
echo "Requesting permissions from JarvisHelper (one prompt)…"
curl -sf -X POST http://127.0.0.1:8788/permissions/prompt >/dev/null 2>&1 || true
echo "Opening System Settings…"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
echo ""
echo "Enable JarvisHelper for:"
echo "  • Microphone"
echo "  • Speech Recognition"
echo "  • Accessibility (mouse/keyboard control)"
echo ""
echo "Then restart helper:"
echo "  launchctl kickstart -k gui/\$(id -u)/com.willy.jarvis-helper"
