#!/bin/bash
# Run this ONCE on your machine (not in sandbox) to publish the repo.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_NAME="${GITHUB_REPO_NAME:-cursor-hackathon-thehague}"
GITHUB_USER="${GITHUB_USER:-arsenijfreimanis1-hub}"

if [ ! -d .git ]; then
  GIT_TEMPLATE_DIR=/dev/null git init -b main
  git add -A
  git commit -m "Bootstrap Cursor Hackathon The Hague team repo" || true
fi

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh repo create "$REPO_NAME" --public --source=. --remote=origin --push \
    --description "Cursor Hackathon The Hague 2026 — team repo"
  gh repo view --json url -q .url
  exit 0
fi

git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo "Create empty repo at: https://github.com/new?name=${REPO_NAME}"
echo "Then run: git push -u origin main"
read -r -p "Press Enter after creating the repo on GitHub..."
git push -u origin main
echo "Done: https://github.com/${GITHUB_USER}/${REPO_NAME}"
