"""Screen vision + desktop control for autonomous runs."""

from __future__ import annotations

import re
import subprocess

from jarvis.services import approvals, macos, ollama, remote_control, security

VISION_PROMPT = """Describe what is on this Mac screen in 2-3 sentences.
Then suggest ONE concrete action William Agent should take.
Format exactly:
DESCRIPTION: ...
ACTION: click X Y
or ACTION: type "some text"
or ACTION: key return
or ACTION: key tab
or ACTION: open_url https://example.com
Use pixel coordinates for click (top-left origin)."""

_IMPROVE_PROMPT = """You are testing the William Agent Mac kiosk and web UI.
Describe any visible bugs, error messages, or broken UI in 2-3 sentences.
Then suggest ONE action to proceed (dismiss popup, click button, switch tab).
Format:
DESCRIPTION: ...
ACTION: click X Y
or ACTION: type "text"
or ACTION: key return
or ACTION: open_url http://127.0.0.1:8787"""


async def _parse_and_execute(analysis: str, *, full_control: bool) -> dict:
    if not full_control and not await security.is_full_access():
        return {"acted": False, "reason": "no full access"}

    action_line = ""
    for line in analysis.splitlines():
        if line.strip().upper().startswith("ACTION:"):
            action_line = line.split(":", 1)[1].strip()
            break
    if not action_line:
        return {"acted": False, "reason": "no ACTION in analysis"}

    lower = action_line.lower()
    if lower.startswith("open_url") or lower.startswith("open "):
        url = action_line.split(maxsplit=1)[-1].strip().strip('"')
        if url.startswith("http"):
            subprocess.run(["/usr/bin/open", url], check=False, timeout=10)
            return {"acted": True, "action": "open_url", "url": url}

    click_m = re.search(r"click\s+(\d+)\s+(\d+)", lower)
    if click_m:
        x, y = float(click_m.group(1)), float(click_m.group(2))
        result = await macos.click(x, y)
        return {"acted": True, "action": "click", "action_result": result}

    type_m = re.search(r'type\s+"([^"]+)"', action_line, re.I)
    if type_m:
        result = await macos.type_text(type_m.group(1))
        return {"acted": True, "action": "type", "action_result": result}

    key_m = re.search(r"key\s+(\w+)", lower)
    if key_m:
        key = key_m.group(1)
        mods = ["cmd"] if "cmd" in lower else []
        result = await macos.press_key(key, modifiers=mods)
        return {"acted": True, "action": "key", "action_result": result}

    return await approvals.execute_desktop_action(f"ACTION: {action_line}")


async def _remote_control_active_response() -> dict:
    return {
        "ok": True,
        "remote_control_active": True,
        "acted": False,
        "reason": "remote control active — vision pipeline bypassed",
    }


async def analyze_screen() -> dict:
    if await remote_control.is_enabled():
        return await _remote_control_active_response()

    shot = await macos.screenshot()
    if not shot.get("ok"):
        return {"ok": False, "error": shot.get("error", "screenshot failed")}

    path = shot.get("path")
    if not path:
        return {"ok": False, "error": "no screenshot path"}

    try:
        analysis = await ollama.vision(path, VISION_PROMPT)
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "hint": "Install a vision model: ollama pull moondream",
            "screenshot": path,
        }

    if await security.is_full_access():
        executed = await _parse_and_execute(analysis, full_control=True)
        return {
            "ok": True,
            "analysis": analysis,
            "screenshot": path,
            "executed": executed.get("acted", False),
            "side_effect": executed,
            "full_access": True,
        }

    approval = await approvals.request_approval(
        action="desktop_action",
        detail=analysis,
    )
    return {
        "ok": True,
        "analysis": analysis,
        "screenshot": path,
        "approval_id": approval["id"],
    }


async def analyze_and_act(*, full_control: bool = False) -> dict:
    if await remote_control.is_enabled():
        return await _remote_control_active_response()

    shot = await macos.screenshot()
    if not shot.get("ok"):
        return {"ok": False, "error": shot.get("error", "screenshot failed")}
    path = shot.get("path")
    try:
        analysis = await ollama.vision(path, _IMPROVE_PROMPT)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "screenshot": path}

    executed = await _parse_and_execute(analysis, full_control=full_control)
    return {
        "ok": True,
        "analysis": analysis,
        "screenshot": path,
        "acted": executed.get("acted", False),
        "action_result": executed,
    }
