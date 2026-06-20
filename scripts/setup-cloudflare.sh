#!/usr/bin/env bash
# Full Cloudflare setup: credentials → tunnel → R2 → public access.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ $# -ge 2 ]]; then
  "$ROOT/scripts/write-cloudflare-env.sh" "$@"
fi
"$ROOT/scripts/provision-cloudflare.sh"
"$ROOT/scripts/enable-public-access.sh"
