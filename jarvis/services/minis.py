"""Minis screen-share state + frame cache for phone ↔ Mac widget."""

from __future__ import annotations

import asyncio
from pathlib import Path

import aiosqlite

from jarvis.database import DB_PATH
from jarvis.services import macos, remote_control

_SCREEN_KEY = "screen_share_enabled"
_cache: bool | None = None
_frame_lock = asyncio.Lock()
_latest_frame: bytes | None = None
_stream_task: asyncio.Task | None = None

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


async def is_screen_share_enabled() -> bool:
    global _cache
    if _cache is not None:
        return _cache
    await ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute(
            "SELECT value FROM agent_settings WHERE key = ?", (_SCREEN_KEY,)
        )).fetchone()
        _cache = bool(row and row[0] == "true")
        return _cache


async def set_screen_share(enabled: bool) -> dict:
    global _cache
    await ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO agent_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
            (_SCREEN_KEY, "true" if enabled else "false"),
        )
        await db.commit()
    _cache = enabled
    if enabled:
        await macos.screen_watcher_resume()
        await _start_stream()
    else:
        await _stop_stream()
        await macos.screen_watcher_pause()
    return {"screen_share_enabled": enabled}


async def status() -> dict:
    helper = await macos.health()
    screen_helper = await macos.screen_watcher_status()
    return {
        "core_ok": True,
        "remote_control": await remote_control.status(),
        "screen_share_enabled": await is_screen_share_enabled(),
        "macos_helper": helper,
        "screen_watcher": screen_helper.get("watcher") if screen_helper.get("ok") else None,
        "has_frame": _latest_frame is not None,
    }


async def handle_input(event_type: str, x: float, y: float) -> dict:
    if not await remote_control.is_enabled():
        return {"ok": False, "error": "remote control disabled"}
    action_map = {"tap": "click", "move": "mousemove", "down": "mousedown", "up": "mouseup"}
    action = action_map.get(event_type)
    if not action:
        return {"ok": False, "error": f"unknown event type: {event_type}"}
    return await macos.dispatch_remote_action(action, {"x": x, "y": y})


async def get_screen_frame() -> bytes | None:
    if not await is_screen_share_enabled():
        return None
    async with _frame_lock:
        return _latest_frame


async def _capture_frame() -> None:
    global _latest_frame
    result = await macos.screenshot()
    if not result.get("ok"):
        return
    path = result.get("path")
    if not path:
        return
    try:
        data = Path(path).read_bytes()
    except OSError:
        return
    async with _frame_lock:
        _latest_frame = data


async def _stream_loop() -> None:
    while await is_screen_share_enabled():
        await _capture_frame()
        await asyncio.sleep(0.4)


async def _start_stream() -> None:
    global _stream_task
    if _stream_task and not _stream_task.done():
        return
    _stream_task = asyncio.create_task(_stream_loop())


async def _stop_stream() -> None:
    global _stream_task, _latest_frame
    if _stream_task and not _stream_task.done():
        _stream_task.cancel()
        try:
            await _stream_task
        except asyncio.CancelledError:
            pass
    _stream_task = None
    async with _frame_lock:
        _latest_frame = None


def frame_content_type(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    return "application/octet-stream"
