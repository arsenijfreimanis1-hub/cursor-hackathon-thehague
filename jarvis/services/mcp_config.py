"""Load and merge MCP server configs from Cursor, NullClaw, and jarvis settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from jarvis.config import ROOT, settings

log = logging.getLogger("jarvis.mcp_config")

_CURSOR_MCP = ROOT / ".cursor" / "mcp.json"
_NULLCLAW_CONFIG = Path.home() / ".nullclaw" / "config.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("failed to read %s: %s", path, exc)
        return {}


def _nullclaw_to_cursor_format(servers: dict[str, Any]) -> dict[str, Any]:
    """Convert NullClaw mcp_servers block to Cursor mcpServers format."""
    out: dict[str, Any] = {}
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        entry: dict[str, Any] = {}
        transport = cfg.get("transport", "stdio")
        if transport == "http":
            if cfg.get("url"):
                entry["url"] = cfg["url"]
            if cfg.get("headers"):
                entry["headers"] = cfg["headers"]
        else:
            if cfg.get("command"):
                entry["command"] = cfg["command"]
            if cfg.get("args"):
                entry["args"] = cfg["args"]
            if cfg.get("env"):
                entry["env"] = cfg["env"]
        if entry:
            out[name] = entry
    return out


def load_mcp_servers() -> dict[str, Any]:
    """Merge MCP servers from .cursor/mcp.json and ~/.nullclaw/config.json."""
    if not settings.mcp_enabled:
        return {}

    merged: dict[str, Any] = {}

    cursor_cfg = _read_json(_CURSOR_MCP)
    cursor_servers = cursor_cfg.get("mcpServers") or cursor_cfg.get("mcp_servers") or {}
    if isinstance(cursor_servers, dict):
        merged.update(cursor_servers)

    nullclaw_cfg = _read_json(_NULLCLAW_CONFIG)
    nullclaw_servers = nullclaw_cfg.get("mcp_servers") or {}
    if isinstance(nullclaw_servers, dict):
        for name, cfg in _nullclaw_to_cursor_format(nullclaw_servers).items():
            merged.setdefault(name, cfg)

    # Optional extra path from settings
    extra_path = settings.mcp_config_path
    if extra_path:
        extra = _read_json(Path(extra_path).expanduser())
        extra_servers = extra.get("mcpServers") or extra.get("mcp_servers") or {}
        if isinstance(extra_servers, dict):
            merged.update(extra_servers)

    return merged


def mcp_server_count() -> int:
    return len(load_mcp_servers())
