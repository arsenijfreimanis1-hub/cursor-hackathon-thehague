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


async def create_task(title: str, body: str = "", source: str = "web") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO tasks (title, body, source) VALUES (?, ?, ?)",
            (title, body, source),
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
        return dict(row) if row else None
