#!/usr/bin/env bash
# Manage William Agent Docker stack (Postgres, Redis, Caddy, backups).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COLIMA="${COLIMA:-/opt/homebrew/bin/colima}"
DOCKER="${DOCKER:-/opt/homebrew/bin/docker}"
BREW="${BREW:-/opt/homebrew/bin/brew}"

ensure_colima() {
  if ! command -v colima >/dev/null 2>&1 && [[ -x "$COLIMA" ]]; then
    export PATH="/opt/homebrew/bin:$PATH"
  fi
  if ! command -v colima >/dev/null 2>&1; then
    echo "Colima not installed — run: brew install colima docker docker-compose"
    exit 1
  fi
  if ! colima status 2>&1 | grep -q "is running"; then
    echo "Starting Colima..."
    colima start --cpu 2 --memory 4 2>&1 | tail -3
  fi
}

cmd="${1:-status}"
case "$cmd" in
  start)
    ensure_colima
    mkdir -p backups data deploy
    PROFILES="--profile backup --profile postgres --profile redis --profile proxy"
    if grep -q '^CLOUDFLARE_TUNNEL_TOKEN=.\+' "$ROOT/.env" 2>/dev/null; then
      PROFILES="$PROFILES --profile public-named"
      if ! grep -q '^JARVIS_PUBLIC_HOSTNAME=.\+' "$ROOT/.env" 2>/dev/null; then
        PROFILES="$PROFILES --profile public-quick"
      fi
    elif grep -q '^JARVIS_PUBLIC_ACCESS=1' "$ROOT/.env" 2>/dev/null; then
      PROFILES="$PROFILES --profile public-quick"
    fi
    docker compose $PROFILES up -d
    echo ""
    echo "Stack running:"
    docker compose ps
    echo ""
    echo "  jarvis-core:  http://127.0.0.1:8787"
    echo "  HTTP proxy:   http://127.0.0.1:8080"
    if [[ -s "$ROOT/data/public-url.txt" ]]; then
      echo "  Public URL:   $(tr -d '[:space:]' < "$ROOT/data/public-url.txt")"
    elif grep -q '^CLOUDFLARE_TUNNEL_TOKEN=.\+' "$ROOT/.env" 2>/dev/null; then
      if grep -q '^JARVIS_PUBLIC_HOSTNAME=.\+' "$ROOT/.env" 2>/dev/null; then
        echo "  Public tunnel: active (named — https://$(grep '^JARVIS_PUBLIC_HOSTNAME=' "$ROOT/.env" | cut -d= -f2))"
      elif [[ -s "$ROOT/data/public-url.txt" ]]; then
        echo "  Public URL:   $(tr -d '[:space:]' < "$ROOT/data/public-url.txt") (quick tunnel)"
        echo "  Named tunnel: connected (add a domain for a stable hostname)"
      else
        echo "  Public tunnel: starting (named + quick)"
      fi
    elif grep -q '^JARVIS_PUBLIC_ACCESS=1' "$ROOT/.env" 2>/dev/null; then
      echo "  Public tunnel: starting (quick tunnel, no token)"
    else
      echo "  Public tunnel: run ./scripts/enable-public-access.sh"
    fi
    echo "  Postgres:     127.0.0.1:5432 (postgres / postgres / rekentafel)"
    echo "  Redis:        127.0.0.1:6379"
    ;;
  stop)
    docker compose --profile backup --profile postgres --profile redis --profile proxy --profile public-quick --profile public-named down 2>/dev/null || true
    echo "Docker stack stopped (launchd services still run on 8787/8788)."
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if colima status 2>&1 | grep -q "is running"; then
      echo "Colima: running"
      docker compose ps 2>/dev/null || echo "No compose services"
    else
      echo "Colima: stopped"
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
