"""Always-on screen activity store, summarization, and progressive-disclosure context."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from jarvis.config import settings
from jarvis.database import DB_PATH

log = logging.getLogger("jarvis.screen_observer")

OBSERVATION_ICONS = {
    "session-goal": "🎯",
    "gotcha": "🔴",
    "problem-solution": "🟡",
    "how-it-works": "🔵",
    "what-changed": "🟢",
    "decision": "🟤",
    "trade-off": "⚖️",
    "other": "⚪",
}

_AMBIGUOUS = re.compile(
    r"\b(this|that|it|where i left off|what was i doing|continue where|why is this)\b",
    re.I,
)
_FRICTION = re.compile(
    r"\b(error|failed|exception|traceback|stuck|timeout|denied|403|404|500)\b",
    re.I,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS screen_captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    app TEXT,
    bundle_id TEXT,
    window_title TEXT,
    ocr_text TEXT,
    phash TEXT,
    screenshot_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_screen_captures_ts ON screen_captures(ts DESC);

CREATE TABLE IF NOT EXISTS screen_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    summary TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    observation_type TEXT NOT NULL DEFAULT 'other',
    category TEXT,
    productivity_state TEXT,
    notion_page_id TEXT,
    relayed_to_learning INTEGER NOT NULL DEFAULT 0,
    usefulness_score REAL
);
CREATE INDEX IF NOT EXISTS idx_screen_summaries_end ON screen_summaries(window_end DESC);

CREATE TABLE IF NOT EXISTS screen_context_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    summary_ids TEXT NOT NULL DEFAULT '[]',
    was_useful INTEGER NOT NULL DEFAULT 0,
    rated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS screen_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat()


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def _meta_get(key: str) -> str | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT value FROM screen_meta WHERE key = ?", (key,))).fetchone()
        return row[0] if row else None


async def _meta_set(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO screen_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_meta(key: str) -> str | None:
    return await _meta_get(key)


async def set_meta(key: str, value: str) -> None:
    await _meta_set(key, value)


async def ingest_events(events: list[dict]) -> dict:
    if not events:
        return {"ok": True, "ingested": 0}
    await ensure_tables()
    ingested = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for ev in events:
            await db.execute(
                """
                INSERT INTO screen_captures (ts, app, bundle_id, window_title, ocr_text, phash, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev.get("ts") or _iso(),
                    ev.get("app"),
                    ev.get("bundle_id"),
                    ev.get("window_title"),
                    (ev.get("ocr_text") or "")[:4000],
                    ev.get("phash"),
                    ev.get("screenshot_path"),
                ),
            )
            ingested += 1
        await db.commit()
    await _prune_screenshots()
    return {"ok": True, "ingested": ingested}


async def _prune_screenshots() -> None:
    cutoff = _iso(_now() - timedelta(minutes=settings.screen_screenshot_retention_minutes))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                "SELECT id, screenshot_path FROM screen_captures WHERE ts < ? AND screenshot_path IS NOT NULL",
                (cutoff,),
            )
        ).fetchall()
        for row in rows:
            path = row["screenshot_path"]
            if path:
                try:
                    Path(path).unlink(missing_ok=True)
                except OSError:
                    pass
            await db.execute(
                "UPDATE screen_captures SET screenshot_path = NULL WHERE id = ?",
                (row["id"],),
            )
        await db.commit()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _keyword_score(query: str, *fields: str) -> float:
    q = {w for w in re.findall(r"[a-z0-9]{3,}", query.lower())}
    if not q:
        return 0.0
    blob = " ".join(f for f in fields if f).lower()
    hits = sum(1 for w in q if w in blob)
    return hits / len(q)


async def get_activity_index(*, minutes: int = 30, limit: int = 12) -> str:
    await ensure_tables()
    cutoff = _iso(_now() - timedelta(minutes=minutes))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT id, window_end, title, observation_type, summary
                FROM screen_summaries
                WHERE window_end >= ?
                ORDER BY window_end DESC
                LIMIT ?
                """,
                (cutoff, limit),
            )
        ).fetchall()
    if not rows:
        return ""
    lines = [f"### Screen activity · last {minutes} min"]
    lines.append("| ID | Time | Type | Title | ~Tokens |")
    lines.append("|----|------|------|-------|---------|")
    for row in rows:
        ts = (row["window_end"] or "")[11:16] or "?"
        icon = OBSERVATION_ICONS.get(row["observation_type"] or "other", "⚪")
        title = (row["title"] or row["summary"] or "")[:60]
        tokens = _estimate_tokens(row["summary"] or "")
        lines.append(f"| #{row['id']} | {ts} | {icon} | {title} | ~{tokens} |")
    lines.append("")
    lines.append("Use GET /api/screen/context?detail_ids= for full details on relevant IDs.")
    return "\n".join(lines)


async def get_activity_timeline(*, anchor_id: int, depth: int = 3) -> str:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        anchor = await (
            await db.execute("SELECT window_end FROM screen_summaries WHERE id = ?", (anchor_id,))
        ).fetchone()
        if not anchor:
            return ""
        end_ts = anchor["window_end"]
        before = await (
            await db.execute(
                """
                SELECT id, window_end, title, observation_type, summary
                FROM screen_summaries WHERE window_end <= ? ORDER BY window_end DESC LIMIT ?
                """,
                (end_ts, depth + 1),
            )
        ).fetchall()
        after = await (
            await db.execute(
                """
                SELECT id, window_end, title, observation_type, summary
                FROM screen_summaries WHERE window_end > ? ORDER BY window_end ASC LIMIT ?
                """,
                (end_ts, depth),
            )
        ).fetchall()
    items = list(reversed(before)) + list(after)
    seen: set[int] = set()
    lines = [f"### Screen timeline around #{anchor_id}"]
    for row in items:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        icon = OBSERVATION_ICONS.get(row["observation_type"] or "other", "⚪")
        lines.append(f"- #{row['id']} {icon} {(row['title'] or '')[:80]}: {(row['summary'] or '')[:200]}")
    return "\n".join(lines)


async def get_capture_details(ids: list[int]) -> str:
    if not ids:
        return ""
    await ensure_tables()
    placeholders = ",".join("?" * len(ids))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        summaries = await (
            await db.execute(
                f"SELECT * FROM screen_summaries WHERE id IN ({placeholders}) ORDER BY window_end",
                ids,
            )
        ).fetchall()
    if not summaries:
        return ""
    parts = ["### Screen observation details"]
    for row in summaries:
        icon = OBSERVATION_ICONS.get(row["observation_type"] or "other", "⚪")
        parts.append(f"\n#{row['id']} {icon} {row['title']}")
        parts.append(f"Window: {row['window_start']} → {row['window_end']}")
        parts.append(f"Category: {row['category'] or 'n/a'} · State: {row['productivity_state'] or 'n/a'}")
        parts.append(row["summary"] or "")
    return "\n".join(parts)


async def get_recent_context(
    *,
    minutes: int = 30,
    query: str | None = None,
    detail_ids: list[int] | None = None,
) -> str:
    if detail_ids:
        details = await get_capture_details(detail_ids)
        index = await get_activity_index(minutes=minutes, limit=8)
        return "\n\n".join(p for p in (index, details) if p)

    index = await get_activity_index(minutes=minutes, limit=10)
    if not index:
        return ""

    if query and _AMBIGUOUS.search(query):
        best_id = await _best_summary_id(query, minutes=minutes)
        if best_id:
            timeline = await get_activity_timeline(anchor_id=best_id, depth=2)
            return "\n\n".join(p for p in (index, timeline) if p)

    if query:
        score = await _best_match_score(query, minutes=minutes)
        if score >= settings.screen_semantic_anchor_threshold:
            best_id = await _best_summary_id(query, minutes=minutes)
            if best_id:
                details = await get_capture_details([best_id])
                return "\n\n".join(p for p in (index, details) if p)

    return index


async def _best_summary_id(query: str, *, minutes: int) -> int | None:
    cutoff = _iso(_now() - timedelta(minutes=minutes))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT id, title, summary, category, productivity_state
                FROM screen_summaries WHERE window_end >= ? ORDER BY window_end DESC LIMIT 20
                """,
                (cutoff,),
            )
        ).fetchall()
    best_id: int | None = None
    best_score = 0.0
    for row in rows:
        score = _keyword_score(
            query,
            row["title"] or "",
            row["summary"] or "",
            row["category"] or "",
        )
        if score > best_score:
            best_score = score
            best_id = row["id"]
    return best_id if best_score >= 0.25 else None


async def _best_match_score(query: str, *, minutes: int) -> float:
    cutoff = _iso(_now() - timedelta(minutes=minutes))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                "SELECT title, summary, category FROM screen_summaries WHERE window_end >= ? LIMIT 20",
                (cutoff,),
            )
        ).fetchall()
    if not rows:
        return 0.0
    return max(_keyword_score(query, r["title"] or "", r["summary"] or "", r["category"] or "") for r in rows)


async def build_window_summary() -> dict | None:
    await ensure_tables()
    last_end = await _meta_get("last_summary_end")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if last_end:
            captures = await (
                await db.execute(
                    "SELECT * FROM screen_captures WHERE ts > ? ORDER BY ts ASC LIMIT 60",
                    (last_end,),
                )
            ).fetchall()
        else:
            window_start = _iso(_now() - timedelta(seconds=settings.screen_summary_window_seconds))
            captures = await (
                await db.execute(
                    "SELECT * FROM screen_captures WHERE ts >= ? ORDER BY ts ASC LIMIT 60",
                    (window_start,),
                )
            ).fetchall()
    if len(captures) < 1:
        return None

    apps = sorted({c["app"] for c in captures if c["app"]})
    ocr_chunks = []
    for c in captures[-8:]:
        text = (c["ocr_text"] or "").strip()
        if text:
            ocr_chunks.append(f"[{c['app']}] {text[:300]}")
    ocr_block = "\n".join(ocr_chunks)[:2000] or "(no readable text)"

    prompt = (
        f"Apps: {', '.join(apps)}\n"
        f"Window titles: {', '.join(sorted({c['window_title'] for c in captures if c['window_title']}))}\n"
        f"OCR excerpts:\n{ocr_block}\n\n"
        "Summarize what the user was doing in 2-3 sentences.\n"
        "Reply ONLY with JSON:\n"
        '{"title":"short title max 10 words","summary":"2-3 sentences",'
        '"observation_type":"gotcha|problem-solution|how-it-works|what-changed|decision|trade-off|session-goal|other",'
        '"category":"work|research|play|learning|communication|creative|admin|other",'
        '"productivity_state":"productive|focused|chilling|procrastinating|distracted|in-meeting|idle"}'
    )

    parsed: dict = {}
    try:
        from jarvis.services import ollama

        raw = await ollama.chat(prompt, system="You summarize Mac screen activity. Output valid JSON only.")
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
    except Exception as exc:
        log.warning("screen summary LLM failed: %s", exc)
        parsed = {
            "title": f"{apps[0] if apps else 'Screen'} activity",
            "summary": ocr_block[:400],
            "observation_type": "other",
            "category": "work",
            "productivity_state": "focused",
        }

    if _FRICTION.search(ocr_block) and parsed.get("observation_type") == "other":
        parsed["observation_type"] = "gotcha"

    window_start = captures[0]["ts"]
    window_end = captures[-1]["ts"]
    title = (parsed.get("title") or "Screen activity")[:100]
    summary = (parsed.get("summary") or title)[:1200]
    obs_type = parsed.get("observation_type") or "other"
    if obs_type not in OBSERVATION_ICONS:
        obs_type = "other"

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO screen_summaries
            (window_start, window_end, summary, title, observation_type, category, productivity_state)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                window_start,
                window_end,
                summary,
                title,
                obs_type,
                parsed.get("category"),
                parsed.get("productivity_state"),
            ),
        )
        await db.commit()
        summary_id = cursor.lastrowid

    await _meta_set("last_summary_end", window_end)
    return {
        "id": summary_id,
        "title": title,
        "summary": summary,
        "observation_type": obs_type,
        "category": parsed.get("category"),
        "productivity_state": parsed.get("productivity_state"),
        "window_start": window_start,
        "window_end": window_end,
        "apps": apps,
    }


async def detect_improvement_signals(summary: dict) -> list[dict]:
    signals: list[dict] = []
    obs = summary.get("observation_type", "other")
    text = f"{summary.get('title', '')} {summary.get('summary', '')}"
    if obs in ("gotcha", "problem-solution", "trade-off") or _FRICTION.search(text):
        signals.append(
            {
                "kind": "screen_friction",
                "observation_type": obs,
                "title": summary.get("title"),
                "summary": summary.get("summary"),
                "summary_id": summary.get("id"),
            }
        )
    return signals


async def rate_context_usefulness(*, session_id: str | None, summary_ids: list[int], was_useful: bool) -> None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO screen_context_ratings (session_id, summary_ids, was_useful, rated_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, json.dumps(summary_ids), 1 if was_useful else 0, _iso()),
        )
        if summary_ids and was_useful:
            placeholders = ",".join("?" * len(summary_ids))
            await db.execute(
                f"UPDATE screen_summaries SET usefulness_score = COALESCE(usefulness_score, 0) + 0.1 WHERE id IN ({placeholders})",
                summary_ids,
            )
        await db.commit()


async def status() -> dict:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        cap = await (await db.execute("SELECT COUNT(*) FROM screen_captures")).fetchone()
        summ = await (await db.execute("SELECT COUNT(*) FROM screen_summaries")).fetchone()
        last = await (
            await db.execute("SELECT id, title, window_end FROM screen_summaries ORDER BY id DESC LIMIT 1")
        ).fetchone()
    return {
        "enabled": settings.screen_watch_enabled,
        "captures": cap[0] if cap else 0,
        "summaries": summ[0] if summ else 0,
        "last_summary": dict(last) if last else None,
    }


async def observer_tick() -> dict:
    if not settings.screen_watch_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled"}

    if settings.screenpipe_bridge_enabled:
        try:
            from jarvis.services import screenpipe_bridge

            await screenpipe_bridge.pull_recent()
        except Exception as exc:
            log.debug("screenpipe bridge: %s", exc)

    summary = await build_window_summary()
    if not summary:
        return {"ok": True, "summarized": False}

    result: dict = {"ok": True, "summarized": True, "summary_id": summary["id"]}

    from jarvis.services import learning, notion_sync

    signals = await detect_improvement_signals(summary)
    for signal in signals:
        await learning.record_screen_friction(
            title=signal.get("title") or "Screen friction",
            detail=signal.get("summary") or "",
            observation_type=signal.get("observation_type") or "gotcha",
        )

    if notion_sync.configured():
        notion_result = await notion_sync.sync_screen_summary(summary)
        result["notion"] = notion_result
        if notion_result.get("page_id"):
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE screen_summaries SET notion_page_id = ? WHERE id = ?",
                    (notion_result["page_id"], summary["id"]),
                )
                await db.commit()

    return result
