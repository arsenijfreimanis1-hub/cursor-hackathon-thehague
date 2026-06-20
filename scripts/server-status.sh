#!/usr/bin/env bash
# William Agent — local server health snapshot
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== William Agent server status ==="
echo "Time: $(date)"
echo ""

check_http() {
  local name="$1" url="$2"
  if curl -sf --max-time 3 "$url" >/dev/null 2>&1; then
    echo "  OK  $name ($url)"
  else
    echo "  FAIL $name ($url)"
  fi
}

echo "-- HTTP services --"
check_http "jarvis-core" "http://127.0.0.1:8787/api/health"
check_http "macos-helper" "http://127.0.0.1:8788/status"
check_http "openclaw" "http://127.0.0.1:18789"
check_http "ollama" "http://127.0.0.1:11434/api/tags"

echo ""
echo "-- launchd --"
for label in com.willy.jarvis-core com.willy.jarvis-helper ai.openclaw.gateway; do
  if launchctl print "gui/$(id -u)/$label" &>/dev/null; then
    echo "  OK  $label"
  else
    echo "  FAIL $label (not loaded)"
  fi
done

echo ""
echo "-- SQLite --"
DB="$ROOT/data/jarvis.db"
if [[ -f "$DB" ]]; then
  echo "  OK  jarvis.db ($(du -h "$DB" | cut -f1))"
else
  echo "  FAIL jarvis.db missing"
fi

echo ""
echo "-- Docker stack --"
if command -v docker &>/dev/null && colima status 2>&1 | grep -q "is running"; then
  docker compose ps 2>/dev/null || echo "  (no compose services)"
  check_http "caddy-proxy" "http://127.0.0.1:8080/api/health"
  if [[ -s "$ROOT/data/public-url.txt" ]]; then
    pub="$(tr -d '[:space:]' < "$ROOT/data/public-url.txt")"
    check_http "public-tunnel" "$pub/api/health"
    echo "  Public URL: $pub"
  fi
else
  echo "  colima/docker not running"
fi

echo ""
echo "Admin panel: http://127.0.0.1:8787/admin"
echo "Chat:        http://127.0.0.1:8787/"
