import pytest

from jarvis.services import popup_handler


def test_parse_no_popup():
    analysis = "POPUP: none\nSome other text"
    parsed = popup_handler._parse_popup_analysis(analysis)
    assert parsed.get("popup") is False


def test_parse_allow_popup():
    analysis = (
        "POPUP: yes\n"
        "TITLE: Screen Recording\n"
        "BUTTONS: Don't Allow, OK\n"
        "RECOMMENDED: allow\n"
        "ACTION: click 450 320\n"
        "REASON: JarvisHelper needs screen recording"
    )
    parsed = popup_handler._parse_popup_analysis(analysis)
    assert parsed.get("popup") is True
    assert parsed.get("click_x") == 450
    assert popup_handler._policy_override(parsed) == "allow"


@pytest.mark.asyncio
async def test_handle_popups_none(monkeypatch):
    async def fake_screenshot():
        return {"ok": True, "path": "/tmp/x.png"}

    async def fake_vision(path, prompt):
        return "POPUP: none"

    async def fake_full_access():
        return True

    monkeypatch.setattr("jarvis.services.macos.screenshot", fake_screenshot)
    monkeypatch.setattr("jarvis.services.ollama.vision", fake_vision)
    monkeypatch.setattr("jarvis.services.security.is_full_access", fake_full_access)

    result = await popup_handler.handle_popups(full_control=True)
    assert result["ok"] is True
    assert result.get("popup") is False
