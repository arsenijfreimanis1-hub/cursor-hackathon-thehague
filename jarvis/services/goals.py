"""Goal storage and plan creation (pending approval)."""

from __future__ import annotations

import uuid

import aiosqlite

from jarvis.database import DB_PATH
from jarvis.services import task_priority, task_splitter, tasks

GOAL_STATUS_AWAITING = "awaiting_approval"
GOAL_STATUS_RUNNING = "running"
GOAL_STATUS_COMPLETE = "complete"
GOAL_STATUS_FAILED = "failed"
GOAL_STATUS_PAUSED = "paused"
GOAL_STATUS_BLOCKED = "blocked"


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_approval',
                batch_id TEXT,
                source TEXT NOT NULL DEFAULT 'web',
                iteration_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                error TEXT
            );
            """
        )
        try:
            await db.execute("ALTER TABLE tasks ADD COLUMN goal_id INTEGER")
        except Exception:
            pass
        await db.commit()


async def get_goal(goal_id: int) -> dict | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))).fetchone()
        return dict(row) if row else None


async def list_goal_tasks(goal_id: int) -> list[dict]:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE goal_id = ? ORDER BY priority ASC, id ASC",
            (goal_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]


async def update_goal_status(
    goal_id: int,
    status: str,
    *,
    error: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    iteration_count: int | None = None,
) -> dict | None:
    await ensure_tables()
    fields = ["status = ?", "updated_at = datetime('now')"]
    values: list[object] = [status]
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if started_at is not None:
        fields.append("started_at = ?")
        values.append(started_at)
    if completed_at is not None:
        fields.append("completed_at = ?")
        values.append(completed_at)
    if iteration_count is not None:
        fields.append("iteration_count = ?")
        values.append(iteration_count)
    values.append(goal_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            f"UPDATE goals SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
        row = await (await db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))).fetchone()
        return dict(row) if row else None


async def increment_iteration(goal_id: int) -> int:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            UPDATE goals
            SET iteration_count = iteration_count + 1,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (goal_id,),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT iteration_count FROM goals WHERE id = ?", (goal_id,)
        )).fetchone()
        return int(row["iteration_count"]) if row else 0


def build_task_tree(goal_tasks: list[dict]) -> dict:
    parent = next((t for t in goal_tasks if not t.get("parent_id")), None)
    children = [t for t in goal_tasks if t.get("parent_id")]
    return {
        "parent": parent,
        "children": children,
        "total": len(goal_tasks),
        "done": sum(1 for t in goal_tasks if t.get("status") == "done"),
        "failed": sum(1 for t in goal_tasks if t.get("status") == "failed"),
        "pending": sum(1 for t in goal_tasks if t.get("status") in ("pending", "queued", "running")),
    }


async def get_goal_detail(goal_id: int) -> dict | None:
    goal = await get_goal(goal_id)
    if not goal:
        return None
    goal_tasks = await list_goal_tasks(goal_id)
    return {
        **goal,
        "tasks": goal_tasks,
        "tree": build_task_tree(goal_tasks),
    }


async def create_goal_from_prompt(
    prompt: str,
    *,
    source: str = "web",
) -> dict:
    """Split prompt into subtasks; store goal awaiting approval (no execution yet)."""
    await ensure_tables()
    subtasks = await task_splitter.split_prompt(prompt)
    ordered = task_priority.sort_by_speed(subtasks)
    batch_id = uuid.uuid4().hex[:10]

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO goals (prompt, status, batch_id, source)
            VALUES (?, ?, ?, ?)
            """,
            (prompt, GOAL_STATUS_AWAITING, batch_id, source),
        )
        goal_id = cursor.lastrowid
        await db.commit()

    parent = await tasks.create_task(
        title=f"Goal: {prompt[:90]}",
        body=prompt,
        source=source,
        status="pending",
        batch_id=batch_id,
        priority=0,
        goal_id=goal_id,
    )
    child_ids: list[int] = []
    for part in ordered:
        prio, _ = task_priority.estimate_priority(part)
        child = await tasks.create_task(
            title=part[:120],
            body=part,
            source=source,
            status="pending",
            parent_id=parent["id"],
            batch_id=batch_id,
            priority=prio,
            goal_id=goal_id,
        )
        child_ids.append(child["id"])

    detail = await get_goal_detail(goal_id)
    assert detail is not None
    detail["subtasks"] = ordered
    detail["parent_task_id"] = parent["id"]
    detail["child_task_ids"] = child_ids
    return detail
