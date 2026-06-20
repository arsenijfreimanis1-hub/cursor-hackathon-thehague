"""Execution-first dispatch — run local actions before LLM chat."""

from __future__ import annotations

from jarvis.services import cursor_agent, security, system_control, terminal


async def try_local_execute(text: str, *, voice: bool = False) -> dict | None:
    """Return a route result if this text is a local macOS/terminal action, else None."""
    if system_control.parse_command(text):
        result = await system_control.execute(text)
        if result.get("ok"):
            return {
                "reply": result.get("reply", "Done, boss."),
                "engine": "system",
                "intent": "system",
                "executed": True,
            }
        err = result.get("error", "")
        if err and err != "not a system command":
            return {
                "reply": result.get("reply", "Cannot do that, boss."),
                "engine": "system",
                "intent": "system",
                "executed": False,
            }

    if terminal.resolve_command(text):
        full_access = await security.is_full_access()
        result = await terminal.execute(text, full_access=full_access, voice=voice)
        if result.get("ok"):
            return {
                "reply": result.get("reply", "Done, boss."),
                "engine": "terminal",
                "intent": "terminal",
                "executed": True,
                "command": result.get("command"),
                "stdout": result.get("stdout"),
            }
        if result.get("error") != "not a terminal command":
            return {
                "reply": result.get("reply", result.get("error", "Cannot run that, boss.")),
                "engine": "terminal",
                "intent": "terminal",
                "executed": False,
            }
    return None


def needs_cursor_plan(text: str) -> bool:
    """Compound or project-scale work — plan with Cursor (Claude tier), not local chat."""
    lowered = text.lower()
    if cursor_agent.should_escalate(text):
        return True
    if len(text) > 120 and any(
        w in lowered
        for w in ("and then", "also", "first", "second", "after that", "build", "create", "deploy")
    ):
        return True
    return False
