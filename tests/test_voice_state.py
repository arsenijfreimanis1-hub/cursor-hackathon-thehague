"""Tests for jarvis.services.voice_state."""

import pytest

from jarvis.services.voice_state import VoiceUIState, map_helper_status


@pytest.mark.parametrize(
    "helper,expected",
    [
        (None, VoiceUIState.OFFLINE),
        ({"ok": False, "error": "connection refused"}, VoiceUIState.OFFLINE),
        ({"ok": True, "voice_speaking": True}, VoiceUIState.SPEAKING),
        ({"ok": True, "busy": True, "healthy": True}, VoiceUIState.BUSY),
        ({"ok": True, "sleeping": True}, VoiceUIState.SLEEPING),
        ({"ok": True, "healthy": False}, VoiceUIState.UNHEALTHY),
        ({"ok": True, "healthy": True, "awaiting_command": True}, VoiceUIState.AWAITING),
        (
            {"ok": True, "healthy": True, "conversation_mode": True, "listening_for_response": True},
            VoiceUIState.CONVERSATION,
        ),
        ({"ok": True, "healthy": True, "wake_listening": True}, VoiceUIState.STANDBY),
        ({"ok": True, "healthy": True, "voice_state": "sleeping"}, VoiceUIState.SLEEPING),
    ],
)
def test_map_helper_status(helper, expected):
    ui = map_helper_status(helper)
    assert ui.state == expected
    assert ui.label
    assert ui.color.startswith("#")


def test_voice_ui_payload_keys():
    from jarvis.services.voice_state import voice_ui_payload

    payload = voice_ui_payload({"ok": True, "healthy": True, "wake_listening": True})
    assert set(payload.keys()) == {"state", "label", "detail", "color", "animate"}
    assert payload["state"] == "standby"
