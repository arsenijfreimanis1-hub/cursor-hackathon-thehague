import pytest
from datetime import datetime, timedelta, timezone

from jarvis.services import screen_observer


def _iso_ago(**kwargs) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kwargs)).isoformat()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_ingest_and_index(tmp_path, monkeypatch):
    db_path = tmp_path / "screen.db"
    monkeypatch.setattr(screen_observer, "DB_PATH", db_path)
    await screen_observer.ensure_tables()

    events = [
        {
            "ts": _iso_ago(seconds=30),
            "app": "Cursor",
            "window_title": "improve_run.py",
            "ocr_text": "def start(): error failed",
            "phash": "abc",
        },
        {
            "ts": _iso_ago(seconds=20),
            "app": "Cursor",
            "window_title": "improve_run.py",
            "ocr_text": "pytest traceback",
            "phash": "abd",
        },
    ]
    result = await screen_observer.ingest_events(events)
    assert result["ok"] is True
    assert result["ingested"] == 2

    index = await screen_observer.get_activity_index(minutes=60)
    assert index == ""


@pytest.mark.asyncio
async def test_summary_and_friction(tmp_path, monkeypatch):
    db_path = tmp_path / "screen.db"
    monkeypatch.setattr(screen_observer, "DB_PATH", db_path)
    await screen_observer.ensure_tables()

    async def fake_chat(prompt, **kwargs):
        return (
            '{"title":"pytest failure in improve_run",'
            '"summary":"Boss debugged improve_run tests with errors visible.",'
            '"observation_type":"gotcha","category":"work","productivity_state":"focused"}'
        )

    monkeypatch.setattr("jarvis.services.ollama.chat", fake_chat)

    await screen_observer.ingest_events(
        [
            {
                "ts": _iso_ago(seconds=15),
                "app": "Cursor",
                "ocr_text": "error failed traceback",
                "phash": "x1",
            }
        ]
    )
    summary = await screen_observer.build_window_summary()
    assert summary is not None
    assert summary["observation_type"] == "gotcha"

    signals = await screen_observer.detect_improvement_signals(summary)
    assert len(signals) == 1
    assert signals[0]["kind"] == "screen_friction"

    index = await screen_observer.get_activity_index(minutes=60)
    assert "#" in index
    assert "pytest" in index.lower() or "improve" in index.lower()


@pytest.mark.asyncio
async def test_progressive_disclosure(tmp_path, monkeypatch):
    db_path = tmp_path / "screen.db"
    monkeypatch.setattr(screen_observer, "DB_PATH", db_path)
    await screen_observer.ensure_tables()

    start = _iso_ago(minutes=1)
    end = _iso_now()
    async with __import__("aiosqlite").connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO screen_summaries
            (window_start, window_end, summary, title, observation_type, category, productivity_state)
            VALUES (?, ?, 'Working on jarvis improve_run tests', 'improve_run debugging', 'how-it-works', 'work', 'focused')
            """,
            (start, end),
        )
        await db.commit()

    timeline = await screen_observer.get_activity_timeline(anchor_id=1, depth=1)
    assert "improve_run" in timeline.lower()

    details = await screen_observer.get_capture_details([1])
    assert "improve_run" in details.lower()

    ctx = await screen_observer.get_recent_context(minutes=60, query="what was I doing with improve_run")
    assert "Screen activity" in ctx or "improve" in ctx.lower()
