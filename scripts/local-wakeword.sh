#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.voice-venv"
PYTHON="$VENV/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "OPENWAKEWORD_PYTHON_MISSING" >&2
  echo "Run: $ROOT/scripts/setup-local-voice.sh" >&2
  exit 2
fi

exec "$PYTHON" "$ROOT/scripts/local_voice_openwakeword.py"
