#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUDIO_FILE="${WILLIAM_AUDIO_FILE:-}"
MODEL_PATH="${WILLIAM_WHISPER_MODEL:-${WHISPER_MODEL_PATH:-}}"

if [[ -z "$AUDIO_FILE" || ! -f "$AUDIO_FILE" ]]; then
  echo "Missing WILLIAM_AUDIO_FILE" >&2
  exit 2
fi

if [[ -z "$MODEL_PATH" || ! -f "$MODEL_PATH" ]]; then
  echo "Missing whisper model. Run: $ROOT/scripts/setup-local-voice.sh" >&2
  exit 2
fi

BIN=""
for candidate in \
  "${WHISPER_CPP_BIN:-}" \
  "/opt/homebrew/bin/whisper-cli" \
  "/usr/local/bin/whisper-cli" \
  "$(command -v whisper-cli 2>/dev/null || true)"
do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    BIN="$candidate"
    break
  fi
done

if [[ -z "$BIN" ]]; then
  echo "whisper-cli not found. Run: brew install whisper-cpp" >&2
  exit 2
fi

exec "$BIN" -m "$MODEL_PATH" -f "$AUDIO_FILE" -l en --no-prints
