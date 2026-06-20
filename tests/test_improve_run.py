import pytest

from jarvis.services import improve_run


@pytest.mark.asyncio
async def test_improve_run_start_stop(monkeypatch):
    async def fake_run_all():
        return [{"name": "core_health", "ok": True}]

    async def fake_ui_probe(run_id):
        return None

    monkeypatch.setattr(improve_run.improve_tests, "run_all", fake_run_all)
    monkeypatch.setattr(improve_run, "_ui_probe", fake_ui_probe)
    async def fake_open_surfaces():
        return None

    monkeypatch.setattr(improve_run, "_open_test_surfaces", fake_open_surfaces)
    monkeypatch.setattr(improve_run.self_modify, "ensure_repo", lambda: None)
    async def fake_full_access(_):
        return None

    monkeypatch.setattr(improve_run.security, "set_full_access", fake_full_access)

    started = await improve_run.start(duration_minutes=5)
    assert started["ok"] is True
    assert started["run_id"]

    status = await improve_run.get_status()
    assert status["running"] is True
    assert status["duration_minutes"] == 5

    stopped = await improve_run.stop()
    assert stopped["ok"] is True

    if improve_run._active_task:
        try:
            await improve_run._active_task
        except Exception:
            pass

    final = await improve_run.get_status(started["run_id"])
    assert final["status"] in ("stopped", "completed", "failed")
