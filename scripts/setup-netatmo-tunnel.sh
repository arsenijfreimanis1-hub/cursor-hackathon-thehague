#!/usr/bin/env bash
set -euo pipefail

# Netatmo webhooks require HTTPS on port 443.
# This script starts a Cloudflare quick tunnel to expose JarvisCore's webhook.

if ! command -v cloudflared >/dev/null; then
  echo "Installing cloudflared..."
  brew install cloudflared
fi

echo ""
echo "Starting tunnel to http://127.0.0.1:8787/api/netatmo/webhook"
echo "Copy the https://*.trycloudflare.com URL into your Netatmo developer app:"
echo "  https://dev.netatmo.com/apps"
echo ""
echo "Webhook path: /api/netatmo/webhook"
echo ""

cloudflared tunnel --url http://127.0.0.1:8787
