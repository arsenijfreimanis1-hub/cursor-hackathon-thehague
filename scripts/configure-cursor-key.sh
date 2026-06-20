#!/usr/bin/env bash
# Securely prompt for CURSOR_API_KEY and sync into .env + launchd.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"

cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

if python3 -c "from jarvis.config import settings; exit(0 if settings.cursor_configured() else 1)" 2>/dev/null; then
  echo "Cursor API key already configured."
  exit 0
fi

open "https://cursor.com/dashboard/integrations" 2>/dev/null || true

KEY="$(osascript <<'APPLESCRIPT' 2>/dev/null || true
display dialog "Paste your Cursor User API Key (starts with cursor_).

Create one at: cursor.com/dashboard/integrations" default answer "" with title "William Agent — Cursor API Key" buttons {"Skip", "Save"} default button "Save" with hidden answer
if button returned of result is "Save" then
  return text returned of result
end if
APPLESCRIPT
)"

KEY="$(echo "$KEY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
if [[ -z "$KEY" ]]; then
  echo "Skipped — add CURSOR_API_KEY to jarvis-core/.env manually."
  exit 1
fi

export JARVIS_PENDING_CURSOR_KEY="$KEY"
export ENV_FILE
if ! python3 - <<'PY'
import os, sys
from jarvis.config import is_cursor_key_valid
key = os.environ.get("JARVIS_PENDING_CURSOR_KEY", "")
sys.exit(0 if is_cursor_key_valid(key) else 1)
PY
then
  echo "Invalid key — paste the full key from cursor.com/dashboard/integrations (not the placeholder)."
  exit 1
fi

python3 - <<'PY'
import os, re
from pathlib import Path

key = os.environ["JARVIS_PENDING_CURSOR_KEY"]
env = Path(os.environ["ENV_FILE"])
lines = env.read_text(encoding="utf-8").splitlines() if env.is_file() else []
out: list[str] = []
replaced = False
for line in lines:
    if re.match(r"^\s*#?\s*CURSOR_API_KEY=", line):
        if not replaced:
            out.append(f"CURSOR_API_KEY={key}")
            replaced = True
        continue
    out.append(line)
if not replaced:
    out.append(f"CURSOR_API_KEY={key}")
env.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY

unset JARVIS_PENDING_CURSOR_KEY

chmod +x scripts/sync-launchd-env.sh scripts/restart.sh
./scripts/sync-launchd-env.sh
./scripts/restart.sh core

echo "Cursor API key saved and jarvis-core restarted."
