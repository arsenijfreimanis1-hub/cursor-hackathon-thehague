import re
import uuid

import aiosqlite

from jarvis.database import DB_PATH

HISTORY_LIMIT = 12
VOICE_HISTORY_LIMIT = 20
TIME_GAP_MINUTES = 45
TOPIC_WORDS = 6

_STOP = frozenset(
    "what when where that this with have will boss about your mine just like tell "
    "open play watch listen want need please could would should".split()
)


def _topic_key(text: str) -> str:
    words = re.findall(r"[a-z]{3,}", text.lower())
    sig = [w for w in words if w not in _STOP][:TOPIC_WORDS]
    return " ".join(sorted(set(sig)))


def _topics_related(a: str, b: str) -> bool:
    if not a or not b:
        return True
    wa, wb = set(a.split()), set(b.split())
    if not wa or not wb:
        return True
    overlap = len(wa & wb)
    return overlap >= 1 or (overlap / max(len(wa), len(wb))) >= 0.3


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL DEFAULT 'web',
                topic TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_active_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                engine TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            """
        )
        try:
            await db.execute("ALTER TABLE conversations ADD COLUMN topic TEXT NOT NULL DEFAULT ''")
            await db.commit()
        except Exception:
            pass


async def _find_merge_candidate(source: str, message: str) -> str | None:
    topic = _topic_key(message)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (
            await db.execute(
                """
                SELECT id, topic FROM conversations
                WHERE source = ?
                  AND datetime(last_active_at) >= datetime('now', ?)
                ORDER BY last_active_at DESC LIMIT 1
                """,
                (source, f"-{TIME_GAP_MINUTES} minutes"),
            )
        ).fetchone()
        if not row:
            return None
        if _topics_related(row["topic"] or "", topic):
            await db.execute(
                "UPDATE conversations SET last_active_at = datetime('now'), topic = ? WHERE id = ?",
                (topic or row["topic"], row["id"]),
            )
            await db.commit()
            return row["id"]
    return None


async def get_or_create(
    session_id: str | None,
    *,
    source: str = "web",
    message: str = "",
) -> tuple[str, bool]:
    """Return (conversation_id, is_new_session)."""
    await ensure_tables()

    if session_id:
        async with aiosqlite.connect(DB_PATH) as db:
            row = await (
                await db.execute("SELECT id FROM conversations WHERE id = ?", (session_id,))
            ).fetchone()
            if row:
                topic = _topic_key(message)
                await db.execute(
                    "UPDATE conversations SET last_active_at = datetime('now'), topic = COALESCE(NULLIF(?, ''), topic) WHERE id = ?",
                    (topic, session_id),
                )
                await db.commit()
                return session_id, False

    merged = await _find_merge_candidate(source, message)
    if merged:
        return merged, False

    new_id = str(uuid.uuid4())
    topic = _topic_key(message)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO conversations (id, source, topic) VALUES (?, ?, ?)",
            (new_id, source, topic),
        )
        await db.commit()
    return new_id, True


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    engine: str | None = None,
) -> None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (conversation_id, role, content, engine) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, engine),
        )
        await db.execute(
            "UPDATE conversations SET last_active_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        await db.commit()


def format_context(history: list[dict], *, limit: int = 10) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-limit:]:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()[:240]
        if content:
            lines.append(f"{role}: {content}")
    if not lines:
        return ""
    return "RECENT CONVERSATION:\n" + "\n".join(lines)


async def get_history(conversation_id: str, *, limit: int = HISTORY_LIMIT) -> list[dict]:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT role, content, engine, created_at FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in reversed(rows)]


async def get_active(source: str | None = None) -> dict | None:
    await ensure_tables()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if source:
            row = await (
                await db.execute(
                    """
                    SELECT * FROM conversations WHERE source = ?
                    ORDER BY last_active_at DESC LIMIT 1
                    """,
                    (source,),
                )
            ).fetchone()
        else:
            row = await (
                await db.execute(
                    "SELECT * FROM conversations ORDER BY last_active_at DESC LIMIT 1"
                )
            ).fetchone()
        return dict(row) if row else None
