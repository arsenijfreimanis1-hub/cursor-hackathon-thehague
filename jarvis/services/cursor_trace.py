"""Persist Cursor SDK run transcripts — thinking, assistant text, tool use."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import aiosqlite

from jarvis.database import DB_PATH

log = logging.getLogger("jarvis.cursor_trace")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cursor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    agent_id TEXT,
    source TEXT NOT NULL DEFAULT 'cursor_agent',
    prompt_preview TEXT,
    status TEXT,
    result TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cursor_runs_run_id ON cursor_runs(run_id);

CREATE TABLE IF NOT EXISTS cursor_run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cursor_run_db_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    raw TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (cursor_run_db_id) REFERENCES cursor_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_cursor_run_events_run ON cursor_run_events(cursor_run_db_id, seq);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


def message_to_entry(msg) -> dict:
    """Normalize an SDKMessage into a storable dict."""
    msg_type = getattr(msg, "type", "unknown")
    entry: dict = {"type": msg_type, "text": ""}

    if msg_type == "assistant":
        content = getattr(getattr(msg, "message", None), "content", ()) or ()
        parts: list[str] = []
        for block in content:
            btype = getattr(block, "type", "")
            if btype == "text":
                parts.append(getattr(block, "text", "") or "")
            elif btype == "tool_use":
                name = getattr(block, "name", "tool")
                parts.append(f"[tool_use: {name}]")
        entry["text"] = "\n".join(p for p in parts if p)

    elif msg_type == "thinking":
        entry["text"] = getattr(msg, "text", "") or ""

    elif msg_type == "tool_use":
        name = getattr(msg, "name", "") or getattr(msg, "tool_name", "tool")
        entry["text"] = f"tool: {name}"
        input_val = getattr(msg, "input", None)
        if input_val:
            entry["text"] += f" {json.dumps(input_val)[:400]}"

    else:
        entry["text"] = str(msg)[:500]

    try:
        entry["raw"] = json.dumps(msg, default=lambda o: getattr(o, "__dict__", str(o)))[:2000]
    except Exception:
        entry["raw"] = None
    return entry


async def start_run(
    *,
    prompt: str,
    source: str = "cursor_agent",
    run_id: str | None = None,
    agent_id: str | None = None,
) -> int:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO cursor_runs (run_id, agent_id, source, prompt_preview, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, agent_id, source, prompt[:500], _now()),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def append_event(db_run_id: int, seq: int, entry: dict) -> None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO cursor_run_events (cursor_run_db_id, seq, event_type, text, raw, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                db_run_id,
                seq,
                entry.get("type", "unknown"),
                (entry.get("text") or "")[:8000],
                entry.get("raw"),
                _now(),
            ),
        )
        await db.commit()


async def finish_run(
    db_run_id: int,
    *,
    run_id: str | None = None,
    agent_id: str | None = None,
    status: str | None = None,
    result: str | None = None,
) -> None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE cursor_runs
            SET run_id = COALESCE(?, run_id),
                agent_id = COALESCE(?, agent_id),
                status = ?,
                result = ?
            WHERE id = ?
            """,
            (run_id, agent_id, status, (result or "")[:12000], db_run_id),
        )
        await db.commit()


async def get_run(db_run_id: int) -> dict | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM cursor_runs WHERE id = ?", (db_run_id,))).fetchone()
        if not row:
            return None
        events = await (
            await db.execute(
                "SELECT * FROM cursor_run_events WHERE cursor_run_db_id = ? ORDER BY seq",
                (db_run_id,),
            )
        ).fetchall()
    data = dict(row)
    data["events"] = [dict(e) for e in events]
    return data


async def get_run_by_sdk_id(run_id: str) -> dict | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (
            await db.execute("SELECT * FROM cursor_runs WHERE run_id = ? ORDER BY id DESC LIMIT 1", (run_id,))
        ).fetchone()
    if not row:
        return None
    return await get_run(row["id"])


async def list_runs(*, limit: int = 20, source: str | None = None) -> list[dict]:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if source:
            rows = await (
                await db.execute(
                    "SELECT * FROM cursor_runs WHERE source = ? ORDER BY id DESC LIMIT ?",
                    (source, limit),
                )
            ).fetchall()
        else:
            rows = await (
                await db.execute("SELECT * FROM cursor_runs ORDER BY id DESC LIMIT ?", (limit,))
            ).fetchall()
    return [dict(r) for r in rows]


async def format_transcript(db_run_id: int) -> str:
    run = await get_run(db_run_id)
    if not run:
        return ""
    lines = [f"Cursor run #{db_run_id} status={run.get('status')} sdk_run_id={run.get('run_id')}"]
    for ev in run.get("events") or []:
        label = ev.get("event_type", "?").upper()
        text = (ev.get("text") or "").strip()
        if text:
            lines.append(f"[{label}] {text[:600]}")
    if run.get("result"):
        lines.append(f"[RESULT] {(run['result'] or '')[:800]}")
    return "\n".join(lines)
