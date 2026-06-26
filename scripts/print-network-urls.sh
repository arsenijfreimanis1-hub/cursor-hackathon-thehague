#!/usr/bin/env bash
# Print LAN URLs for phones on Titaan Members Wi‑Fi
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Prefer en0 (Wi‑Fi) then en1
IP=""
for iface in en0 en1; do
  IP="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
  if [[ -n "$IP" ]]; then break; fi
done

if [[ -z "$IP" ]]; then
  echo "Could not detect LAN IP. Set VITE_LAN_HOST manually in .env"
  exit 1
fi

echo ""
echo "=============================================="
echo "  Titaan Members Wi‑Fi — phone URLs"
echo "=============================================="
echo ""
echo "  Guest (scan / browse):  http://${IP}:5173"
echo "  Waiter app (browser):   http://${IP}:5174"
echo "  API:                    http://${IP}:3000/v1/health"
echo ""
echo "  Add to .env:"
echo "    VITE_LAN_HOST=${IP}"
echo ""

if [[ -f .env ]]; then
  if grep -q '^VITE_LAN_HOST=' .env; then
    sed -i '' "s|^VITE_LAN_HOST=.*|VITE_LAN_HOST=${IP}|" .env
  else
    echo "VITE_LAN_HOST=${IP}" >> .env
  fi
  echo "  Updated .env with VITE_LAN_HOST=${IP}"
else
  echo "  Tip: cp .env.example .env first"
fi
echo "=============================================="
echo ""
