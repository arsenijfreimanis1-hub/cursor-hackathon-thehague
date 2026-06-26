#!/bin/bash
set -euo pipefail
: "${ELEVENLABS_API_KEY:?ELEVENLABS_API_KEY required}"

VOICE_ID="${ELEVENLABS_VOICE_ID:-21m00Tcm4TlvDq8ikWAM}"
OUT="$(cd "$(dirname "$0")/../.." && pwd)/apps/voice/assets/smoke-test.mp3"

mkdir -p "$(dirname "$OUT")"

HTTP=$(curl -sf -w "%{http_code}" -o "$OUT" \
  -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
  -H "xi-api-key: ${ELEVENLABS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hackathon smoke test. Integrations are working.","model_id":"eleven_multilingual_v2"}')

[ "$HTTP" = "200" ] && [ -s "$OUT" ]
