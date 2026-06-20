"""Persistence and lookup for William's reusable specialist agents."""

from __future__ import annotations

import json

import aiosqlite

from jarvis.database import DB_PATH
from jarvis.services.agent_types import AgentRecord, AgentSpec, agent_name_key

_SCHEMA = """
CREATE TABLE IF NOT EXISTS specialist_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL UNIQUE,
    purpose TEXT NOT NULL,
    instructions TEXT NOT NULL,
    trigger_phrases TEXT NOT NULL DEFAULT '[]',
    runtime_config TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    parent_agent_id INTEGER,
    performance_score REAL NOT NULL DEFAULT 0,
    learning_notes TEXT NOT NULL DEFAULT '',
    last_used_at TEXT,
    last_improved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_specialist_agents_status
    ON specialist_agents(status, updated_at DESC);
"""


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


def _row_to_record(row: aiosqlite.Row) -> AgentRecord:
    return AgentRecord.model_validate(
        {
            "id": row["id"],
            "name": row["name"],
            "name_key": row["name_key"],
            "purpose": row["purpose"],
            "instructions": row["instructions"],
            "trigger_phrases": json.loads(row["trigger_phrases"] or "[]"),
            "runtime": json.loads(row["runtime_config"] or "{}"),
            "status": row["status"],
            "version": row["version"],
            "parent_agent_id": row["parent_agent_id"],
            "performance_score": row["performance_score"] or 0.0,
            "learning_notes": row["learning_notes"] or "",
            "last_used_at": row["last_used_at"],
            "last_improved_at": row["last_improved_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )


async def register_agent(spec: AgentSpec) -> AgentRecord:
    await ensure_tables()
    payload = spec.model_dump()
    name_key = agent_name_key(payload["name"])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        existing = await (
            await db.execute(
                "SELECT id, version FROM specialist_agents WHERE name_key = ?",
                (name_key,),
            )
        ).fetchone()
        if existing:
            version = int(existing["version"] or 1) + 1
            await db.execute(
                """
                UPDATE specialist_agents
                SET name = ?, purpose = ?, instructions = ?, trigger_phrases = ?,
                    runtime_config = ?, status = ?, version = ?, parent_agent_id = ?,
                    learning_notes = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    payload["name"],
                    payload["purpose"],
                    payload["instructions"],
                    json.dumps(payload["trigger_phrases"]),
                    json.dumps(payload["runtime"]),
                    payload["status"],
                    version,
                    payload["parent_agent_id"],
                    payload["learning_notes"],
                    existing["id"],
                ),
            )
            row_id = existing["id"]
        else:
            cursor = await db.execute(
                """
                INSERT INTO specialist_agents (
                    name, name_key, purpose, instructions, trigger_phrases, runtime_config,
                    status, version, parent_agent_id, learning_notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    payload["name"],
                    name_key,
                    payload["purpose"],
                    payload["instructions"],
                    json.dumps(payload["trigger_phrases"]),
                    json.dumps(payload["runtime"]),
                    payload["status"],
                    payload["parent_agent_id"],
                    payload["learning_notes"],
                ),
            )
            row_id = cursor.lastrowid
        await db.commit()
        row = await (
            await db.execute("SELECT * FROM specialist_agents WHERE id = ?", (row_id,))
        ).fetchone()
    return _row_to_record(row)


async def get_agent_by_id(agent_id: int, *, include_inactive: bool = False) -> AgentRecord | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM specialist_agents WHERE id = ?"
        params: tuple[object, ...] = (agent_id,)
        if not include_inactive:
            query += " AND status = 'active'"
        row = await (await db.execute(query, params)).fetchone()
    return _row_to_record(row) if row else None


async def get_agent(name: str, *, include_inactive: bool = False) -> AgentRecord | None:
    await ensure_tables()
    key = agent_name_key(name)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM specialist_agents WHERE name_key = ?"
        params: tuple[object, ...] = (key,)
        if not include_inactive:
            query += " AND status = 'active'"
        row = await (await db.execute(query, params)).fetchone()
    return _row_to_record(row) if row else None


async def list_agents(*, status: str | None = "active") -> list[AgentRecord]:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            rows = await (
                await db.execute(
                    "SELECT * FROM specialist_agents WHERE status = ? ORDER BY updated_at DESC",
                    (status,),
                )
            ).fetchall()
        else:
            rows = await (
                await db.execute(
                    "SELECT * FROM specialist_agents ORDER BY updated_at DESC"
                )
            ).fetchall()
    return [_row_to_record(row) for row in rows]


async def create_agent(spec: AgentSpec) -> AgentRecord:
    existing = await get_agent(spec.name, include_inactive=True)
    if existing:
        raise ValueError(f"agent already exists: {spec.name}")
    return await register_agent(spec)


async def update_agent(agent_id: int, updates: dict) -> AgentRecord | None:
    existing = await get_agent_by_id(agent_id, include_inactive=True)
    if not existing:
        return None

    payload = existing.model_dump()
    payload.pop("id", None)
    payload.pop("name_key", None)
    payload.pop("version", None)
    payload.pop("performance_score", None)
    payload.pop("last_used_at", None)
    payload.pop("last_improved_at", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)

    merged = {**payload, **{k: v for k, v in updates.items() if v is not None}}
    spec = AgentSpec.model_validate(merged)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conflict = await (
            await db.execute(
                "SELECT id FROM specialist_agents WHERE name_key = ? AND id != ?",
                (agent_name_key(spec.name), agent_id),
            )
        ).fetchone()
        if conflict:
            raise ValueError(f"agent already exists: {spec.name}")

        await db.execute(
            """
            UPDATE specialist_agents
            SET name = ?, name_key = ?, purpose = ?, instructions = ?, trigger_phrases = ?,
                runtime_config = ?, status = ?, version = version + 1, parent_agent_id = ?,
                learning_notes = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                spec.name,
                agent_name_key(spec.name),
                spec.purpose,
                spec.instructions,
                json.dumps(spec.trigger_phrases),
                json.dumps(spec.runtime.model_dump()),
                spec.status,
                spec.parent_agent_id,
                spec.learning_notes,
                agent_id,
            ),
        )
        await db.commit()
        row = await (
            await db.execute("SELECT * FROM specialist_agents WHERE id = ?", (agent_id,))
        ).fetchone()
    return _row_to_record(row) if row else None


async def archive_agent(agent_id: int) -> AgentRecord | None:
    return await update_agent(agent_id, {"status": "archived"})


async def record_agent_usage(name: str) -> None:
    await ensure_tables()
    key = agent_name_key(name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE specialist_agents
            SET last_used_at = datetime('now'), updated_at = datetime('now')
            WHERE name_key = ?
            """,
            (key,),
        )
        await db.commit()


async def update_learning_state(
    agent_id: int,
    *,
    performance_score: float | None = None,
    learning_notes: str | None = None,
    mark_improved: bool = False,
) -> None:
    await ensure_tables()
    fields = ["updated_at = datetime('now')"]
    params: list[object] = []
    if performance_score is not None:
        fields.append("performance_score = ?")
        params.append(round(float(performance_score), 4))
    if learning_notes is not None:
        fields.append("learning_notes = ?")
        params.append(learning_notes.strip()[:4000])
    if mark_improved:
        fields.append("last_improved_at = datetime('now')")
    params.append(agent_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE specialist_agents SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        await db.commit()


async def find_triggered_agent(text: str) -> AgentRecord | None:
    lowered = text.lower()
    for agent in await list_agents(status="active"):
        if any(phrase.lower() in lowered for phrase in agent.trigger_phrases):
            return agent
    return None
