#!/bin/bash
# Expose local API (port 4000) via Cloudflare quick tunnel for n8n webhooks.
set -euo pipefail

PORT="${API_PORT:-4000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Install cloudflared:"
  echo "  brew install cloudflared"
  echo "  or: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

echo "Starting tunnel to http://localhost:${PORT}"
echo "Copy the https://*.trycloudflare.com URL to README Integration Contracts → PUBLIC_WEBHOOK_URL"
cloudflared tunnel --url "http://localhost:${PORT}"
