#!/usr/bin/env bash
# Optional: upgrade to a stable named Cloudflare tunnel (custom domain).
# Base minimum public access needs no token — run ./scripts/enable-public-access.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"

if grep -q '^CLOUDFLARE_TUNNEL_TOKEN=.\+' "$ENV_FILE" 2>/dev/null; then
  echo "Cloudflare tunnel token already configured."
  exit 0
fi

open "https://one.dash.cloudflare.com/?to=/:account/networks/tunnels" 2>/dev/null || true
open "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/" 2>/dev/null || true

TOKEN="$(osascript <<'APPLESCRIPT' 2>/dev/null || true
display dialog "Paste your Cloudflare Tunnel token.

In Cloudflare Zero Trust:
1. Networks → Tunnels → Create tunnel → Docker
2. Copy the token (starts with eyJ…)
3. Add a Public Hostname:
   Service URL = http://host.docker.internal:8080

Paste token below:" default answer "" with title "William Agent — Public Tunnel" buttons {"Skip", "Save"} default button "Save" with hidden answer
if button returned of result is "Save" then
  return text returned of result
end if
APPLESCRIPT
)"

TOKEN="$(echo "$TOKEN" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
if [[ -z "$TOKEN" ]]; then
  echo "Skipped — add CLOUDFLARE_TUNNEL_TOKEN to .env when ready."
  exit 1
fi

if ! grep -q '^CLOUDFLARE_TUNNEL_TOKEN=' "$ENV_FILE" 2>/dev/null; then
  echo "CLOUDFLARE_TUNNEL_TOKEN=$TOKEN" >> "$ENV_FILE"
else
  python3 - "$TOKEN" "$ENV_FILE" <<'PY'
import re, sys
token, path = sys.argv[1], sys.argv[2]
text = open(path).read()
text = re.sub(r'^CLOUDFLARE_TUNNEL_TOKEN=.*$', f'CLOUDFLARE_TUNNEL_TOKEN={token}', text, flags=re.M)
open(path, 'w').write(text)
PY
fi

echo "Starting public stack..."
"$ROOT/scripts/docker-stack.sh" restart
echo ""
echo "Public access ready once Cloudflare hostname is configured."
echo "Tunnel backend URL: http://host.docker.internal:8080"
echo "Local proxy:        http://$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1):8080"
