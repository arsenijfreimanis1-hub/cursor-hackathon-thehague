#!/bin/bash
# Create .env.local from template (run once on each machine).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/.env.local" ]; then
  echo ".env.local already exists — edit manually."
  exit 0
fi
cp "$ROOT/.env.example" "$ROOT/.env.local"
echo "Created .env.local — add your keys:"
echo "  APIFY_TOKEN=       (console.apify.com → Integrations)"
echo "  N8N_API_KEY=       (n8n → Settings → API)"
echo "  N8N_BASE_URL=      (e.g. https://your.app.n8n.cloud)"
echo ""
echo "Then run: ./scripts/connect-services.sh"
