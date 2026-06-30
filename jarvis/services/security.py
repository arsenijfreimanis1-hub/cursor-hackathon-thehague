import aiosqlite

from jarvis.database import DB_PATH

_KEY = "full_access"
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


async def is_full_access() -> bool:
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


async def set_full_access(enabled: bool) -> dict:
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

    result: dict = {"full_access": enabled}
    if enabled:
        result["permissions"] = await _unlock_system_permissions()
    return result


async def status() -> dict:
    return {"full_access": await is_full_access()}


async def _unlock_system_permissions() -> dict:
    """Bootstrap missing permissions without TCC popup spam (no CGRequestScreenCaptureAccess)."""
    from jarvis.services import permissions

    return await permissions.bootstrap()
