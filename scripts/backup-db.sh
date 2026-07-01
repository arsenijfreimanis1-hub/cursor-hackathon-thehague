#!/usr/bin/env bash
# Copy SQLite DB to backups with timestamp. Keeps last 14 copies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/jarvis-paths.sh
source "$ROOT/scripts/jarvis-paths.sh"

DB="$JARVIS_DATA_DIR/jarvis.db"
DEST="$JARVIS_BACKUPS_DIR"
mkdir -p "$DEST"

if [[ ! -f "$DB" ]]; then
  echo "No database at $DB"
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M)"
cp "$DB" "$DEST/jarvis-${STAMP}.db"
echo "Backed up → $DEST/jarvis-${STAMP}.db"

ls -1t "$DEST"/jarvis-*.db 2>/dev/null | tail -n +15 | while read -r f; do rm -f "$f"; done
