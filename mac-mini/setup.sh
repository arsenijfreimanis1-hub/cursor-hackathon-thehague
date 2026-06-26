#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Hackathon Mac mini setup"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "WARNING: Docker not found. Install Docker Desktop for Mac mini services."
else
  docker compose up -d
  echo "Postgres: localhost:5432 (hackathon/hackathon)"
  echo "Redis: localhost:6379"
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created mac-mini/.env — fill in API keys before sync."
fi

chmod +x "$SCRIPT_DIR"/*.sh
chmod +x "$REPO_ROOT/.cursor/hooks/auto-push.sh" 2>/dev/null || true

echo "==> Setup complete. Run ./sync-from-github.sh after teammates push."
