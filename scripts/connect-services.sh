#!/bin/bash
# Verify connections to activated partner APIs. Reads .env.local at repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.local}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "Loaded: $ENV_FILE"
else
  echo "WARNING: No $ENV_FILE — create from .env.example and add your keys."
fi

echo ""
echo "=== Connection report ==="

# Apify
if [ -n "${APIFY_TOKEN:-}" ]; then
  if RESP=$(curl -sf -H "Authorization: Bearer ${APIFY_TOKEN}" "https://api.apify.com/v2/users/me" 2>&1); then
    USER=$(echo "$RESP" | jq -r '.data.username // .username // "ok"')
    echo "✅ Apify: connected as $USER"
  else
    echo "❌ Apify: failed — check APIFY_TOKEN"
  fi
else
  echo "⏭  Apify: APIFY_TOKEN not set"
fi

# n8n Cloud API
if [ -n "${N8N_API_KEY:-}" ] && [ -n "${N8N_BASE_URL:-}" ]; then
  if curl -sf -H "X-N8N-API-KEY: ${N8N_API_KEY}" "${N8N_BASE_URL%/}/api/v1/workflows?limit=1" >/dev/null 2>&1; then
    echo "✅ n8n: API reachable at $N8N_BASE_URL"
  else
    echo "❌ n8n: API call failed — check N8N_API_KEY and N8N_BASE_URL"
  fi
elif [ -n "${N8N_API_KEY:-}" ]; then
  echo "⏭  n8n: N8N_API_KEY set but N8N_BASE_URL missing (e.g. https://your.app.n8n.cloud)"
else
  echo "⏭  n8n: N8N_API_KEY not set"
fi

# ElevenLabs (optional — team has not activated yet)
if [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  if curl -sf -H "xi-api-key: ${ELEVENLABS_API_KEY}" "https://api.elevenlabs.io/v1/user" >/dev/null 2>&1; then
    echo "✅ ElevenLabs: connected"
  else
    echo "❌ ElevenLabs: invalid key"
  fi
else
  echo "⏭  ElevenLabs: not activated (optional stretch)"
fi

# Fluxzero (optional)
if [ -n "${FLUXZERO_API_KEY:-}" ]; then
  echo "✅ Fluxzero: key present (manual verify at fluxzero.io)"
else
  echo "⏭  Fluxzero: not activated (not using for this product)"
fi

# Local API
if curl -sf "http://localhost:${API_PORT:-4000}/health" >/dev/null 2>&1; then
  echo "✅ Local API: running on port ${API_PORT:-4000}"
else
  echo "⏭  Local API: not running (start: cd Tarik/api && npm run dev)"
fi

echo ""
echo "Full smoke suite: ./scripts/smoke-test/run-all.sh"
