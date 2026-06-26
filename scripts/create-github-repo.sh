#!/bin/bash
# Create GitHub repo and push initial commit.
# Usage: GITHUB_TOKEN=ghp_xxx ./scripts/create-github-repo.sh
# Or: install gh CLI and run: gh auth login && ./scripts/create-github-repo.sh

set -euo pipefail

REPO_NAME="${GITHUB_REPO_NAME:-cursor-hackathon-thehague}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -d .git ]; then
  echo "Git already initialized."
else
  git init -b main
fi

git add -A
git commit -m "$(cat <<'EOF'
Bootstrap Cursor Hackathon The Hague team repo.

Shared MCP config, Mac mini integration hub, teammate Cursor prompts,
README-as-team-bus, and partner perk activation docs.
EOF
)" || echo "Nothing new to commit"

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "Creating repo with gh CLI..."
  gh repo create "$REPO_NAME" --public --source=. --remote=origin --push --description "Cursor Hackathon The Hague 2026 — team repo"
  echo "Done: $(gh repo view --json url -q .url)"
  exit 0
fi

if [ -n "${GITHUB_TOKEN:-}" ]; then
  USER="$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user | jq -r .login)"
  echo "Creating repo for user: $USER"
  curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"description\":\"Cursor Hackathon The Hague 2026\"}" \
    https://api.github.com/user/repos >/dev/null
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://${GITHUB_TOKEN}@github.com/${USER}/${REPO_NAME}.git"
  git push -u origin main
  echo "Done: https://github.com/${USER}/${REPO_NAME}"
  exit 0
fi

echo ""
echo "No gh CLI or GITHUB_TOKEN found."
echo "Manual steps:"
echo "  1. Create repo at https://github.com/new?name=$REPO_NAME"
echo "  2. git remote add origin https://github.com/YOUR_USER/$REPO_NAME.git"
echo "  3. git push -u origin main"
echo ""
echo "Or install gh: https://cli.github.com/ then: gh auth login && ./scripts/create-github-repo.sh"
