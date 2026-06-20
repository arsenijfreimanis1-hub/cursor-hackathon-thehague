import re

import aiosqlite

from jarvis.database import DB_PATH
from jarvis.services import macos

ACTION_RE = re.compile(r"ACTION:\s*(.+)", re.I)
NETATMO_ID_RE = re.compile(r"Netatmo (?:recognized person |ID:\s*)(\S+)", re.I)


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


def parse_action(detail: str) -> dict:
    match = ACTION_RE.search(detail or "")
    if not match:
        return {"ok": False, "error": "no ACTION line in approval detail"}
    action = match.group(1).strip().lower()
    if "click" in action:
        nums = re.findall(r"\d+", action)
        if len(nums) >= 2:
            return {"kind": "click", "x": float(nums[0]), "y": float(nums[1])}
        return {"kind": "click", "hint": action}
    if "type" in action or "enter" in action or "write" in action:
        quoted = re.search(r'"([^"]+)"', detail)
        text = quoted.group(1) if quoted else action
        return {"kind": "type", "text": text}
    return {"kind": "unknown", "hint": action}


async def _apply_side_effect(approval: dict) -> dict | None:
    action = approval.get("action")
    detail = approval.get("detail") or ""

    if action == "self_modify_merge":
        from jarvis.services import self_modify

        merge = await self_modify.merge_sandbox()
        return {"merge": merge}

    if action == "desktop_action":
        parsed = parse_action(detail)
        if parsed.get("kind") == "click" and "x" in parsed:
            return await macos.click(parsed["x"], parsed["y"])
        if parsed.get("kind") == "type" and parsed.get("text"):
            return await macos.type_text(parsed["text"])
        return {"ok": False, "parsed": parsed, "error": "could not execute desktop action automatically"}

    if action == "sensitive_action":
        from jarvis.services import router

        routed = await router.route(detail, voice=False)
        await macos.notify(
            "William Agent",
            routed.get("reply", "Sensitive action completed.")[:120],
            speak=False,
        )
        return {"ok": True, "executed": routed}

    if action == "store_person":
        match = NETATMO_ID_RE.search(detail)
        netatmo_id = match.group(1).rstrip(".") if match else None
        await macos.notify(
            "William Agent",
            "Person approved. Open the panel to name them.",
            speak=False,
        )
        return {"ok": True, "action": "store_person", "netatmo_id": netatmo_id}

    return None


async def execute_desktop_action(detail: str) -> dict:
    parsed = parse_action(detail)
    if parsed.get("kind") == "click" and "x" in parsed:
        return await macos.click(parsed["x"], parsed["y"])
    if parsed.get("kind") == "type" and parsed.get("text"):
        return await macos.type_text(parsed["text"])
    return {"ok": False, "parsed": parsed, "error": "could not execute desktop action"}
