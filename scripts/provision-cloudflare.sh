#!/usr/bin/env bash
# Provision named Cloudflare Tunnel + save token to .env (uses CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME:-jarvis-william-agent}"
HOSTNAME="${JARVIS_PUBLIC_HOSTNAME:-}"
SERVICE_URL="${JARVIS_TUNNEL_SERVICE_URL:-http://caddy:8080}"

[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

: "${CLOUDFLARE_ACCOUNT_ID:?Set CLOUDFLARE_ACCOUNT_ID in .env}"
: "${CLOUDFLARE_API_TOKEN:?Set CLOUDFLARE_API_TOKEN in .env}"

api() {
  local method="$1" path="$2"
  shift 2
  curl -sf -X "$method" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4$path" "$@"
}

python3 - "$ENV_FILE" "$CLOUDFLARE_ACCOUNT_ID" "$CLOUDFLARE_API_TOKEN" <<'PY' || true
import re, sys
path, account, token = sys.argv[1:4]
text = open(path).read() if __import__('pathlib').Path(path).is_file() else ''
for k, v in {
    'CLOUDFLARE_ACCOUNT_ID': account,
    'CLOUDFLARE_API_TOKEN': token,
}.items():
    if re.search(rf'^{k}=', text, re.M):
        text = re.sub(rf'^{k}=.*$', f'{k}={v}', text, flags=re.M)
    else:
        text += f'\n{k}={v}\n'
open(path, 'w').write(text)
PY

echo "Checking Cloudflare API token..."
api GET "/accounts/$CLOUDFLARE_ACCOUNT_ID/tokens/verify" >/dev/null

if [[ -z "$HOSTNAME" ]]; then
  zone_json="$(api GET "/zones?per_page=50")"
  HOSTNAME="$(python3 - <<'PY' "$zone_json"
import json, sys
zones = json.loads(sys.argv[1]).get("result", [])
if not zones:
    print("")
else:
    z = zones[0]
    print(f"jarvis.{z['name']}")
PY
)"
fi

tunnel_id=""
existing="$(api GET "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel")"
tunnel_id="$(python3 - <<'PY' "$existing" "$TUNNEL_NAME"
import json, sys
data = json.loads(sys.argv[1])
name = sys.argv[2]
for t in data.get("result", []):
    if t.get("name") == name:
        print(t.get("id", ""))
        break
PY
)"

if [[ -z "$tunnel_id" ]]; then
  echo "Creating tunnel: $TUNNEL_NAME"
  created="$(api POST "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel" \
    --data "{\"name\":\"$TUNNEL_NAME\",\"config_src\":\"cloudflare\"}")"
  tunnel_id="$(python3 -c "import json,sys; print(json.load(sys.stdin)['result']['id'])" <<<"$created")"
else
  echo "Reusing tunnel: $TUNNEL_NAME ($tunnel_id)"
fi

if [[ -n "$HOSTNAME" ]]; then
  echo "Configuring hostname: $HOSTNAME -> $SERVICE_URL"
  api PUT "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$tunnel_id/configurations" \
    --data "{\"config\":{\"ingress\":[{\"hostname\":\"$HOSTNAME\",\"service\":\"$SERVICE_URL\"},{\"service\":\"http_status:404\"}]}}" >/dev/null
  zone_name="${HOSTNAME#*.}"
  if [[ "$HOSTNAME" == *.* ]]; then
    zone_name="${HOSTNAME#jarvis.}"
    [[ "$zone_name" == "$HOSTNAME" ]] && zone_name="${HOSTNAME#*.}"
  fi
  zone_id="$(python3 - <<'PY' "$zone_json" "$zone_name"
import json, sys
zones = json.loads(sys.argv[1]).get("result", [])
name = sys.argv[2]
for z in zones:
    if z.get("name") == name:
        print(z.get("id", ""))
        break
PY
  )"
  if [[ -n "$zone_id" ]]; then
    api POST "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$tunnel_id/routes" \
      --data "{\"network\":\"$HOSTNAME\",\"tunnel_id\":\"$tunnel_id\"}" >/dev/null 2>&1 || \
    api PUT "/zones/$zone_id/dns_records" \
      --data "{\"type\":\"CNAME\",\"name\":\"${HOSTNAME%%.$zone_name}\",\"content\":\"$tunnel_id.cfargotunnel.com\",\"proxied\":true}" >/dev/null 2>&1 || true
  fi
else
  echo "No Cloudflare zone found — using quick tunnel for public URL."
  api PUT "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$tunnel_id/configurations" \
    --data "{\"config\":{\"ingress\":[{\"service\":\"$SERVICE_URL\"}]}}" >/dev/null
fi

echo "Fetching tunnel token..."
token_json="$(api GET "/accounts/$CLOUDFLARE_ACCOUNT_ID/cfd_tunnel/$tunnel_id/token")"
tunnel_token="$(python3 -c "import json,sys; print(json.load(sys.stdin)['result'])" <<<"$token_json")"

python3 - "$tunnel_token" "$tunnel_id" "$HOSTNAME" "$ENV_FILE" <<'PY'
import re, sys
token, tunnel_id, hostname, path = sys.argv[1:5]
text = open(path).read()
for k, v in {
    'CLOUDFLARE_TUNNEL_TOKEN': token,
    'CLOUDFLARE_TUNNEL_ID': tunnel_id,
    'JARVIS_PUBLIC_ACCESS': '1',
}.items():
    if re.search(rf'^{k}=', text, re.M):
        text = re.sub(rf'^{k}=.*$', f'{k}={v}', text, flags=re.M)
    else:
        text += f'\n{k}={v}\n'
if hostname:
    if re.search(r'^JARVIS_PUBLIC_HOSTNAME=', text, re.M):
        text = re.sub(r'^JARVIS_PUBLIC_HOSTNAME=.*$', f'JARVIS_PUBLIC_HOSTNAME={hostname}', text, flags=re.M)
    else:
        text += f'\nJARVIS_PUBLIC_HOSTNAME={hostname}\n'
open(path, 'w').write(text)
PY

mkdir -p "$ROOT/data"
if [[ -n "$HOSTNAME" ]]; then
  echo "https://$HOSTNAME" > "$ROOT/data/public-url.txt"
else
  rm -f "$ROOT/data/public-url.txt"
fi

echo "Restarting docker stack with named tunnel..."
"$ROOT/scripts/provision-r2.sh" 2>/dev/null || echo "R2 setup skipped (check CLOUDFLARE_R2_* in .env)"
"$ROOT/scripts/docker-stack.sh" restart

if [[ -n "$HOSTNAME" ]]; then
  echo ""
  echo "Public URL: https://$HOSTNAME"
  echo "Health:     https://$HOSTNAME/api/health"
else
  echo ""
  echo "Named tunnel is running (stable reconnect)."
  echo "Add a domain to Cloudflare for a custom hostname, then re-run with:"
  echo "  JARVIS_PUBLIC_HOSTNAME=jarvis.yourdomain.com ./scripts/provision-cloudflare.sh"
fi
