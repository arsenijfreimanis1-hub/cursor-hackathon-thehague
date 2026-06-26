#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NODE="${NODE:-node}"
API_PORT="${API_PORT:-4000}"

"$NODE" "$ROOT/scripts/smoke-test/mini-server.mjs" &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1 && break
  sleep 0.2
done

RESP=$(curl -sf "http://localhost:${API_PORT}/health")
echo "$RESP" | grep -q '"status":"ok"'
