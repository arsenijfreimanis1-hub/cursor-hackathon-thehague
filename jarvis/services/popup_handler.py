"""Detect macOS dialogs/popups via vision and click Allow/Deny/Dismiss."""

from __future__ import annotations

import logging
import re

from jarvis.config import settings
from jarvis.services import macos, ollama, permissions, security

log = logging.getLogger("jarvis.popup")

POPUP_PROMPT = """Inspect this Mac screenshot for modal dialogs, alerts, permission prompts, or popups blocking the screen.

If NO popup/dialog is visible, reply exactly:
POPUP: none

If a popup IS visible, reply exactly:
POPUP: yes
TITLE: short title of the dialog
BUTTONS: comma-separated button labels you see
RECOMMENDED: allow
or RECOMMENDED: deny
or RECOMMENDED: dismiss
ACTION: click X Y
REASON: one short line

Rules for RECOMMENDED:
- allow: Screen Recording, Accessibility, Microphone for JarvisHelper, William Agent, Cursor, Terminal, Python
- allow: OK, Continue, Open, Grant, Allow, Yes on safe confirmations
- deny: Delete, Erase, Remove, Don't Save (unless clearly junk), Sign Out, Purchase
- dismiss: Close/X on non-critical nag dialogs

Use pixel coordinates for ACTION (top-left origin). Pick the button matching RECOMMENDED."""

_ALLOW_WORDS = re.compile(
    r"\b(allow|ok|continue|open|grant|yes|accept|enable|confirm)\b",
    re.I,
)
_DENY_WORDS = re.compile(
    r"\b(deny|don'?t allow|delete|erase|remove|cancel|no|don'?t save|sign out)\b",
    re.I,
)
_SAFE_APPS = re.compile(
    r"\b(jarvis|william|cursor|terminal|python|screen recording|accessibility|microphone)\b",
    re.I,
)


def _parse_popup_analysis(analysis: str) -> dict:
    lines = analysis.splitlines()
    data: dict = {"popup": False}
    for line in lines:
        upper = line.strip().upper()
        if upper.startswith("POPUP:"):
            data["popup"] = "yes" in line.lower()
        elif upper.startswith("TITLE:"):
            data["title"] = line.split(":", 1)[1].strip()
        elif upper.startswith("BUTTONS:"):
            data["buttons"] = line.split(":", 1)[1].strip()
        elif upper.startswith("RECOMMENDED:"):
            data["recommended"] = line.split(":", 1)[1].strip().lower()
        elif upper.startswith("ACTION:"):
            data["action"] = line.split(":", 1)[1].strip()
        elif upper.startswith("REASON:"):
            data["reason"] = line.split(":", 1)[1].strip()

    click_m = re.search(r"click\s+(\d+)\s+(\d+)", (data.get("action") or "").lower())
    if click_m:
        data["click_x"] = float(click_m.group(1))
        data["click_y"] = float(click_m.group(2))
    return data


def _policy_override(parsed: dict) -> str | None:
    """Safety override for recommended action based on title/buttons."""
    blob = f"{parsed.get('title', '')} {parsed.get('buttons', '')} {parsed.get('reason', '')}"
    if _SAFE_APPS.search(blob):
        return "allow"
    if _DENY_WORDS.search(blob) and not _SAFE_APPS.search(blob):
        if "don't save" in blob.lower() and "cursor" in blob.lower():
            return None
        return "deny"
    return None


async def handle_popups(*, full_control: bool = True, max_attempts: int | None = None) -> dict:
    """Detect macOS dialogs and click Allow/Deny/Dismiss (native AX first, then vision)."""
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

        shot = await macos.screenshot()
        if not shot.get("ok"):
            err = shot.get("error", "screenshot failed")
            if "screencapture" in err.lower() or "screenshot" in err.lower():
                permissions.open_settings_pane("screen_recording")
            return {"ok": False, "error": err, "actions": actions, "needs_screen_recording": True}

        path = shot.get("path")
        try:
            analysis = await ollama.vision(path, POPUP_PROMPT)
        except Exception as exc:
            return {"ok": False, "error": str(exc), "actions": actions}

        parsed = _parse_popup_analysis(analysis)
        if not parsed.get("popup"):
            return {"ok": True, "popup": False, "attempts": attempt + 1, "actions": actions}

        recommended = _policy_override(parsed) or parsed.get("recommended", "dismiss")
        parsed["recommended_final"] = recommended

        if "click_x" not in parsed:
            actions.append({"attempt": attempt + 1, "parsed": parsed, "acted": False, "reason": "no coordinates"})
            break

        if not full_control:
            actions.append({"attempt": attempt + 1, "parsed": parsed, "acted": False, "reason": "no full control"})
            break

        click_result = await macos.click(parsed["click_x"], parsed["click_y"])
        action_record = {
            "attempt": attempt + 1,
            "title": parsed.get("title"),
            "recommended": recommended,
            "reason": parsed.get("reason"),
            "click": {"x": parsed["click_x"], "y": parsed["click_y"]},
            "click_result": click_result,
            "acted": click_result.get("ok", False),
        }
        actions.append(action_record)
        log.info("popup handled: %s -> %s", parsed.get("title"), recommended)

        if not click_result.get("ok"):
            break

    handled = any(a.get("acted") for a in actions)
    return {
        "ok": True,
        "popup": handled or bool(actions),
        "handled": handled,
        "actions": actions,
        "needs_reprompt": handled,
    }
