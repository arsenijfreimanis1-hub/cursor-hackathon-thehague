import aiosqlite

from jarvis.database import DB_PATH


async def list_tasks(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def list_tasks_by_status(status: str, *, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY priority ASC, id ASC LIMIT ?",
            (status, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def create_task(
    title: str,
    body: str = "",
    source: str = "web",
    *,
    status: str = "pending",
    parent_id: int | None = None,
    batch_id: str | None = None,
    priority: int = 50,
    goal_id: int | None = None,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO tasks (title, body, source, status, parent_id, batch_id, priority, goal_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, body, source, status, parent_id, batch_id, priority, goal_id),
        )
        await db.commit()
        row = await (await db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))).fetchone()
        return dict(row)


async def update_task_status(task_id: int, status: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, task_id),
        )
        await db.commit()
        row = await (await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))).fetchone()
    if row:
        from jarvis.services import activity_stream

        task = dict(row)
        await activity_stream.emit(
            "task",
            (task.get("title") or f"Task #{task_id}")[:120],
            detail=f"Status → {status}",
            status=status,
            engine=task.get("source"),
            metadata={"task_id": task_id},
        )
    return dict(row) if row else None


async def list_batch_tasks(batch_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE batch_id = ? ORDER BY priority ASC, id ASC",
            (batch_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
