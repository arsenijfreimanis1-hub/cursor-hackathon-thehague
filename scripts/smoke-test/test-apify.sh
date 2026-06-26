#!/bin/bash
set -euo pipefail
: "${APIFY_TOKEN:?APIFY_TOKEN required}"

RESP=$(curl -sf -H "Authorization: Bearer ${APIFY_TOKEN}" \
  "https://api.apify.com/v2/users/me")

echo "$RESP" | grep -q '"username"'
