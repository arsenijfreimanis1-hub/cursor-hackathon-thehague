"""Detect macOS dialogs/popups via Accessibility only (no Screen Recording)."""

from __future__ import annotations

import logging
import re

from jarvis.config import settings
from jarvis.services import macos, security

log = logging.getLogger("jarvis.popup")

_ALLOW_WORDS = re.compile(
    r"\b(allow|ok|continue|open|grant|yes|accept|enable|confirm)\b",
    re.I,
)
_DENY_WORDS = re.compile(
    r"\b(deny|don'?t allow|delete|erase|remove|cancel|no|don'?t save|sign out)\b",
    re.I,
)
_SAFE_APPS = re.compile(
    r"\b(jarvis|william|cursor|terminal|python|accessibility|microphone)\b",
    re.I,
)


def _policy_override(title: str, button: str) -> str | None:
    blob = f"{title} {button}"
    if _SAFE_APPS.search(blob):
        return "allow"
    if _DENY_WORDS.search(blob) and not _SAFE_APPS.search(blob):
        return "deny"
    return None


async def handle_popups(*, full_control: bool = True, max_attempts: int | None = None) -> dict:
    """Detect macOS dialogs and click Allow/Deny/Dismiss using Accessibility only."""
    if not settings.popup_handler_enabled:
        return {"ok": True, "skipped": True, "reason": "disabled"}

    if full_control and not await security.is_full_access():
        return {"ok": False, "error": "full access required for popup clicks — enable in admin panel"}

    attempts = max_attempts or settings.popup_max_attempts
    actions: list[dict] = []

    for attempt in range(attempts):
        native = await macos.handle_dialogs_native()
        if native.get("acted"):
            native_actions = native.get("actions") or []
            is_permission_dialog = any(
                a.get("kind") in ("dialog_button", "privacy_toggle") for a in native_actions
            )
            actions.append({
                "attempt": attempt + 1,
                "method": "accessibility",
                "acted": True,
                "native": native,
            })
            return {
                "ok": True,
                "popup": True,
                "handled": True,
                "actions": actions,
                "needs_reprompt": is_permission_dialog,
            }

        # No popup found via AX — stop (no screenshot/vision fallback).
        return {"ok": True, "popup": False, "attempts": attempt + 1, "actions": actions, "method": "accessibility"}

    handled = any(a.get("acted") for a in actions)
    return {
        "ok": True,
        "popup": handled or bool(actions),
        "handled": handled,
        "actions": actions,
        "method": "accessibility",
    }
