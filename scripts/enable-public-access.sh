#!/usr/bin/env bash
# Turn on public HTTPS with zero manual tokens (Cloudflare quick tunnel).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
URL_FILE="$ROOT/data/public-url.txt"
mkdir -p "$ROOT/data"

[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"
if ! grep -q '^JARVIS_PUBLIC_ACCESS=' "$ENV_FILE" 2>/dev/null; then
  echo "JARVIS_PUBLIC_ACCESS=1" >> "$ENV_FILE"
else
  python3 - "$ENV_FILE" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path).read()
text = re.sub(r'^JARVIS_PUBLIC_ACCESS=.*$', 'JARVIS_PUBLIC_ACCESS=1', text, flags=re.M)
open(path, 'w').write(text)
PY
fi

"$ROOT/scripts/docker-stack.sh" start

echo "Waiting for public URL..."
for _ in $(seq 1 90); do
  url="$(docker logs jarvis-tunnel-quick 2>&1 | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1 || true)"
  if [[ -z "$url" ]]; then
    url="$(docker logs jarvis-tunnel 2>&1 | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | head -1 || true)"
  fi
  if [[ -n "$url" ]]; then
    printf '%s\n' "$url" > "$URL_FILE"
    if curl -sf --max-time 15 "$url/api/health" >/dev/null 2>&1; then
      echo ""
      echo "Public URL: $url"
      echo "Health:     $url/api/health"
      echo "Chat:       $url/"
      exit 0
    fi
  fi
  sleep 1
done

echo "Tunnel starting — check: docker logs jarvis-tunnel-quick"
docker logs jarvis-tunnel-quick 2>&1 | tail -20
exit 1
