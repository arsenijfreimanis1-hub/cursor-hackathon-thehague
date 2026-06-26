#!/usr/bin/env bash
# Start Rekentafel with a public URL via Cloudflare quick tunnel (cloudflared-quick profile).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p data

echo "Starting Caddy proxy + Cloudflare quick tunnel..."
docker compose --profile proxy --profile public-quick up -d caddy cloudflared-quick

echo "Waiting for public URL..."
for i in $(seq 1 60); do
  URL="$(docker compose logs cloudflared-quick 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)"
  if [[ -n "$URL" ]]; then
    echo "$URL" > data/rekentafel-public-url.txt
    echo ""
    echo "Public Rekentafel URL: $URL"
    echo ""
    echo "Add to .env:"
    echo "  PUBLIC_BASE_URL=$URL"
    echo "  MOLLIE_WEBHOOK_URL=$URL/v1/webhooks/mollie"
    echo ""
    echo "Then re-seed QR codes: pnpm --filter @rekentafel/db db:seed"
    echo "Staff app: $URL/staff/"
    exit 0
  fi
  sleep 2
done

echo "Tunnel starting — check logs: docker compose logs -f cloudflared-quick"
exit 1
