"""Agent-specific usage logs, outcomes, and lightweight self-improvement."""

from __future__ import annotations

import json

import aiosqlite

from jarvis.database import DB_PATH
from jarvis.services import agent_registry, event_log
from jarvis.services.agent_types import AgentRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    agent_version INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'web',
    conversation_id TEXT,
    task TEXT NOT NULL,
    reply TEXT,
    run_id TEXT,
    model TEXT,
    workspace_dir TEXT,
    allowed_tools TEXT NOT NULL DEFAULT '[]',
    success INTEGER NOT NULL DEFAULT 0,
    outcome TEXT NOT NULL DEFAULT 'failed',
    metadata TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_agent_usage_logs_agent_created
    ON agent_usage_logs(agent_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_outcomes (
    usage_log_id INTEGER PRIMARY KEY,
    score REAL NOT NULL DEFAULT 0,
    alignment_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    lesson_key TEXT NOT NULL,
    lesson TEXT NOT NULL,
    remedy TEXT NOT NULL,
    occurrences INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(agent_id, lesson_key)
);
CREATE INDEX IF NOT EXISTS idx_agent_lessons_agent_status
    ON agent_lessons(agent_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS agent_evolution_meta (
    agent_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY(agent_id, key)
);
"""

_LESSON_RULES = {
    "constraint": (
        "State tool and allowlist limits early, then offer the closest supported next step.",
        "When blocked by the allowlist, say what is allowed and suggest a concrete handoff or narrower task.",
    ),
    "execution_failure": (
        "Validate workspace, tool assumptions, and required context before attempting specialist work.",
        "If execution fails, mention the missing prerequisite plainly instead of acting as if the task completed.",
    ),
    "alignment": (
        "Keep replies tightly scoped to the requested deliverable and specialist role.",
        "Mirror the requested artifact or action in the first sentence before adding supporting detail.",
    ),
    "reliability": (
        "Preserve the concise response pattern that is producing strong recent outcomes.",
        "Reuse the current structure and only expand when the task explicitly asks for depth.",
    ),
}


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


def _classify_outcome(*, ok: bool, reply: str) -> str:
    lowered = reply.lower()
    if ok and "outside the allowlist" in lowered:
        return "constrained"
    if ok and any(token in lowered for token in ("cannot", "blocked", "constraint", "outside the allowlist")):
        return "constrained"
    return "success" if ok else "failed"


def _lesson_keys(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    low_alignment = 0
    for row in rows:
        outcome = row["outcome"]
        if outcome == "constrained":
            counts["constraint"] = counts.get("constraint", 0) + 1
        if not row["success"]:
            counts["execution_failure"] = counts.get("execution_failure", 0) + 1
        if float(row["score"] or 0) < 0.55:
            low_alignment += 1
    if low_alignment >= 2:
        counts["alignment"] = low_alignment
    if not counts and rows and min(float(row["score"] or 0) for row in rows[:4]) >= 0.8:
        counts["reliability"] = len(rows[:4])
    return counts


def _render_learning_notes(lessons: list[dict]) -> str:
    if not lessons:
        return ""
    lines: list[str] = []
    for lesson in lessons[:3]:
        lines.append(f"{lesson['lesson']} Remedy: {lesson['remedy']}")
    return "\n".join(lines)


async def _replace_lessons(agent_id: int, lessons: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE agent_lessons SET status = 'inactive', updated_at = datetime('now') WHERE agent_id = ?",
            (agent_id,),
        )
        for item in lessons:
            await db.execute(
                """
                INSERT INTO agent_lessons (agent_id, lesson_key, lesson, remedy, occurrences, status, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', datetime('now'))
                ON CONFLICT(agent_id, lesson_key) DO UPDATE SET
                    lesson = excluded.lesson,
                    remedy = excluded.remedy,
                    occurrences = excluded.occurrences,
                    status = 'active',
                    updated_at = datetime('now')
                """,
                (
                    agent_id,
                    item["lesson_key"],
                    item["lesson"],
                    item["remedy"],
                    item["occurrences"],
                ),
            )
        await db.commit()


async def _set_meta(agent_id: int, key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO agent_evolution_meta (agent_id, key, value, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(agent_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
            """,
            (agent_id, key, value),
        )
        await db.commit()


async def list_recent_runs(agent_name: str, *, limit: int = 20) -> list[dict]:
    await ensure_tables()
    agent = await agent_registry.get_agent(agent_name, include_inactive=True)
    if not agent:
        return []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT l.id, l.agent_id, l.agent_name, l.agent_version, l.source, l.task, l.reply,
                       l.run_id, l.model, l.workspace_dir, l.allowed_tools, l.success, l.outcome,
                       l.metadata, o.score, o.alignment_notes, l.created_at
                FROM agent_usage_logs l
                LEFT JOIN agent_outcomes o ON o.usage_log_id = l.id
                WHERE l.agent_id = ?
                ORDER BY l.created_at DESC, l.id DESC
                LIMIT ?
                """,
                (agent.id, limit),
            )
        ).fetchall()
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        item["success"] = bool(item["success"])
        try:
            item["allowed_tools"] = json.loads(item["allowed_tools"] or "[]")
        except json.JSONDecodeError:
            item["allowed_tools"] = []
        if item.get("metadata"):
            try:
                item["metadata"] = json.loads(item["metadata"])
            except json.JSONDecodeError:
                pass
        out.append(item)
    return out


async def refresh_agent_learning(agent_name: str) -> dict:
    await ensure_tables()
    agent = await agent_registry.get_agent(agent_name, include_inactive=True)
    if not agent:
        return {"ok": False, "error": f"unknown agent: {agent_name}"}

    rows = await list_recent_runs(agent.name, limit=12)
    if not rows:
        return {"ok": True, "updated": False, "reason": "no runs recorded"}

    total_runs = len(rows)
    success_count = sum(1 for row in rows if row["success"])
    failure_count = total_runs - success_count
    avg_score = round(sum(float(row["score"] or 0) for row in rows) / total_runs, 4)

    lesson_counts = _lesson_keys(rows)
    lessons = []
    for key, occurrences in sorted(lesson_counts.items(), key=lambda item: item[1], reverse=True):
        lesson, remedy = _LESSON_RULES[key]
        lessons.append(
            {
                "lesson_key": key,
                "lesson": lesson,
                "remedy": remedy,
                "occurrences": occurrences,
            }
        )

    await _replace_lessons(agent.id, lessons)
    await _set_meta(agent.id, "recent_runs", str(total_runs))
    await _set_meta(agent.id, "recent_successes", str(success_count))
    await _set_meta(agent.id, "recent_failures", str(failure_count))
    await _set_meta(agent.id, "average_score", f"{avg_score:.4f}")
    await _set_meta(agent.id, "last_outcome", rows[0]["outcome"])
    await _set_meta(agent.id, "last_run_id", rows[0].get("run_id") or "")

    learning_notes = _render_learning_notes(lessons)
    await agent_registry.update_learning_state(
        agent.id,
        performance_score=avg_score,
        learning_notes=learning_notes,
        mark_improved=bool(lessons),
    )
    return {
        "ok": True,
        "updated": True,
        "agent_name": agent.name,
        "recent_runs": total_runs,
        "average_score": avg_score,
        "lessons": len(lessons),
    }


async def record_agent_execution(
    agent: AgentRecord,
    task: str,
    result: dict,
    *,
    voice: bool = False,
    conversation_id: str | None = None,
) -> dict:
    await ensure_tables()
    ok = bool(result.get("ok"))
    reply = (result.get("result") if ok else result.get("error")) or ""
    task_status = "done" if ok else "failed"
    score, alignment_notes = event_log.evaluate_alignment(
        task,
        reply,
        task_status=task_status,
        intent="agent",
        engine="agent",
    )
    outcome = _classify_outcome(ok=ok, reply=reply)
    metadata = {
        "voice": voice,
        "allowed_tools": agent.runtime.allowed_tools,
    }
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO agent_usage_logs (
                agent_id, agent_name, agent_version, source, conversation_id, task, reply,
                run_id, model, workspace_dir, allowed_tools, success, outcome, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent.id,
                agent.name,
                agent.version,
                "voice" if voice else "web",
                conversation_id,
                task[:2000],
                reply[:4000],
                result.get("run_id"),
                agent.runtime.model,
                agent.runtime.workspace_dir,
                json.dumps(agent.runtime.allowed_tools),
                1 if ok else 0,
                outcome,
                json.dumps(metadata),
            ),
        )
        usage_log_id = cursor.lastrowid
        await db.execute(
            """
            INSERT INTO agent_outcomes (usage_log_id, score, alignment_notes)
            VALUES (?, ?, ?)
            """,
            (usage_log_id, round(float(score), 4), alignment_notes[:1000]),
        )
        await db.commit()

    await agent_registry.record_agent_usage(agent.name)
    summary = await refresh_agent_learning(agent.name)
    summary["score"] = round(float(score), 4)
    summary["outcome"] = outcome
    return summary


async def get_agent_lessons_block(agent_name: str, *, limit: int = 3) -> str:
    await ensure_tables()
    agent = await agent_registry.get_agent(agent_name, include_inactive=True)
    if not agent:
        return ""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                """
                SELECT lesson_key, lesson, remedy, occurrences
                FROM agent_lessons
                WHERE agent_id = ? AND status = 'active'
                ORDER BY occurrences DESC, updated_at DESC
                LIMIT ?
                """,
                (agent.id, limit),
            )
        ).fetchall()
    if not rows:
        return ""
    lines = ["AGENT-SPECIFIC LEARNING (apply these if relevant):"]
    for row in rows:
        lines.append(f"- [{row['lesson_key']}] {row['lesson']} Remedy: {row['remedy']}")
    return "\n".join(lines)


async def get_agent_summary(agent_name: str) -> dict:
    await ensure_tables()
    agent = await agent_registry.get_agent(agent_name, include_inactive=True)
    if not agent:
        return {"ok": False, "error": f"unknown agent: {agent_name}"}
    runs = await list_recent_runs(agent.name, limit=10)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (
            await db.execute(
                "SELECT key, value FROM agent_evolution_meta WHERE agent_id = ? ORDER BY key ASC",
                (agent.id,),
            )
        ).fetchall()
    return {
        "ok": True,
        "agent_name": agent.name,
        "performance_score": agent.performance_score,
        "learning_notes": agent.learning_notes,
        "last_improved_at": agent.last_improved_at,
        "recent_runs": runs,
        "meta": {row["key"]: row["value"] for row in rows},
    }
