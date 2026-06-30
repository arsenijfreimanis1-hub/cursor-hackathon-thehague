#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}!${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }

echo "=== William Agent — full setup ==="
echo ""

# 1. Python deps
PYTHON="/opt/homebrew/bin/python3.12"
[[ -x "$PYTHON" ]] || PYTHON="python3.12"
if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
ok "Python dependencies installed"

# 2. Ollama models
if command -v ollama >/dev/null 2>&1; then
  RAM_GB=$(sysctl -n hw.memsize | awk '{printf "%.0f", $1/1024/1024/1024}')
  TARGET="llama3.1:8b"
  if [[ "$RAM_GB" -lt 12 ]]; then
    TARGET="llama3.2:3b"
    warn "RAM ${RAM_GB}GB — keeping fast model llama3.2:3b"
  else
    ok "RAM ${RAM_GB}GB — pulling ${TARGET} for better local reasoning"
    ollama pull "$TARGET" || warn "Could not pull $TARGET — will use existing models"
  fi
  ollama pull moondream 2>/dev/null || warn "moondream pull skipped (vision optional)"
  if ! grep -q '^JARVIS_OLLAMA_MODEL=' .env 2>/dev/null; then
    echo "JARVIS_OLLAMA_MODEL=$TARGET" >> .env
    ok "Set JARVIS_OLLAMA_MODEL=$TARGET in .env"
  fi
else
  warn "ollama not found — install with: brew install ollama"
fi

# 3. Cursor API key check
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp .env.example .env

KEY_OK=$(python3 - <<'PY'
from jarvis.config import settings
print("yes" if settings.cursor_configured() else "no")
PY
)

if [[ "$KEY_OK" != "yes" ]]; then
  warn "CURSOR_API_KEY missing — opening secure prompt…"
  if ./scripts/configure-cursor-key.sh; then
    KEY_OK=yes
    ok "Cursor API key configured"
  else
    echo ""
    echo "  Manual setup:"
    echo "  1. Open https://cursor.com/dashboard/integrations"
    echo "  2. Create a User API Key"
    echo "  3. Run: ./scripts/configure-cursor-key.sh"
    echo ""
  fi
else
  ok "Cursor API key configured"
fi

# 4. Install services
chmod +x scripts/*.sh
VOICE_BACKEND="${WILLIAM_VOICE_BACKEND:-$(awk -F= '/^WILLIAM_VOICE_BACKEND=/{print $2}' .env 2>/dev/null | tail -n1)}"
if [[ "$VOICE_BACKEND" == "local_openwakeword_whisper" ]]; then
  ./scripts/setup-local-voice.sh
  ok "Local offline voice stack installed"
fi
./scripts/sync-launchd-env.sh
./scripts/install.sh
./scripts/install-helper.sh
ok "JarvisCore + macOS helper installed"

# 4b. OpenClaw WhatsApp bridge
if command -v openclaw >/dev/null 2>&1; then
  ./scripts/fix-openclaw.sh || warn "OpenClaw/WhatsApp setup incomplete — run ./scripts/fix-openclaw.sh"
else
  warn "openclaw not installed — WhatsApp bridge skipped (npm install -g openclaw)"
fi

# 4c. Retire separate kiosk — JarvisHelper menubar + web panel are the unified UI
./scripts/uninstall-kiosk.sh 2>/dev/null || warn "Kiosk uninstall skipped"

# 5. Memory & server stack
./scripts/setup-memory-server.sh 2>/dev/null || warn "Memory/server setup partial — run ./scripts/setup-memory-server.sh"

# 6. Permissions (opens System Settings — requires your click)
echo ""
warn "Granting permissions — approve in System Settings if prompted:"
open "$ROOT/macos-helper/JarvisHelper.app" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || true
if [[ "$VOICE_BACKEND" != "local_openwakeword_whisper" ]]; then
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition" 2>/dev/null || true
fi
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true

# 6. Health check
sleep 3
echo ""
echo "=== Health check ==="
HEALTH=$(curl -s http://127.0.0.1:8787/api/health 2>/dev/null || echo '{}')
python3 - <<PY
import json, sys
h = json.loads('''$HEALTH''')
print(f"  Ollama:      {'OK' if h.get('ollama',{}).get('ok') else 'DOWN'} ({h.get('ollama',{}).get('default','?')})")
print(f"  Helper:      {'OK' if h.get('macos_helper',{}).get('ok') else 'DOWN'}")
print(f"  Cursor:      {'OK' if h.get('cursor',{}).get('configured') else 'NEEDS KEY'}")
print(f"  Worker:      {'OK' if h.get('worker',{}).get('running') else 'DOWN'}")
print(f"  Mic:         {h.get('macos_helper',{}).get('permissions',{}).get('microphone','?')}")
print(f"  Accessibility: {h.get('macos_helper',{}).get('accessibility', False)}")
oc = h.get('openclaw', {})
print(f"  OpenClaw:    {'OK' if oc.get('whatsapp') else 'DOWN'} (bridge={'yes' if oc.get('bridge') else 'no'})")
PY

echo ""
echo "Panel: http://127.0.0.1:8787"
echo "Restart anytime: ./scripts/restart.sh"
echo ""
if [[ "$KEY_OK" != "yes" ]]; then
  fail "Add CURSOR_API_KEY to .env, then: ./scripts/setup-all.sh"
  exit 1
fi
ok "William is ready. Say: Hey Willy"
