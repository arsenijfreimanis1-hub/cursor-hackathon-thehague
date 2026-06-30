#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VOICE_VENV="$ROOT/.voice-venv"
PYTHON="/opt/homebrew/bin/python3.12"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3 || true)"
if [[ -z "$PYTHON" ]]; then
  echo "python3 is required" >&2
  exit 1
fi

MODEL_DIR="$ROOT/models/whisper"
MODEL_PATH="$MODEL_DIR/ggml-base.en.bin"
OWW_VERSION="v0.5.1"
DEFAULT_WAKE="$ROOT/scripts/local-wakeword.sh"
DEFAULT_WHISPER="$ROOT/scripts/local-whisper-transcribe.sh"
ENV_FILE="$ROOT/.env"
[[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"

echo "=== William local voice setup ==="

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required for whisper.cpp and portaudio." >&2
  exit 1
fi

brew install whisper-cpp portaudio

if [[ ! -d "$VOICE_VENV" ]]; then
  "$PYTHON" -m venv "$VOICE_VENV"
fi
source "$VOICE_VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install openwakeword onnxruntime sounddevice numpy

OWW_SITE_DIR="$("$VOICE_VENV/bin/python" - <<'PY'
import openwakeword
import os
print(os.path.dirname(openwakeword.__file__))
PY
)"
OWW_MODEL_DIR="$OWW_SITE_DIR/resources/models"
mkdir -p "$OWW_MODEL_DIR"

download_oww_model() {
  local filename="$1"
  local target="$OWW_MODEL_DIR/$filename"
  if [[ ! -f "$target" ]]; then
    curl -L \
      "https://github.com/dscripka/openWakeWord/releases/download/${OWW_VERSION}/${filename}" \
      -o "$target"
  fi
}

download_oww_model "embedding_model.onnx"
download_oww_model "melspectrogram.onnx"
download_oww_model "hey_jarvis_v0.1.onnx"

chmod +x "$DEFAULT_WAKE" "$DEFAULT_WHISPER"

mkdir -p "$MODEL_DIR"
if [[ ! -f "$MODEL_PATH" ]]; then
  curl -L \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" \
    -o "$MODEL_PATH"
fi

python - <<PY
from pathlib import Path
env_path = Path("$ENV_FILE")
updates = {
    "WILLIAM_VOICE_BACKEND": "local_openwakeword_whisper",
    "WILLIAM_OPENWAKEWORD_COMMAND": "$DEFAULT_WAKE",
    "WILLIAM_OPENWAKEWORD_MODEL": "$OWW_MODEL_DIR/hey_jarvis_v0.1.onnx",
    "WILLIAM_OPENWAKEWORD_THRESHOLD": "0.62",
    "WILLIAM_WHISPER_COMMAND": "$DEFAULT_WHISPER",
    "WILLIAM_WHISPER_MODEL": "$MODEL_PATH",
}
lines = []
seen = set()
if env_path.exists():
    lines = env_path.read_text(encoding="utf-8").splitlines()
new_lines = []
for raw in lines:
    key = raw.split("=", 1)[0].strip() if "=" in raw else ""
    if key in updates:
        new_lines.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        new_lines.append(raw)
for key, value in updates.items():
    if key not in seen:
        new_lines.append(f"{key}={value}")
env_path.write_text("\\n".join(new_lines).rstrip() + "\\n", encoding="utf-8")
PY

echo ""
echo "Local voice stack configured:"
echo "  backend: local_openwakeword_whisper"
echo "  wake command: $DEFAULT_WAKE"
echo "  wake model: $OWW_MODEL_DIR/hey_jarvis_v0.1.onnx"
echo "  whisper command: $DEFAULT_WHISPER"
echo "  whisper model: $MODEL_PATH"
echo ""
echo "Next steps:"
echo "  1. ./scripts/install-helper.sh"
echo "  2. ./scripts/grant-voice-permissions.sh"
echo "  3. launchctl kickstart -k gui/\$(id -u)/com.willy.jarvis-helper"
