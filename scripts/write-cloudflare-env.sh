#!/usr/bin/env bash
# One-time: write Cloudflare credentials from arguments into .env
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"

ACCOUNT_ID="${1:?account id}"
API_TOKEN="${2:?api token}"
R2_KEY="${3:-}"
R2_SECRET="${4:-}"
R2_ENDPOINT="${5:-}"

python3 - "$ENV_FILE" "$ACCOUNT_ID" "$API_TOKEN" "$R2_KEY" "$R2_SECRET" "$R2_ENDPOINT" <<'PY'
import re, sys
path, account, token, r2k, r2s, r2e = sys.argv[1:7]
text = open(path).read()
vals = {
    'CLOUDFLARE_ACCOUNT_ID': account,
    'CLOUDFLARE_API_TOKEN': token,
    'JARVIS_PUBLIC_ACCESS': '1',
}
if r2k: vals['CLOUDFLARE_R2_ACCESS_KEY_ID'] = r2k
if r2s: vals['CLOUDFLARE_R2_SECRET_ACCESS_KEY'] = r2s
if r2e: vals['CLOUDFLARE_R2_ENDPOINT'] = r2e
for k, v in vals.items():
    if re.search(rf'^{k}=', text, re.M):
        text = re.sub(rf'^{k}=.*$', f'{k}={v}', text, flags=re.M)
    else:
        text += f'\n{k}={v}\n'
open(path, 'w').write(text)
print('Cloudflare credentials saved to .env')
PY
