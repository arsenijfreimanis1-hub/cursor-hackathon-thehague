#!/usr/bin/env bash
# Fix OpenClaw gateway version skew and reconnect WhatsApp → JarvisCore bridge.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== OpenClaw + WhatsApp repair ==="

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI not found — install: npm install -g openclaw"
  exit 1
fi

VER="$(openclaw --version 2>/dev/null | head -1 || true)"
echo "CLI: $VER"

# Fix allowlist typo if present
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".openclaw" / "openclaw.json"
if not p.is_file():
    raise SystemExit(0)
data = json.loads(p.read_text())
wa = data.get("channels", {}).get("whatsapp", {})
nums = wa.get("allowFrom", [])
fixed = []
for n in nums:
    if n == "+316292447466":
        fixed.append("+31629247466")
    else:
        fixed.append(n)
if fixed != nums:
    wa["allowFrom"] = fixed
    data.setdefault("channels", {})["whatsapp"] = wa
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("Fixed WhatsApp allowFrom phone number")
PY

echo "Reinstalling gateway service (matches CLI version)…"
openclaw gateway install --force 2>/dev/null || openclaw gateway install 2>/dev/null || true

echo "Fixing OpenClaw state permissions…"
chmod -R u+rwX "$HOME/.openclaw/state" 2>/dev/null || true

echo "Applying doctor fixes + WhatsApp plugin…"
openclaw doctor --fix 2>/dev/null || true
openclaw plugins install clawhub:@openclaw/whatsapp 2>/dev/null || true

echo "Pairing WhatsApp if needed…"
openclaw channels login --channel whatsapp 2>/dev/null || true
"$ROOT/scripts/install-openclaw-bridge.sh"

UID_NUM="$(id -u)"
launchctl kickstart -k "gui/$UID_NUM/ai.openclaw.gateway" 2>/dev/null || true

echo "Waiting for WhatsApp channel…"
for i in $(seq 1 18); do
  if tail -200 "$HOME/.openclaw/logs/gateway.log" "$HOME/Library/Logs/openclaw/gateway.log" /tmp/openclaw/openclaw-*.log 2>/dev/null | grep -q "Listening for WhatsApp inbound messages"; then
    echo "WhatsApp connected."
    if curl -sf http://127.0.0.1:8787/api/health >/dev/null 2>&1; then
      curl -s http://127.0.0.1:8787/api/health | python3 -c "import json,sys; h=json.load(sys.stdin); o=h.get('openclaw',{}); print('  bridge:', o.get('bridge'), 'whatsapp:', o.get('whatsapp'))" 2>/dev/null || true
    fi
    exit 0
  fi
  sleep 5
done

echo "WhatsApp did not start. Try:"
echo "  openclaw channels login whatsapp   # scan QR on phone"
echo "  openclaw channels status"
echo "  openclaw doctor --fix"
exit 1
