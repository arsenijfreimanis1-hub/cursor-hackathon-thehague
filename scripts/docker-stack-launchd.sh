#!/usr/bin/env bash
# Non-blocking wrapper for launchd — colima must NOT use -f (foreground).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec >>"$ROOT/logs/docker-stack.log" 2>>"$ROOT/logs/docker-stack.err.log"
echo "--- $(date) docker-stack launch ---"
LOCKDIR="$ROOT/logs/docker-stack.lockdir"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "another docker-stack run in progress, skipping"
  exit 0
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null || true' EXIT
"$ROOT/scripts/docker-stack.sh" start
