#!/usr/bin/env bash
# One-command Rekentafel local stack: Postgres, migrate, seed, dev services.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example — review DATABASE_URL and DEV_VENUE_ID after seed."
  cp .env.example .env
fi

echo "Starting Postgres..."
docker compose --profile postgres up -d

echo "Waiting for Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres -d rekentafel >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Running migrations and seed..."
pnpm install
pnpm --filter @rekentafel/db db:migrate
pnpm --filter @rekentafel/db db:seed

echo ""
echo "Rekentafel stack ready. Starting dev servers..."
echo "  API:        http://localhost:3000/v1/health"
echo "  Guest web:  http://localhost:5173"
echo "  Staff PWA:  http://localhost:5174"
echo ""
echo "Tip: set DEV_VENUE_ID in .env from seed output if not already set."
echo ""

pnpm dev:api &
API_PID=$!
pnpm dev:guest &
GUEST_PID=$!
pnpm dev:staff &
STAFF_PID=$!

cleanup() {
  kill "$API_PID" "$GUEST_PID" "$STAFF_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
