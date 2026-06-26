#!/bin/bash
# Run all integration smoke tests. Requires .env.local with API keys for cloud tests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-.env.local}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

PASS=0
FAIL=0
SKIP=0

run_test() {
  local name="$1"
  shift
  echo ""
  echo "=== $name ==="
  if "$@"; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name"
    FAIL=$((FAIL + 1))
  fi
}

skip_test() {
  local name="$1"
  local reason="$2"
  echo ""
  echo "=== $name ==="
  echo "SKIP: $reason"
  SKIP=$((SKIP + 1))
}

# 1. API health (local)
run_test "API /health" "$ROOT/scripts/smoke-test/test-api-health.sh"

# 2. n8n webhook receiver on API
run_test "n8n webhook POST /webhooks/n8n" "$ROOT/scripts/smoke-test/test-n8n-webhook.sh"

# 3. Apify account
if [ -n "${APIFY_TOKEN:-}" ]; then
  run_test "Apify API user" "$ROOT/scripts/smoke-test/test-apify.sh"
else
  skip_test "Apify API" "APIFY_TOKEN not set in $ENV_FILE"
fi

# 4. ElevenLabs TTS
if [ -n "${ELEVENLABS_API_KEY:-}" ]; then
  run_test "ElevenLabs TTS" "$ROOT/scripts/smoke-test/test-elevenlabs.sh"
else
  skip_test "ElevenLabs TTS" "ELEVENLABS_API_KEY not set in $ENV_FILE"
fi

echo ""
echo "Results: $PASS passed, $FAIL failed, $SKIP skipped"
[ "$FAIL" -eq 0 ]
