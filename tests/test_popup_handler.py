import pytest

from jarvis.services import popup_handler


@pytest.mark.asyncio
async def test_handle_popups_none(monkeypatch):
    async def fake_native():
        return {"ok": True, "acted": False, "actions": []}

    async def fake_full_access():
        return True

    monkeypatch.setattr("jarvis.services.macos.handle_dialogs_native", fake_native)
    monkeypatch.setattr("jarvis.services.security.is_full_access", fake_full_access)

    result = await popup_handler.handle_popups(full_control=True)
    assert result["ok"] is True
    assert result.get("popup") is False
    assert result.get("method") == "accessibility"
