"""Canonical voice UI state — single mapping from JarvisHelper /status JSON."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class VoiceUIState(StrEnum):
    OFFLINE = "offline"
    UNHEALTHY = "unhealthy"
    SLEEPING = "sleeping"
    STANDBY = "standby"
    AWAITING = "awaiting"
    CONVERSATION = "conversation"
    BUSY = "busy"
    SPEAKING = "speaking"


class VoiceUI(BaseModel):
    state: VoiceUIState
    label: str
    detail: str
    color: str
    animate: bool = False


_UI: dict[VoiceUIState, VoiceUI] = {
    VoiceUIState.OFFLINE: VoiceUI(
        state=VoiceUIState.OFFLINE,
        label="Offline",
        detail="JarvisHelper is not reachable",
        color="#6b7280",
        animate=False,
    ),
    VoiceUIState.UNHEALTHY: VoiceUI(
        state=VoiceUIState.UNHEALTHY,
        label="Unhealthy",
        detail="Check microphone and speech permissions",
        color="#ef4444",
        animate=False,
    ),
    VoiceUIState.SLEEPING: VoiceUI(
        state=VoiceUIState.SLEEPING,
        label="Sleeping",
        detail="Say Hey Willy to wake",
        color="#7c3aed",
        animate=True,
    ),
    VoiceUIState.STANDBY: VoiceUI(
        state=VoiceUIState.STANDBY,
        label="On guard",
        detail="Listening for wake word",
        color="#f59e0b",
        animate=False,
    ),
    VoiceUIState.AWAITING: VoiceUI(
        state=VoiceUIState.AWAITING,
        label="I'm listening",
        detail="Waiting for your command",
        color="#22c55e",
        animate=True,
    ),
    VoiceUIState.CONVERSATION: VoiceUI(
        state=VoiceUIState.CONVERSATION,
        label="Go ahead",
        detail="Conversation mode",
        color="#22c55e",
        animate=True,
    ),
    VoiceUIState.BUSY: VoiceUI(
        state=VoiceUIState.BUSY,
        label="Thinking…",
        detail="Processing your request",
        color="#3b82f6",
        animate=True,
    ),
    VoiceUIState.SPEAKING: VoiceUI(
        state=VoiceUIState.SPEAKING,
        label="Speaking",
        detail="William is talking",
        color="#3b82f6",
        animate=True,
    ),
}


def _with_detail(base: VoiceUI, detail: str | None) -> VoiceUI:
    if not detail:
        return base
    return base.model_copy(update={"detail": detail})


def map_helper_status(helper: dict | None) -> VoiceUI:
    """Map raw helper JSON (from macos.health) to the voice_ui contract."""
    if not helper or not helper.get("ok"):
        err = (helper or {}).get("error", "")
        return _with_detail(_UI[VoiceUIState.OFFLINE], err or None)

    if helper.get("voice_speaking"):
        return _UI[VoiceUIState.SPEAKING]

    if helper.get("busy"):
        return _UI[VoiceUIState.BUSY]

    if helper.get("sleeping"):
        return _UI[VoiceUIState.SLEEPING]

    if not helper.get("healthy", False):
        wake_status = helper.get("wake_status") or helper.get("statusMessage")
        return _with_detail(_UI[VoiceUIState.UNHEALTHY], wake_status)

    if helper.get("awaiting_command") or helper.get("listening_for_response"):
        if helper.get("conversation_mode"):
            return _UI[VoiceUIState.CONVERSATION]
        return _UI[VoiceUIState.AWAITING]

    if helper.get("conversation_mode"):
        return _UI[VoiceUIState.CONVERSATION]

    if helper.get("wake_listening") or helper.get("voice_state") == "standby":
        return _UI[VoiceUIState.STANDBY]

    voice_state = helper.get("voice_state")
    if isinstance(voice_state, str):
        try:
            return _UI[VoiceUIState(voice_state)]
        except ValueError:
            pass

    return _UI[VoiceUIState.STANDBY]


def voice_ui_payload(helper: dict | None) -> dict:
    """Serialize VoiceUI for API responses."""
    return map_helper_status(helper).model_dump()
