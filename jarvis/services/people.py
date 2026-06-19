import aiosqlite

from jarvis.database import DB_PATH

PEOPLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    netatmo_id TEXT UNIQUE,
    name TEXT NOT NULL,
    face_url TEXT,
    is_known INTEGER NOT NULL DEFAULT 0,
    greet_enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT
);
"""


async def ensure_people_table() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(PEOPLE_SCHEMA)
        await db.commit()


async def list_people() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM people ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_by_netatmo_id(netatmo_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM people WHERE netatmo_id = ?", (netatmo_id,)
        )).fetchone()
        return dict(row) if row else None


async def upsert_person(
    netatmo_id: str,
    name: str,
    *,
    face_url: str | None = None,
    is_known: bool = True,
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        existing = await (await db.execute(
            "SELECT * FROM people WHERE netatmo_id = ?", (netatmo_id,)
        )).fetchone()
        if existing:
            await db.execute(
                """UPDATE people SET name = ?, face_url = COALESCE(?, face_url),
                   is_known = ?, last_seen_at = datetime('now') WHERE netatmo_id = ?""",
                (name, face_url, int(is_known), netatmo_id),
            )
        else:
            await db.execute(
                """INSERT INTO people (netatmo_id, name, face_url, is_known, last_seen_at)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (netatmo_id, name, face_url, int(is_known)),
            )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM people WHERE netatmo_id = ?", (netatmo_id,)
        )).fetchone()
        return dict(row)


async def mark_seen(netatmo_id: str, face_url: str | None = None) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE people SET last_seen_at = datetime('now'), face_url = COALESCE(?, face_url) WHERE netatmo_id = ?",
            (face_url, netatmo_id),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM people WHERE netatmo_id = ?", (netatmo_id,)
        )).fetchone()
        return dict(row) if row else None


async def forget_person(person_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM people WHERE id = ?", (person_id,))
        await db.commit()
        return cursor.rowcount > 0
