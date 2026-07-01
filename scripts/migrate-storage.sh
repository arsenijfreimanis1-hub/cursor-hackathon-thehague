#!/usr/bin/env bash
# Move William runtime state from jarvis-core/ into ~/Library (Mac mini internal storage).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/jarvis-paths.sh
source "$ROOT/scripts/jarvis-paths.sh"

STATE="$HOME/Library/Application Support/Jarvis"
DATA="$STATE/data"
LOGS="$HOME/Library/Logs/Jarvis"
BACKUPS="$STATE/backups"
MODELS="$STATE/models"

echo "William storage migration"
echo "  Repo:   $ROOT"
echo "  State:  $STATE"
echo "  Data:   $DATA"
echo "  Logs:   $LOGS"

mkdir -p "$DATA" "$BACKUPS" "$MODELS/whisper" "$LOGS" \
  "$STATE/agents" "$STATE/cache/skills" "$STATE/cache/cursor-traces"

for sub in data backups models; do
  src="$ROOT/$sub"
  if [[ -d "$src" ]] && [[ -n "$(ls -A "$src" 2>/dev/null || true)" ]]; then
    echo "→ rsync $src → $STATE/$sub/"
    mkdir -p "$STATE/$sub"
    rsync -a "$src/" "$STATE/$sub/"
  fi
done

if [[ -d "$ROOT/logs" ]]; then
  echo "→ rsync logs"
  rsync -a "$ROOT/logs/" "$LOGS/" || true
fi

ENV_FILE="$ROOT/.env"
touch "$ENV_FILE"
upsert_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i '' "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

upsert_env JARVIS_DATA_DIR "$DATA"
upsert_env JARVIS_STATE_ROOT "$STATE"
upsert_env JARVIS_LOGS_DIR "$LOGS"
upsert_env JARVIS_WORKSPACE_DIR "$ROOT"

echo ""
echo "Done. Next:"
echo "  ./scripts/sync-launchd-env.sh"
echo "  ./scripts/restart.sh"
