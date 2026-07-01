"""Desktop awareness + control via Accessibility API (no Screen Recording)."""

from __future__ import annotations

import re
import subprocess

from jarvis.services import activity_stream, approvals, macos, ollama, remote_control, security

_QUERY_SYSTEM = """You see the user's Mac through its Accessibility tree (apps, windows, buttons, text fields).
No screenshot — this is structured UI text from the frontmost app.

Answer the user's question in 1-3 sentences, then suggest ONE action if they want UI interaction.

Format exactly:
DESCRIPTION: <answer>
ACTION: none
or ACTION: press "Button Label"
or ACTION: type "text to type"
or ACTION: key return
or ACTION: key tab
or ACTION: open_url https://example.com

Rules:
- Use press with the exact button/menu label from the UI tree.
- Do not invent buttons that are not listed.
- Prefer press over pixel clicks."""

_DESCRIBE_SYSTEM = """You see a Mac app's Accessibility UI tree. Describe what the user is looking at in 2-3 sentences.
Suggest ONE concrete action William should take.

Format exactly:
DESCRIPTION: ...
ACTION: none
or ACTION: press "label"
or ACTION: type "text"
or ACTION: key return
or ACTION: open_url https://example.com"""

_IMPROVE_SYSTEM = """You are testing the William Agent Mac UI.
Review the Accessibility tree for bugs, errors, or broken UI. Suggest ONE action to proceed.

Format:
DESCRIPTION: ...
ACTION: press "label"
or ACTION: type "text"
or ACTION: key return
or ACTION: open_url http://127.0.0.1:8787"""


async def _fetch_context() -> dict:
    ctx = await macos.desktop_context()
    if not ctx.get("ok"):
        return ctx
    return ctx


async def _analyze_context(system: str, context_text: str, user_query: str = "") -> str:
    user = f"User question: {user_query}\n\nUI TREE:\n{context_text}" if user_query else f"UI TREE:\n{context_text}"
    return await ollama.chat(user, system=system)


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
    if lower in ("none", "n/a", "no"):
        return {"acted": False, "reason": "no action needed"}

    if lower.startswith("open_url") or lower.startswith("open "):
        url = action_line.split(maxsplit=1)[-1].strip().strip('"')
        if url.startswith("http"):
            subprocess.run(["/usr/bin/open", url], check=False, timeout=10)
            return {"acted": True, "action": "open_url", "url": url}

    press_m = re.search(r'press\s+"([^"]+)"', action_line, re.I) or re.search(
        r"press\s+(\S.+)$", action_line, re.I
    )
    click_label_m = re.search(r'click\s+"([^"]+)"', action_line, re.I) or re.search(
        r"click\s+(?:the\s+)?(.+)$", action_line, re.I
    )
    target = None
    if press_m:
        target = press_m.group(1).strip()
    elif click_label_m and not re.search(r"click\s+\d+", lower):
        target = click_label_m.group(1).strip().strip('"')

    if target:
        result = await macos.desktop_press(target)
        return {
            "acted": result.get("ok", False),
            "action": "press",
            "target": target,
            "action_result": result,
            "method": "accessibility",
        }

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
        "reason": "remote control active — desktop pipeline bypassed",
    }


async def analyze_screen() -> dict:
    if await remote_control.is_enabled():
        return await _remote_control_active_response()

    ctx = await _fetch_context()
    if not ctx.get("ok"):
        return {"ok": False, "error": ctx.get("error", "desktop context failed"), "method": "accessibility"}

    text = ctx.get("text") or ""
    try:
        analysis = await _analyze_context(_DESCRIBE_SYSTEM, text)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "context": ctx, "method": "accessibility"}

    if await security.is_full_access():
        executed = await _parse_and_execute(analysis, full_control=True)
        return {
            "ok": True,
            "analysis": analysis,
            "context": ctx,
            "executed": executed.get("acted", False),
            "side_effect": executed,
            "full_access": True,
            "method": "accessibility",
        }

    approval = await approvals.request_approval(action="desktop_action", detail=analysis)
    return {
        "ok": True,
        "analysis": analysis,
        "context": ctx,
        "approval_id": approval["id"],
        "method": "accessibility",
    }


async def analyze_and_act(*, full_control: bool = False) -> dict:
    if await remote_control.is_enabled():
        return await _remote_control_active_response()

    ctx = await _fetch_context()
    if not ctx.get("ok"):
        return {"ok": False, "error": ctx.get("error", "desktop context failed")}
    text = ctx.get("text") or ""
    try:
        analysis = await _analyze_context(_IMPROVE_SYSTEM, text)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "context": ctx}

    executed = await _parse_and_execute(analysis, full_control=full_control)
    return {
        "ok": True,
        "analysis": analysis,
        "context": ctx,
        "acted": executed.get("acted", False),
        "action_result": executed,
        "method": "accessibility",
    }


def _extract_description(analysis: str) -> str:
    for line in analysis.splitlines():
        if line.strip().upper().startswith("DESCRIPTION:"):
            return line.split(":", 1)[1].strip()
    return analysis.strip()[:400]


def _wants_action(analysis: str) -> bool:
    upper = analysis.upper()
    if "ACTION: NONE" in upper:
        return False
    return "ACTION:" in upper and not upper.strip().endswith("ACTION:")


async def observe_and_act(query: str, *, max_steps: int = 3, voice: bool = False) -> dict:
    """Accessibility tree → LLM → press/type (no Screen Recording)."""
    if await remote_control.is_enabled():
        return await _remote_control_active_response()

    steps: list[dict] = []
    last_description = ""

    for step in range(max_steps):
        await activity_stream.emit(
            "screen",
            f"Reading UI {step + 1}",
            detail="Scanning frontmost app via Accessibility…",
            status="running",
            engine="accessibility",
        )
        ctx = await _fetch_context()
        if not ctx.get("ok"):
            err = ctx.get("error", "desktop context failed")
            await activity_stream.emit("screen", "UI scan failed", detail=err, status="error")
            return {"ok": False, "error": err, "steps": steps, "method": "accessibility"}

        app = ctx.get("app") or "app"
        window = ctx.get("window_title") or ""
        summary = f"{app} · {window}"[:120]
        text = ctx.get("text") or ""

        await activity_stream.emit(
            "screen",
            "Analyzing UI",
            detail=summary,
            status="running",
            engine="accessibility",
        )

        try:
            analysis = await _analyze_context(_QUERY_SYSTEM, text, user_query=query)
        except Exception as exc:
            await activity_stream.emit("screen", "Analysis failed", detail=str(exc), status="error")
            return {"ok": False, "error": str(exc), "steps": steps, "method": "accessibility"}

        last_description = _extract_description(analysis)
        step_record: dict = {
            "step": step + 1,
            "analysis": analysis,
            "context": {"app": app, "window": window},
            "acted": False,
            "method": "accessibility",
        }

        await activity_stream.emit(
            "screen",
            "UI understood",
            detail=last_description,
            status="done",
            engine="accessibility",
        )

        if not _wants_action(analysis):
            steps.append(step_record)
            break

        full_access = await security.is_full_access()
        if not full_access:
            approval = await approvals.request_approval(action="desktop_action", detail=analysis)
            step_record["approval_id"] = approval["id"]
            steps.append(step_record)
            await activity_stream.emit(
                "screen",
                "Action needs approval",
                detail=last_description,
                status="done",
                engine="accessibility",
            )
            return {
                "ok": True,
                "description": last_description,
                "approval_id": approval["id"],
                "steps": steps,
                "method": "accessibility",
            }

        await activity_stream.emit(
            "screen",
            "Acting on UI",
            detail="Press / type via Accessibility…",
            status="running",
            engine="desktop",
        )
        executed = await _parse_and_execute(analysis, full_control=True)
        step_record["acted"] = executed.get("acted", False)
        step_record["action"] = executed
        steps.append(step_record)

        await activity_stream.emit(
            "screen",
            "Action complete" if executed.get("acted") else "No action taken",
            detail=executed.get("target") or executed.get("action") or executed.get("reason", ""),
            status="done",
            engine="desktop",
        )

        if not executed.get("acted"):
            break

    reply = last_description or "I read what's on your screen, boss." if voice else (last_description or "UI analyzed.")
    return {
        "ok": True,
        "description": last_description,
        "reply": reply,
        "steps": steps,
        "acted": any(s.get("acted") for s in steps),
        "method": "accessibility",
    }
