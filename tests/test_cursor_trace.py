import pytest

from jarvis.services import cursor_trace


@pytest.mark.asyncio
async def test_cursor_trace_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cursor_trace, "DB_PATH", tmp_path / "trace.db")
    await cursor_trace.ensure_tables()

    db_id = await cursor_trace.start_run(prompt="fix improve_run", source="test")
    await cursor_trace.append_event(db_id, 0, {"type": "thinking", "text": "I should check the test file"})
    await cursor_trace.append_event(db_id, 1, {"type": "assistant", "text": "Fixed the import."})
    await cursor_trace.finish_run(db_id, run_id="run-abc", status="completed", result="Fixed import")

    run = await cursor_trace.get_run(db_id)
    assert run is not None
    assert len(run["events"]) == 2
    assert run["events"][0]["event_type"] == "thinking"

    transcript = await cursor_trace.format_transcript(db_id)
    assert "THINKING" in transcript
    assert "Fixed the import" in transcript
