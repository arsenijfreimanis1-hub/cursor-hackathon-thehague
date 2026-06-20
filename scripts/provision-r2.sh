#!/usr/bin/env bash
# Create R2 bucket for off-site backups (uses CLOUDFLARE_* from .env).
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
BUCKET="${CLOUDFLARE_R2_BUCKET:-jarvis-backups}"

[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
: "${CLOUDFLARE_ACCOUNT_ID:?}"
: "${CLOUDFLARE_API_TOKEN:?}"
: "${CLOUDFLARE_R2_ACCESS_KEY_ID:?}"
: "${CLOUDFLARE_R2_SECRET_ACCESS_KEY:?}"
: "${CLOUDFLARE_R2_ENDPOINT:?}"

api() {
  curl -sf -X "$1" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID$2" "${@:3}"
}

existing="$(api GET "/r2/buckets" || echo '{"result":{"buckets":[]}}')"
has="$(python3 - <<'PY' "$existing" "$BUCKET"
import json, sys
data = json.loads(sys.argv[1])
bucket = sys.argv[2]
print("yes" if any(b.get("name") == bucket for b in data.get("result", {}).get("buckets", [])) else "no")
PY
)"
if [[ "$has" != "yes" ]]; then
  echo "Creating R2 bucket: $BUCKET"
  resp="$(curl -sS -X POST \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/r2/buckets" \
    --data "{\"name\":\"$BUCKET\"}")"
  if ! python3 -c "import json,sys; d=json.loads(sys.argv[1]); sys.exit(0 if d.get('success') else 1)" "$resp"; then
    msg="$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print((d.get('errors') or [{}])[0].get('message',''))" "$resp")"
    echo "R2 not ready: $msg"
    echo "Enable R2 in Cloudflare Dashboard, then re-run ./scripts/provision-r2.sh"
    exit 0
  fi
else
  echo "R2 bucket exists: $BUCKET"
fi

python3 - "$BUCKET" "$ENV_FILE" <<'PY'
import re, sys
bucket, path = sys.argv[1:3]
text = open(path).read()
if re.search(r'^CLOUDFLARE_R2_BUCKET=', text, re.M):
    text = re.sub(r'^CLOUDFLARE_R2_BUCKET=.*$', f'CLOUDFLARE_R2_BUCKET={bucket}', text, flags=re.M)
else:
    text += f'\nCLOUDFLARE_R2_BUCKET={bucket}\n'
open(path, 'w').write(text)
PY

if command -v aws >/dev/null 2>&1; then
  AWS_ACCESS_KEY_ID="$CLOUDFLARE_R2_ACCESS_KEY_ID" \
  AWS_SECRET_ACCESS_KEY="$CLOUDFLARE_R2_SECRET_ACCESS_KEY" \
    aws s3 ls "s3://$BUCKET" --endpoint-url "$CLOUDFLARE_R2_ENDPOINT" >/dev/null
  echo "R2 S3 access OK"
else
  echo "Install awscli for S3 uploads: brew install awscli"
fi
