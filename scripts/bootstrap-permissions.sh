#!/usr/bin/env bash
# One-shot permission bootstrap — opens settings panes, no TCC popup spam.
# For user-initiated TCC prompts (first-time setup), use grant-voice-permissions.sh instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Bootstrapping JarvisHelper permissions (settings panes only)…"
curl -sf -X POST "http://127.0.0.1:8787/api/permissions/bootstrap" | python3 -m json.tool 2>/dev/null || \
  curl -sf -X POST "http://127.0.0.1:8788/permissions/bootstrap" | python3 -m json.tool 2>/dev/null || true

echo ""
echo "If toggles did not auto-enable, manually enable JarvisHelper for:"
echo "  • Accessibility (required first — enables native dialog handler)"
echo "  • Screen Recording (capture layer — NOT Notion)"
echo "  • Microphone + Speech Recognition (apple_legacy voice)"
echo ""
echo "User-initiated TCC prompts (menubar → Grant permissions…):"
echo "  curl -X POST http://127.0.0.1:8788/permissions/prompt"
