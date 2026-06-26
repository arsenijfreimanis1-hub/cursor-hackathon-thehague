#!/bin/bash
# Pull latest from GitHub and apply integration updates on Mac mini.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "==> $(date -u +%Y-%m-%dT%H:%M:%SZ) sync-from-github"

git fetch origin 2>/dev/null || true
git pull --rebase origin main 2>/dev/null || git pull --rebase 2>/dev/null || true

# Load mac-mini secrets if present
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Restart Docker services if compose file changed
if command -v docker >/dev/null 2>&1 && [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
  docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
fi

# Print latest changelog line for operator
echo "--- Latest README changelog ---"
grep -A1 "## Changelog" "$REPO_ROOT/README.md" | tail -5 || true

# Optional: start API if apps/api exists and has package.json
if [ -f "$REPO_ROOT/apps/api/package.json" ]; then
  echo "API found at apps/api — run manually: cd apps/api && npm install && npm run dev"
fi

echo "==> Sync complete. Check README Integration Contracts for new webhook URLs."
