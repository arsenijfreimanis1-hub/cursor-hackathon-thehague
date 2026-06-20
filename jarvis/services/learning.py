"""Self-learning: record struggles, update reports, inject lessons into prompts."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import aiosqlite

from jarvis.config import settings
from jarvis.database import DB_PATH
from jarvis.services import ollama

REPORT_PATH = settings.data_dir / "learning-report.md"
LESSON_LIMIT = 8
EVENTS_PER_AREA = 5

_STRUGGLE_REPLY = re.compile(
    r"\b(could not verify|cannot run|cannot do|trouble right now|no reliable facts|"
    r"task failed|not reachable|unavailable)\b",
    re.I,
)

_DEFAULT_REMEDIES: dict[str, str] = {
    "fact/could_not_verify": (
        "Always search or use structured tools first. If facts are empty, say you could not verify — never guess."
    ),
    "fact/low_confidence": (
        "Use Open-Meteo for weather and system clock for time before generic web search."
    ),
    "reason/could_not_verify": (
        "For hard reasoning, escalate to Cursor when web confidence is low instead of answering from the small local model."
    ),
    "terminal/terminal_failed": (
        "Check full-access mode and command syntax. Prefer maintenance phrases William already knows."
    ),
    "system/system_failed": (
        "Confirm the app or URL exists. Retry with a simpler open/launch command."
    ),
    "unknown/error": (
        "Log the failure, keep the reply short, and avoid repeating the same approach without new context."
    ),
    "code/escalation_unavailable": (
        "Tell the boss Cursor is not configured instead of attempting codegen with the local model."
    ),
    "action/task_failed": (
        "Break background work into smaller steps and verify tools before queueing."
    ),
    "screen/screen_friction": (
        "When boss hits repeated on-screen errors, check screen context before retrying the same fix."
    ),
}


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS struggle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                intent TEXT,
                engine TEXT,
                failure_kind TEXT NOT NULL,
                user_message TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS learning_lessons (
                area TEXT PRIMARY KEY,
                lesson TEXT NOT NULL,
                remedy TEXT NOT NULL,
                occurrences INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS learning_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        await db.commit()


def _area(intent: str | None, failure_kind: str) -> str:
    return f"{intent or 'unknown'}/{failure_kind}"


def _default_remedy(area: str) -> str:
    return _DEFAULT_REMEDIES.get(area, _DEFAULT_REMEDIES["unknown/error"])


async def _meta_get(key: str) -> str | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT value FROM learning_meta WHERE key = ?", (key,))).fetchone()
        return row[0] if row else None


async def _meta_set(key: str, value: str) -> None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO learning_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def record_struggle(
    *,
    user_message: str,
    failure_kind: str,
    intent: str | None = None,
    engine: str | None = None,
    detail: str | None = None,
) -> None:
    await ensure_tables()
    area = _area(intent, failure_kind)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO struggle_events (area, intent, engine, failure_kind, user_message, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (area, intent, engine, failure_kind, user_message[:500], (detail or "")[:1000]),
        )
        await db.commit()
    await _maybe_refresh_report()


def _detect_failure_kind(routed: dict, *, error: str | None = None) -> str | None:
    if error:
        return "error"
    engine = routed.get("engine", "")
    if engine in ("error", "blocked"):
        return engine
    if routed.get("escalation") == "unavailable":
        return "escalation_unavailable"
    web = routed.get("web")
    if web in ("no_results", "none"):
        return "could_not_verify"
    if web in ("low",):
        return "low_confidence"
    reply = routed.get("reply", "")
    if _STRUGGLE_REPLY.search(reply):
        if "could not verify" in reply.lower() or "no reliable facts" in reply.lower():
            return "could_not_verify"
        if engine == "terminal":
            return "terminal_failed"
        if engine == "system":
            return "system_failed"
        if engine == "error":
            return "error"
    return None


async def record_screen_friction(
    *,
    title: str,
    detail: str,
    observation_type: str = "gotcha",
) -> None:
    await record_struggle(
        user_message=title[:500],
        failure_kind="screen_friction",
        intent="screen",
        engine="screen_observer",
        detail=f"[{observation_type}] {detail[:800]}",
    )


async def observe_turn(text: str, routed: dict, *, error: str | None = None) -> None:
    failure_kind = _detect_failure_kind(routed, error=error)
    if not failure_kind:
        return
    detail = error or routed.get("reply")
    await record_struggle(
        user_message=text,
        failure_kind=failure_kind,
        intent=routed.get("intent"),
        engine=routed.get("engine"),
        detail=detail,
    )


async def observe_task_failure(
    *,
    user_message: str,
    error: str,
    intent: str | None = None,
    engine: str | None = None,
) -> None:
    await record_struggle(
        user_message=user_message,
        failure_kind="task_failed",
        intent=intent or "action",
        engine=engine or "orchestrator",
        detail=error,
    )


async def _events_since_report() -> int:
    last = await _meta_get("last_report_at")
    async with aiosqlite.connect(DB_PATH) as db:
        if last:
            row = await (
                await db.execute(
                    "SELECT COUNT(*) FROM struggle_events WHERE created_at > ?",
                    (last,),
                )
            ).fetchone()
        else:
            row = await (await db.execute("SELECT COUNT(*) FROM struggle_events")).fetchone()
        return row[0] if row else 0


async def _maybe_refresh_report() -> None:
    since = await _events_since_report()
    if since < 3:
        return
    await update_report()


async def _grouped_events(*, days: int = 14) -> list[dict]:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT area, intent, failure_kind, user_message, detail, created_at
                FROM struggle_events
                WHERE datetime(created_at) >= datetime('now', ?)
                ORDER BY created_at DESC
                """,
                (f"-{days} days",),
            )
        ).fetchall()

    grouped: dict[str, dict] = {}
    for row in rows:
        area = row["area"]
        bucket = grouped.setdefault(
            area,
            {
                "area": area,
                "intent": row["intent"],
                "failure_kind": row["failure_kind"],
                "count": 0,
                "examples": [],
            },
        )
        bucket["count"] += 1
        if len(bucket["examples"]) < EVENTS_PER_AREA:
            bucket["examples"].append(
                {
                    "message": row["user_message"],
                    "detail": row["detail"],
                    "at": row["created_at"],
                }
            )
    return sorted(grouped.values(), key=lambda g: g["count"], reverse=True)


async def _synthesize_lesson(group: dict) -> dict:
    examples = group["examples"]
    sample = "\n".join(
        f"- User: {e['message'][:120]}"
        + (f" | Detail: {e['detail'][:80]}" if e.get("detail") else "")
        for e in examples[:3]
    )
    prompt = (
        f"Area: {group['area']} ({group['count']} recent failures)\n"
        f"Examples:\n{sample}\n\n"
        "Write ONE lesson sentence and ONE remedy sentence for William Agent to avoid repeating this mistake. "
        "Plain text only. Format exactly:\nLesson: ...\nRemedy: ..."
    )
    try:
        raw = await ollama.chat(prompt, system="You distill agent failures into brief operational lessons.")
        lesson_m = re.search(r"Lesson:\s*(.+)", raw, re.I)
        remedy_m = re.search(r"Remedy:\s*(.+)", raw, re.I)
        lesson = (lesson_m.group(1).strip() if lesson_m else raw.split("\n")[0].strip())[:300]
        remedy = (
            remedy_m.group(1).strip() if remedy_m else _default_remedy(group["area"])
        )[:400]
    except Exception:
        lesson = f"Repeated failures in {group['area']} ({group['count']} times)."
        remedy = _default_remedy(group["area"])
    return {"area": group["area"], "lesson": lesson, "remedy": remedy, "occurrences": group["count"]}


async def _save_lessons(lessons: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for item in lessons:
            await db.execute(
                """
                INSERT INTO learning_lessons (area, lesson, remedy, occurrences, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(area) DO UPDATE SET
                    lesson = excluded.lesson,
                    remedy = excluded.remedy,
                    occurrences = excluded.occurrences,
                    updated_at = datetime('now')
                """,
                (item["area"], item["lesson"], item["remedy"], item["occurrences"]),
            )
        await db.commit()


def _render_report(lessons: list[dict], groups: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        "# William Learning Report",
        "",
        f"Last updated: {now}",
        "",
        "William updates this report after repeated failures so he does not repeat the same mistakes.",
        "",
        "## Active lessons",
        "",
    ]
    if not lessons:
        lines.append("_No struggle areas recorded yet. William will populate this as he learns._")
    else:
        for item in lessons:
            lines.extend(
                [
                    f"### {item['area']} ({item['occurrences']} recent)",
                    f"- **Lesson:** {item['lesson']}",
                    f"- **Remedy:** {item['remedy']}",
                    "",
                ]
            )

    lines.extend(["## Recent struggle log", ""])
    if not groups:
        lines.append("_No recent events._")
    else:
        for group in groups[:12]:
            lines.append(f"### {group['area']} — {group['count']} events")
            for ex in group["examples"][:3]:
                lines.append(f"- `{ex['at']}` — {ex['message'][:100]}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


async def update_report(*, force: bool = False) -> dict:
    await ensure_tables()
    groups = await _grouped_events()
    if not groups and not force:
        return {"ok": True, "updated": False, "reason": "no struggles recorded"}

    lessons: list[dict] = []
    for group in groups[:LESSON_LIMIT]:
        lessons.append(await _synthesize_lesson(group))

    await _save_lessons(lessons)
    report = _render_report(lessons, groups)
    REPORT_PATH.write_text(report, encoding="utf-8")
    await _meta_set("last_report_at", datetime.now().isoformat(timespec="seconds"))

    return {
        "ok": True,
        "updated": True,
        "path": str(REPORT_PATH),
        "areas": len(lessons),
        "events": sum(g["count"] for g in groups),
    }


async def get_lessons_block() -> str:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT area, lesson, remedy FROM learning_lessons
                ORDER BY occurrences DESC, updated_at DESC
                LIMIT ?
                """,
                (LESSON_LIMIT,),
            )
        ).fetchall()
    if not rows:
        return ""
    lines = ["LEARNED FROM PAST MISTAKES (follow these):"]
    for row in rows:
        lines.append(f"- [{row['area']}] {row['lesson']} → {row['remedy']}")
    return "\n".join(lines)


async def get_report() -> dict:
    await ensure_tables()
    text = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
    async with aiosqlite.connect(DB_PATH) as db:
        events = await (await db.execute("SELECT COUNT(*) FROM struggle_events")).fetchone()
        lessons = await (await db.execute("SELECT COUNT(*) FROM learning_lessons")).fetchone()
    return {
        "path": str(REPORT_PATH),
        "report": text,
        "event_count": events[0] if events else 0,
        "lesson_count": lessons[0] if lessons else 0,
        "last_updated": await _meta_get("last_report_at"),
    }


async def periodic_refresh() -> None:
    result = await update_report()
    if result.get("updated"):
        from jarvis.services import tasks

        await tasks.create_task(
            title="Learning report updated",
            body=f"{result.get('areas', 0)} struggle areas reviewed",
            source="learning",
        )
