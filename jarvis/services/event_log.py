"""Unified append-only interaction timeline: chat, voice, tasks, terminal, escalations."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

import aiosqlite

from jarvis.database import DB_PATH

_META_MEMORY_SINCE = "memory_since"
_STOP = frozenset(
    "what when where that this with have will boss about your mine just like tell "
    "please could would should the and for are was".split()
)


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS interaction_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'web',
                user_message TEXT,
                assistant_reply TEXT,
                intent TEXT,
                task_id INTEGER,
                task_status TEXT,
                engine TEXT,
                conversation_id TEXT,
                alignment_score REAL,
                alignment_notes TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_events_created ON interaction_events(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_source ON interaction_events(source, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_type ON interaction_events(event_type, created_at DESC);
            CREATE TABLE IF NOT EXISTS jarvis_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        await db.commit()


async def ensure_memory_epoch() -> str:
    """Set memory_since to deployment time on first boot."""
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (
            await db.execute("SELECT value FROM jarvis_meta WHERE key = ?", (_META_MEMORY_SINCE,))
        ).fetchone()
        if row:
            return row[0]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            "INSERT INTO jarvis_meta (key, value) VALUES (?, ?)",
            (_META_MEMORY_SINCE, now),
        )
        await db.commit()
        return now


async def memory_since() -> str:
    return await ensure_memory_epoch()


async def log_event(
    event_type: str,
    *,
    source: str = "web",
    user_message: str | None = None,
    assistant_reply: str | None = None,
    intent: str | None = None,
    task_id: int | None = None,
    task_status: str | None = None,
    engine: str | None = None,
    conversation_id: str | None = None,
    alignment_score: float | None = None,
    alignment_notes: str | None = None,
    metadata: dict | None = None,
) -> dict:
    await ensure_tables()
    event_id = str(uuid.uuid4())
    meta_json = json.dumps(metadata) if metadata else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO interaction_events (
                id, event_type, source, user_message, assistant_reply,
                intent, task_id, task_status, engine, conversation_id,
                alignment_score, alignment_notes, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event_type,
                source,
                (user_message or "")[:2000] or None,
                (assistant_reply or "")[:4000] or None,
                intent,
                task_id,
                task_status,
                engine,
                conversation_id,
                alignment_score,
                (alignment_notes or "")[:1000] or None,
                meta_json,
            ),
        )
        await db.commit()
    from jarvis.services import activity_stream

    await activity_stream.broadcast(
        {
            "kind": event_type,
            "title": _event_title(event_type, engine, intent),
            "detail": (assistant_reply or user_message or "")[:500],
            "status": task_status or "done",
            "engine": engine,
            "metadata": metadata or {},
        }
    )
    return {"id": event_id, "event_type": event_type}


def _event_title(event_type: str, engine: str | None, intent: str | None) -> str:
    if event_type == "integration":
        return engine or "integration"
    if intent:
        return f"{event_type} · {intent}"
    return event_type


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in _STOP}


def evaluate_alignment(
    user_message: str,
    assistant_reply: str,
    *,
    task_status: str | None = None,
    intent: str | None = None,
    engine: str | None = None,
) -> tuple[float, str]:
    """Lightweight post-task alignment check (no LLM)."""
    if not user_message or not assistant_reply:
        return 0.5, "missing message or reply"

    reply_lower = assistant_reply.lower()
    fail_markers = (
        "could not verify",
        "cannot run",
        "cannot do",
        "trouble right now",
        "task failed",
        "sorry boss",
        "unavailable",
        "no reliable facts",
    )
    if any(m in reply_lower for m in fail_markers):
        return 0.2, "reply indicates failure or unverified facts"

    if task_status == "failed":
        return 0.15, "task marked failed"

    if task_status in ("done", "approved") and engine not in ("error", "blocked", "ignored"):
        user_kw = _keywords(user_message)
        reply_kw = _keywords(assistant_reply)
        overlap = len(user_kw & reply_kw) / max(len(user_kw), 1) if user_kw else 0.5
        if intent in ("system", "terminal") and task_status == "done":
            return 0.9, "action completed"
        if overlap >= 0.25 or len(user_message.split()) <= 4:
            return min(0.95, 0.6 + overlap * 0.35), "reply addresses request"
        return 0.55, "completed but weak topical overlap"

    if engine in ("error", "blocked"):
        return 0.1, f"engine={engine}"

    if intent == "ignored":
        return 0.3, "voice noise ignored"

    user_kw = _keywords(user_message)
    reply_kw = _keywords(assistant_reply)
    if user_kw:
        overlap = len(user_kw & reply_kw) / len(user_kw)
        if overlap >= 0.3:
            return 0.8, "good topical overlap"
        return 0.5, "partial overlap"
    return 0.65, "short or generic exchange"


async def log_interaction(
    *,
    source: str,
    user_message: str,
    assistant_reply: str,
    intent: str | None = None,
    task_id: int | None = None,
    task_status: str | None = None,
    engine: str | None = None,
    conversation_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    score, notes = evaluate_alignment(
        user_message,
        assistant_reply,
        task_status=task_status,
        intent=intent,
        engine=engine,
    )
    event = await log_event(
        "chat",
        source=source,
        user_message=user_message,
        assistant_reply=assistant_reply,
        intent=intent,
        task_id=task_id,
        task_status=task_status,
        engine=engine,
        conversation_id=conversation_id,
        alignment_score=score,
        alignment_notes=notes,
        metadata=metadata,
    )
    event["alignment_score"] = score
    event["alignment_notes"] = notes
    try:
        from jarvis.services import vigil_metrics

        vigil_metrics.emit_interaction(
            source=source,
            user_message=user_message,
            assistant_reply=assistant_reply,
            intent=intent,
            engine=engine,
            task_status=task_status,
            alignment_score=score,
            metadata=metadata,
        )
    except Exception:
        pass
    return event


async def log_task_outcome(
    *,
    source: str,
    user_message: str,
    reply: str,
    task_id: int,
    task_status: str,
    engine: str | None = None,
    conversation_id: str | None = None,
) -> dict:
    score, notes = evaluate_alignment(
        user_message,
        reply,
        task_status=task_status,
        engine=engine,
        intent="action",
    )
    event = await log_event(
        "task_outcome",
        source=source,
        user_message=user_message,
        assistant_reply=reply,
        intent="action",
        task_id=task_id,
        task_status=task_status,
        engine=engine,
        conversation_id=conversation_id,
        alignment_score=score,
        alignment_notes=notes,
    )
    event["alignment_score"] = score
    event["alignment_notes"] = notes
    try:
        from jarvis.services import vigil_metrics

        vigil_metrics.emit_task_outcome(
            source=source,
            user_message=user_message,
            reply=reply,
            task_status=task_status,
            engine=engine,
            alignment_score=score,
        )
    except Exception:
        pass
    return event


async def log_integration(
    integration: str,
    *,
    source: str = "system",
    detail: str | None = None,
    task_id: int | None = None,
    metadata: dict | None = None,
) -> dict:
    meta = {"integration": integration, **(metadata or {})}
    result = await log_event(
        "integration",
        source=source,
        user_message=detail,
        metadata=meta,
        task_id=task_id,
    )
    try:
        from jarvis.services import vigil_metrics

        vigil_metrics.emit_integration(integration, detail=detail, metadata=metadata)
    except Exception:
        pass
    return result


async def list_events(
    *,
    limit: int = 50,
    source: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
) -> list[dict]:
    await ensure_tables()
    since = since or await memory_since()
    clauses = ["datetime(created_at) >= datetime(?)"]
    params: list = [since]
    if source:
        clauses.append("source = ?")
        params.append(source)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    params.append(limit)
    where = " AND ".join(clauses)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                f"""
                SELECT id, event_type, source, user_message, assistant_reply,
                       intent, task_id, task_status, engine, conversation_id,
                       alignment_score, alignment_notes, metadata, created_at
                FROM interaction_events
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params,
            )
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        if item.get("metadata"):
            try:
                item["metadata"] = json.loads(item["metadata"])
            except json.JSONDecodeError:
                pass
        out.append(item)
    return out


async def get_timeline_block(*, limit: int = 6) -> str:
    """Compact continuity block for router prompts."""
    events = await list_events(limit=limit)
    if not events:
        return ""
    lines = ["RECENT ACTIVITY (what we did together — use for continuity, don't invent beyond this):"]
    for ev in reversed(events):
        ts = (ev.get("created_at") or "")[:16]
        src = ev.get("source", "?")
        etype = ev.get("event_type", "?")
        if etype == "chat":
            um = (ev.get("user_message") or "")[:80]
            ar = (ev.get("assistant_reply") or "")[:80]
            eng = ev.get("engine") or ""
            lines.append(f"- [{ts} {src}/{eng}] boss: {um} → willy: {ar}")
        elif etype == "task_outcome":
            um = (ev.get("user_message") or "")[:60]
            st = ev.get("task_status") or "?"
            lines.append(f"- [{ts} task#{ev.get('task_id')} {st}] {um}")
        elif etype == "integration":
            meta = ev.get("metadata") or {}
            if isinstance(meta, dict):
                lines.append(f"- [{ts} {meta.get('integration', 'tool')}] {(ev.get('user_message') or '')[:80]}")
    return "\n".join(lines)


async def stats() -> dict:
    await ensure_tables()
    since = await memory_since()
    async with aiosqlite.connect(DB_PATH) as db:
        total = await (
            await db.execute(
                "SELECT COUNT(*) FROM interaction_events WHERE datetime(created_at) >= datetime(?)",
                (since,),
            )
        ).fetchone()
        by_type = await (
            await db.execute(
                """
                SELECT event_type, COUNT(*) AS n FROM interaction_events
                WHERE datetime(created_at) >= datetime(?)
                GROUP BY event_type
                """,
                (since,),
            )
        ).fetchall()
        by_source = await (
            await db.execute(
                """
                SELECT source, COUNT(*) AS n FROM interaction_events
                WHERE datetime(created_at) >= datetime(?)
                GROUP BY source ORDER BY n DESC
                """,
                (since,),
            )
        ).fetchall()
        misaligned = await (
            await db.execute(
                """
                SELECT COUNT(*) FROM interaction_events
                WHERE datetime(created_at) >= datetime(?)
                  AND alignment_score IS NOT NULL AND alignment_score < 0.4
                """,
                (since,),
            )
        ).fetchone()
    return {
        "memory_since": since,
        "total": total[0] if total else 0,
        "by_type": {row[0]: row[1] for row in by_type},
        "by_source": {row[0]: row[1] for row in by_source},
        "misaligned": misaligned[0] if misaligned else 0,
    }
