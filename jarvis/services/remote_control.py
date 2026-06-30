"""Runtime toggle for low-latency remote mouse/keyboard relay."""

from __future__ import annotations

import aiosqlite

from jarvis.database import DB_PATH

_KEY = "remote_control_enabled"
_cache: bool | None = None

_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


async def ensure_table() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SETTINGS_SCHEMA)
        await db.commit()


async def is_enabled() -> bool:
    global _cache
    if _cache is not None:
        return _cache
    await ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute(
            "SELECT value FROM agent_settings WHERE key = ?", (_KEY,)
        )).fetchone()
        _cache = bool(row and row[0] == "true")
        return _cache


async def set_enabled(enabled: bool) -> dict:
    global _cache
    await ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agent_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (_KEY, "true" if enabled else "false"),
        )
        await db.commit()
    _cache = enabled
    return {"remote_control_enabled": enabled}


async def status() -> dict:
    return {"remote_control_enabled": await is_enabled()}


async def require_enabled() -> None:
    if not await is_enabled():
        raise PermissionError("remote control disabled")
