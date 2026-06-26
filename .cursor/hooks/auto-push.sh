#!/bin/bash
# After each agent turn: stage, commit if dirty, push current branch.
# Requires git_write + network permissions in Cursor.

set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

# Skip if not a git repo
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Skip if nothing changed (except maybe hook noise)
if git diff --quiet && git diff --cached --quiet; then
  exit 0
fi

BRANCH="$(git branch --show-current 2>/dev/null || echo main)"
DEV_ID="${HACKATHON_DEV_ID:-dev-unknown}"
MSG="[${DEV_ID}] auto-sync $(date -u +%Y-%m-%dT%H:%M:%SZ)"

git add -A
# Never commit secrets
git reset HEAD -- .env .env.local mac-mini/.env 2>/dev/null || true

if git diff --cached --quiet; then
  exit 0
fi

git commit -m "$MSG" --no-verify 2>/dev/null || exit 0

git pull --rebase origin "$BRANCH" 2>/dev/null || true
git push -u origin "$BRANCH" 2>/dev/null || true

exit 0
