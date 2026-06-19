import aiosqlite

from jarvis.database import DB_PATH


async def list_approvals(status: str | None = None, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                "SELECT * FROM approvals WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM approvals ORDER BY id DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_approval(approval_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM approvals WHERE id = ?", (approval_id,)
        )).fetchone()
        return dict(row) if row else None


async def request_approval(action: str, detail: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO approvals (action, detail) VALUES (?, ?)",
            (action, detail),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM approvals WHERE id = ?", (cursor.lastrowid,)
        )).fetchone()
        return dict(row)


async def resolve_approval(approval_id: int, approved: bool) -> dict | None:
    existing = await get_approval(approval_id)
    if not existing:
        return None

    status = "approved" if approved else "denied"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE approvals SET status = ?, resolved_at = datetime('now') WHERE id = ?",
            (status, approval_id),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM approvals WHERE id = ?", (approval_id,)
        )).fetchone()
        result = dict(row) if row else None

    if result and approved:
        result["side_effect"] = await _apply_side_effect(existing)
    return result


async def _apply_side_effect(approval: dict) -> dict | None:
    action = approval.get("action")
    if action == "self_modify_merge":
        from jarvis.services import self_modify

        merge = await self_modify.merge_sandbox()
        return {"merge": merge}
    return None
