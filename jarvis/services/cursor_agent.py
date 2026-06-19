import asyncio
import os

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions

from jarvis.config import settings

COMPLEX_HINTS = (
    "build app",
    "create app",
    "create website",
    "full stack",
    "refactor",
    "implement",
    "scaffold",
    "codebase",
    "pull request",
    "architecture",
    "typescript project",
    "react app",
    "backend api",
    "deploy",
    "write tests for",
    "fix bug in",
    "add feature",
)


def should_escalate(text: str) -> bool:
    lowered = text.lower()
    if len(text) > 600:
        return True
    return any(hint in lowered for hint in COMPLEX_HINTS)


def _cursor_prompt(prompt: str, cwd: str, api_key: str, model: str) -> dict:
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=api_key,
                model=model,
                local=LocalAgentOptions(cwd=cwd, setting_sources=[]),
            ),
        )
        return {
            "ok": result.status != "error",
            "status": result.status,
            "result": result.result or "",
            "run_id": getattr(result, "id", None),
        }
    except CursorAgentError as exc:
        return {"ok": False, "error": str(exc), "retryable": exc.is_retryable}


async def run(prompt: str, *, cwd: str | None = None) -> dict:
    api_key = settings.resolved_cursor_api_key()
    if not api_key:
        return {
            "ok": False,
            "error": "CURSOR_API_KEY not set — add to ~/.jarvis-core/.env or export it",
        }
    workdir = cwd or str(settings.workspace_dir)
    return await asyncio.to_thread(_cursor_prompt, prompt, workdir, api_key, settings.cursor_model)
