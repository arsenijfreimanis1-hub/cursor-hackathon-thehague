#!/usr/bin/env bash
# Upload latest SQLite backup to Cloudflare R2.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

: "${CLOUDFLARE_R2_BUCKET:?}"
: "${CLOUDFLARE_R2_ENDPOINT:?}"
: "${CLOUDFLARE_R2_ACCESS_KEY_ID:?}"
: "${CLOUDFLARE_R2_SECRET_ACCESS_KEY:?}"

DB="$ROOT/data/jarvis.db"
[[ -f "$DB" ]] || { echo "No jarvis.db"; exit 1; }
command -v aws >/dev/null || { echo "awscli required: brew install awscli"; exit 1; }

key="sqlite/jarvis-$(date +%Y%m%d-%H%M%S).db"
AWS_ACCESS_KEY_ID="$CLOUDFLARE_R2_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$CLOUDFLARE_R2_SECRET_ACCESS_KEY" \
  aws s3 cp "$DB" "s3://$CLOUDFLARE_R2_BUCKET/$key" --endpoint-url "$CLOUDFLARE_R2_ENDPOINT"
echo "Uploaded s3://$CLOUDFLARE_R2_BUCKET/$key"
