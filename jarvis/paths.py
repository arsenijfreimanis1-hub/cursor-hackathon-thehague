"""Canonical storage paths for William Agent on macOS."""

from __future__ import annotations

import os
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent


def venv_python() -> Path:
    """Prefer project venv; fall back to the running interpreter."""
    candidate = ROOT / ".venv" / "bin" / "python"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)

STATE_ROOT = Path(
    os.environ.get("JARVIS_STATE_ROOT", str(Path.home() / "Library" / "Application Support" / "Jarvis"))
)
LOGS_DIR = Path(os.environ.get("JARVIS_LOGS_DIR", str(Path.home() / "Library" / "Logs" / "Jarvis")))
AGENTS_DIR = STATE_ROOT / "agents"
CACHE_DIR = STATE_ROOT / "cache"
MODELS_DIR = STATE_ROOT / "models"
BACKUPS_DIR = STATE_ROOT / "backups"


def resolve_data_dir() -> Path:
    """Prefer explicit env, then migrated Library path, then legacy repo data/."""
    explicit = os.environ.get("JARVIS_DATA_DIR", "").strip()
    if explicit:
        return Path(explicit)
    library = STATE_ROOT / "data"
    legacy = ROOT / "data"
    if library.is_dir() and any(library.iterdir()):
        return library
    if legacy.is_dir() and any(legacy.iterdir()):
        return legacy
    return library


def ensure_state_dirs(data_dir: Path | None = None) -> dict[str, Path]:
    """Create state directories used by William for self-improvement and runtime."""
    data = data_dir or resolve_data_dir()
    dirs = {
        "state_root": STATE_ROOT,
        "data_dir": data,
        "logs_dir": LOGS_DIR,
        "agents_dir": AGENTS_DIR,
        "cache_dir": CACHE_DIR,
        "models_dir": MODELS_DIR,
        "backups_dir": BACKUPS_DIR,
        "builds_dir": data / "builds",
        "minis_updates_dir": data / "minis-updates",
        "william_hub_dir": data / "william-hub",
        "whisper_dir": MODELS_DIR / "whisper",
        "skills_cache_dir": CACHE_DIR / "skills",
        "cursor_traces_dir": CACHE_DIR / "cursor-traces",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs
