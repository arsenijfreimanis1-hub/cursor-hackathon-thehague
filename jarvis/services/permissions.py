"""macOS permission bootstrap — open settings panes without TCC spam."""

from __future__ import annotations

import logging
import subprocess
import time

from jarvis.config import settings
from jarvis.services import macos

log = logging.getLogger("jarvis.permissions")

_SETTINGS_COOLDOWN_SEC = 300.0
_last_settings_open_at = 0.0

_PANES = {
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "speech": "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition",
    "screen_recording": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
}


def open_settings_pane(pane: str, *, force: bool = False) -> bool:
    """Open a System Settings privacy pane, rate-limited to avoid spam loops."""
    global _last_settings_open_at
    url = _PANES.get(pane)
    if not url:
        return False
    now = time.monotonic()
    if not force and now - _last_settings_open_at < _SETTINGS_COOLDOWN_SEC:
        log.debug("settings pane %s skipped (cooldown)", pane)
        return False
    _last_settings_open_at = now
    subprocess.run(["open", url], check=False)
    return True


async def bootstrap(*, force_settings: bool = False) -> dict:
    """One-shot permission bootstrap: status check, native AX, open missing panes.

    Does NOT call CGRequestScreenCaptureAccess or speech/mic authorization prompts.
    """
    status = await macos.health()
    opened: list[str] = []
    native = await macos.handle_dialogs_native()

    if not status.get("accessibility"):
        if open_settings_pane("accessibility", force=force_settings):
            opened.append("accessibility")

    perms = status.get("permissions") or {}
    if perms.get("microphone") != "granted":
        if open_settings_pane("microphone", force=force_settings):
            opened.append("microphone")
    if perms.get("speech") not in ("granted", "authorized"):
        if open_settings_pane("speech", force=force_settings):
            opened.append("speech")

    screen = status.get("screen_watcher") or {}
    if settings.screen_watch_enabled and not screen.get("screen_capture_granted"):
        if open_settings_pane("screen_recording", force=force_settings):
            opened.append("screen_recording")

    if native.get("acted"):
        opened.append("native_dialog_handled")

    return {
        "ok": True,
        "helper": status,
        "native": native,
        "opened_settings": opened,
        "screen_capture_granted": screen.get("screen_capture_granted", False),
        "accessibility": status.get("accessibility", False),
    }
