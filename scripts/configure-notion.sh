#!/usr/bin/env bash
# Configure Notion: token + auto-create "William Agent Learning" parent page.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"

cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

if python3 -c "from jarvis.services.notion_sync import configured; exit(0 if configured() else 1)" 2>/dev/null; then
  echo "Notion already configured."
  exit 0
fi

# Parent page already set — only need API key
EXISTING_PAGE="$(grep -E '^JARVIS_NOTION_PARENT_PAGE_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d ' \"' || true)"

KEY=""
for candidate in \
  "${JARVIS_NOTION_API_KEY:-}" \
  "${NOTION_API_KEY:-}" \
  "$(cat "$HOME/.config/notion/api_key" 2>/dev/null || true)"
do
  if [[ -n "$candidate" && "$candidate" != secret_* && "$candidate" != ntn_your* ]]; then
    KEY="$candidate"
    break
  fi
done

if [[ -z "$KEY" && "$(uname -s)" == "Darwin" ]]; then
  open "https://www.notion.so/my-integrations" 2>/dev/null || true
  KEY="$(osascript <<'APPLESCRIPT' 2>/dev/null || true
display dialog "Paste your Notion integration token (secret_… or ntn_…).

Create at notion.so/my-integrations → New integration → copy token." default answer "" with title "William Agent — Notion" buttons {"Skip", "Save"} default button "Save" with hidden answer
if button returned of result is "Save" then
  return text returned of result
end if
APPLESCRIPT
)"
fi

KEY="$(echo "$KEY" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
if [[ -z "$KEY" ]]; then
  echo "Skipped — set JARVIS_NOTION_API_KEY in .env when ready."
  exit 1
fi

export NOTION_TOKEN="$KEY"
if [[ -n "$EXISTING_PAGE" ]]; then
  PAGE_ID="$EXISTING_PAGE"
else
PAGE_ID="$(python3 - <<'PY'
import json, os, sys, urllib.request

token = os.environ["NOTION_TOKEN"]
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"https://api.notion.com/v1{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.load(resp)

try:
    req("GET", "/users/me")
except Exception as exc:
    print(f"ERROR:{exc}", file=sys.stderr)
    sys.exit(1)

title = "William Agent Learning"
search = req("POST", "/search", {"query": title, "page_size": 10})
for item in search.get("results", []):
    if item.get("object") != "page":
        continue
    props = item.get("properties", {})
    for val in props.values():
        if val.get("type") == "title":
            plain = "".join(t.get("plain_text", "") for t in val.get("title", []))
            if plain.strip().lower() == title.lower():
                print(item["id"])
                sys.exit(0)

page = req(
    "POST",
    "/pages",
    {
        "parent": {"type": "workspace", "workspace": True},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]},
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Auto-created by William Agent. Session logs and task outcomes export here.",
                            },
                        }
                    ]
                },
            }
        ],
    },
)
print(page["id"])
PY
)"
fi || {
  echo "Notion API failed — check token and integration capabilities (read/write content)."
  exit 1
}

if [[ "$PAGE_ID" == ERROR:* ]]; then
  echo "$PAGE_ID"
  exit 1
fi

mkdir -p "$HOME/.config/notion"
echo "$KEY" > "$HOME/.config/notion/api_key"
chmod 600 "$HOME/.config/notion/api_key"

export NOTION_TOKEN PAGE_ID ENV_FILE
python3 - <<'PY'
import os, re
from pathlib import Path

key = os.environ["NOTION_TOKEN"]
page = os.environ["PAGE_ID"]
env = Path(os.environ["ENV_FILE"])
lines = env.read_text(encoding="utf-8").splitlines() if env.is_file() else []
out: list[str] = []
seen_key = seen_page = False
for line in lines:
    if re.match(r"^\s*#?\s*JARVIS_NOTION_API_KEY=", line):
        if not seen_key:
            out.append(f"JARVIS_NOTION_API_KEY={key}")
            seen_key = True
        continue
    if re.match(r"^\s*#?\s*JARVIS_NOTION_PARENT_PAGE_ID=", line):
        if not seen_page:
            out.append(f"JARVIS_NOTION_PARENT_PAGE_ID={page}")
            seen_page = True
        continue
    out.append(line)
if not seen_key:
    out.append(f"JARVIS_NOTION_API_KEY={key}")
if not seen_page:
    out.append(f"JARVIS_NOTION_PARENT_PAGE_ID={page}")
env.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY

./scripts/sync-launchd-env.sh
./scripts/restart.sh core

python3 - <<'PY'
import urllib.request, urllib.error, sys
from jarvis.config import settings

page_id = settings.notion_parent_page_id
token = settings.resolved_notion_api_key()
if not page_id or not token:
    sys.exit(0)
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
r = urllib.request.Request(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
try:
    with urllib.request.urlopen(r, timeout=15):
        print("Notion page accessible to integration.")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("IMPORTANT: Share \"William Agent Learning\" with ntn_willy in Notion → ⋯ → Connections")
        print("Then run: ./scripts/fix-notion-share.sh")
PY

echo "Notion configured. Parent page id saved to .env"
