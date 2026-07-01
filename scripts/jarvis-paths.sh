#!/usr/bin/env bash
# Shared path resolution for William Agent shell scripts.
set -euo pipefail

JARVIS_ROOT="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")/.." && pwd)"
JARVIS_STATE_ROOT="${JARVIS_STATE_ROOT:-$HOME/Library/Application Support/Jarvis}"
JARVIS_LOGS_DIR="${JARVIS_LOGS_DIR:-$HOME/Library/Logs/Jarvis}"
JARVIS_DATA_DIR="${JARVIS_DATA_DIR:-$JARVIS_STATE_ROOT/data}"
JARVIS_BACKUPS_DIR="${JARVIS_BACKUPS_DIR:-$JARVIS_STATE_ROOT/backups}"
JARVIS_MODELS_DIR="${JARVIS_MODELS_DIR:-$JARVIS_STATE_ROOT/models}"

# Legacy fallbacks when migration has not run yet.
if [[ ! -d "$JARVIS_DATA_DIR" || -z "$(ls -A "$JARVIS_DATA_DIR" 2>/dev/null || true)" ]]; then
  if [[ -d "$JARVIS_ROOT/data" && -n "$(ls -A "$JARVIS_ROOT/data" 2>/dev/null || true)" ]]; then
    JARVIS_DATA_DIR="$JARVIS_ROOT/data"
  fi
fi
if [[ ! -d "$JARVIS_BACKUPS_DIR" || -z "$(ls -A "$JARVIS_BACKUPS_DIR" 2>/dev/null || true)" ]]; then
  if [[ -d "$JARVIS_ROOT/backups" ]]; then
    JARVIS_BACKUPS_DIR="$JARVIS_ROOT/backups"
  fi
fi
if [[ ! -d "$JARVIS_MODELS_DIR/whisper" ]]; then
  if [[ -d "$JARVIS_ROOT/models/whisper" ]]; then
    JARVIS_MODELS_DIR="$JARVIS_ROOT/models"
  fi
fi
if [[ ! -d "$JARVIS_LOGS_DIR" || -z "$(ls -A "$JARVIS_LOGS_DIR" 2>/dev/null || true)" ]]; then
  if [[ -d "$JARVIS_ROOT/logs" ]]; then
    JARVIS_LOGS_DIR="$JARVIS_ROOT/logs"
  fi
fi

export JARVIS_ROOT JARVIS_STATE_ROOT JARVIS_LOGS_DIR JARVIS_DATA_DIR JARVIS_BACKUPS_DIR JARVIS_MODELS_DIR
