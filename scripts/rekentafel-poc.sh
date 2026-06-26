#!/usr/bin/env bash
# Rekentafel PoC — one command to run the full demo stack on Mac mini.
# Usage: ./scripts/rekentafel-poc.sh
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

step() { echo ""; echo "==> $1"; echo ""; }

step "Step 1/8 — Preparing environment"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo "Using existing .env"
fi

mkdir -p data/qr-codes

step "Step 2/8 — Starting Postgres (Docker)"
docker compose --profile postgres up -d

echo "Waiting for Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d rekentafel >/dev/null 2>&1; then
    echo "Postgres is ready."
    break
  fi
  sleep 1
done

step "Step 3/8 — Installing dependencies, migrating, seeding"
pnpm install
pnpm --filter @rekentafel/db db:migrate
pnpm --filter @rekentafel/db db:seed

step "Step 4/8 — Starting Rekentafel dev servers (API, guest, staff)"
pnpm dev:api &
API_PID=$!
pnpm dev:guest &
GUEST_PID=$!
pnpm dev:staff &
STAFF_PID=$!

sleep 4
if ! curl -sf http://127.0.0.1:3000/v1/health >/dev/null; then
  echo "Warning: API health check failed — continuing anyway."
else
  echo "API is up at http://localhost:3000/v1"
fi

step "Step 5/8 — Starting public tunnel (Caddy + Cloudflare)"
docker compose --profile proxy --profile public-quick up -d caddy cloudflared-quick

PUBLIC_URL=""
step "Step 6/8 — Waiting for public URL"
for i in $(seq 1 60); do
  PUBLIC_URL="$(docker compose logs cloudflared-quick 2>/dev/null | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)"
  if [[ -n "$PUBLIC_URL" ]]; then
    echo "Public URL: $PUBLIC_URL"
    echo "$PUBLIC_URL" > data/public-url.txt
    break
  fi
  sleep 2
done

if [[ -z "$PUBLIC_URL" ]]; then
  echo ""
  echo "Could not detect Cloudflare URL yet. Check: docker compose logs -f cloudflared-quick"
  echo "When you have the URL, set PUBLIC_BASE_URL in .env and re-run:"
  echo "  pnpm --filter @rekentafel/db db:seed && pnpm generate:qr"
  PUBLIC_URL="http://localhost:5173"
else
  step "Step 7/8 — Updating .env with public URL and re-seeding QR links"
  if grep -q '^PUBLIC_BASE_URL=' .env; then
    sed -i '' "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=$PUBLIC_URL|" .env
  else
    echo "PUBLIC_BASE_URL=$PUBLIC_URL" >> .env
  fi
  if grep -q '^MOLLIE_WEBHOOK_URL=' .env; then
    sed -i '' "s|^MOLLIE_WEBHOOK_URL=.*|MOLLIE_WEBHOOK_URL=$PUBLIC_URL/v1/webhooks/mollie|" .env
  else
    echo "MOLLIE_WEBHOOK_URL=$PUBLIC_URL/v1/webhooks/mollie" >> .env
  fi

  # Restart API so it picks up Mollie webhook URL
  kill "$API_PID" 2>/dev/null || true
  sleep 1
  pnpm dev:api &
  API_PID=$!
  sleep 3

  pnpm --filter @rekentafel/db db:seed

  step "Step 8/8 — Generating printable QR codes"
  pnpm generate:qr
fi

echo ""
echo "=============================================="
echo "  Rekentafel PoC is running"
echo "=============================================="
echo ""
echo "  Public guest site:  $PUBLIC_URL"
echo "  Staff web (browser): ${PUBLIC_URL}/staff/"
echo "  API health:         ${PUBLIC_URL}/v1/health"
echo ""
echo "  QR codes to print:  data/qr-codes/rekentafel-qr-sheet.pdf"
echo "                      data/qr-codes/T01.png … T04.png"
echo ""
echo "  Mollie (test mode):"
echo "    1. Get test key: https://www.mollie.com/dashboard/developers/api-keys"
echo "    2. Set MOLLIE_API_KEY=test_... in .env"
echo "    3. Restart API: kill the dev:api process and run: pnpm dev:api"
echo ""
echo "  Waiter iPhone app (on your MacBook):"
echo "    See docs/rekentafel/POC.md — build apps/waiter-mobile in Xcode"
echo ""
./scripts/print-network-urls.sh
echo ""
echo "  Press Ctrl+C to stop all dev servers."
echo "=============================================="
echo ""

cleanup() {
  echo "Stopping dev servers..."
  kill "$API_PID" "$GUEST_PID" "$STAFF_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
