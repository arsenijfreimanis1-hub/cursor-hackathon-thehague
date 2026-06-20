import pytest

from jarvis.services import notion_sync


@pytest.mark.asyncio
async def test_sync_screen_summary_skipped_when_unconfigured(monkeypatch):
    monkeypatch.setattr(notion_sync.settings, "notion_api_key", "")
    monkeypatch.setattr(notion_sync.settings, "notion_parent_page_id", "")
    result = await notion_sync.sync_screen_summary(
        {
            "title": "Test activity",
            "summary": "Boss edited improve_run.py",
            "observation_type": "how-it-works",
            "category": "work",
            "productivity_state": "focused",
            "apps": ["Cursor"],
        }
    )
    assert result.get("skipped") is True


@pytest.mark.asyncio
async def test_sync_screen_summary_creates_page(monkeypatch):
    monkeypatch.setattr(notion_sync, "configured", lambda: True)
    monkeypatch.setattr(notion_sync, "create_learning_page", _fake_create_page)
    monkeypatch.setattr(notion_sync, "sync_improvement_insight", _fake_improvement)

    result = await notion_sync.sync_screen_summary(
        {
            "title": "pytest error",
            "summary": "Traceback in test_improve_run",
            "observation_type": "gotcha",
            "category": "work",
            "productivity_state": "focused",
            "apps": ["Cursor"],
        }
    )
    assert result["ok"] is True
    assert result["page_id"] == "page-123"


async def _fake_create_page(**kwargs):
    return {"ok": True, "page_id": "page-123", "url": "https://notion.so/page-123"}


async def _fake_improvement(**kwargs):
    return {"ok": True, "page_id": "page-friction"}
