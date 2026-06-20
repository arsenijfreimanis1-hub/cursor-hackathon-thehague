#!/usr/bin/env bash
# Verify Notion integration can access the parent page; guide user to share if not.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

PAGE_ID="$(python3 -c "from jarvis.config import settings; print(settings.notion_parent_page_id)")"
if [[ -z "$PAGE_ID" ]]; then
  echo "Missing JARVIS_NOTION_PARENT_PAGE_ID in .env — run ./scripts/configure-notion.sh"
  exit 1
fi

open "https://www.notion.so/p/${PAGE_ID//-/}"
open "https://www.notion.so/my-integrations" 2>/dev/null || true

osascript <<'APPLESCRIPT' || true
display dialog "Share the page with your integration:

1. In Notion, open \"William Agent Learning\"
2. Click ⋯ (top right) → Connections
3. Add connection: ntn_willy

Click OK when done." with title "William Agent — Notion" buttons {"OK"} default button "OK"
APPLESCRIPT

for i in $(seq 1 24); do
  if python3 - "$PAGE_ID" <<'PY'
import sys, urllib.request, urllib.error
from jarvis.config import settings

page_id = sys.argv[1]
token = settings.resolved_notion_api_key()
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
r = urllib.request.Request(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
try:
    with urllib.request.urlopen(r, timeout=15):
        sys.exit(0)
except urllib.error.HTTPError as e:
    sys.exit(1 if e.code == 404 else 2)
PY
  then
    echo "Integration can access parent page."
    curl -sf -X POST "http://127.0.0.1:8787/api/events/export-notion?limit=10" | python3 -m json.tool
    exit 0
  fi
  sleep 5
done

echo "Still no access — share \"William Agent Learning\" with ntn_willy in Notion Connections."
exit 1
