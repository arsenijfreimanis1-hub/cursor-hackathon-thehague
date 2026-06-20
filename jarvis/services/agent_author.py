"""Minimal specialist-agent authoring helpers."""

from __future__ import annotations

import json

from jarvis.config import settings
from jarvis.services import agent_registry, cursor_agent
from jarvis.services.agent_types import AgentRecord, AgentSpec


def _extract_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("authoring response did not include a JSON object")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("authoring response was not valid JSON") from exc


async def create_from_spec(spec: AgentSpec) -> AgentRecord:
    return await agent_registry.create_agent(spec)


async def draft_spec_from_prompt(
    prompt: str,
    *,
    workspace_dir: str | None = None,
    model: str | None = None,
) -> AgentSpec:
    author_prompt = (
        "Draft a reusable specialist agent spec for William Agent.\n"
        "Return JSON only with keys: name, purpose, instructions, trigger_phrases, "
        "status, runtime, parent_agent_id, learning_notes.\n"
        'Set status to "active".\n'
        'Set runtime.execution_engine to "cursor".\n'
        'Set runtime.autonomy_mode to "supervised" unless the request clearly needs "assisted".\n'
        'Set runtime.allowed_tools to a minimal allowlist chosen from: '
        '["cursor_agent.run", "memory.retrieve", "memory.store", "system_control.execute", '
        '"terminal.execute", "web.research"].\n'
        "Keep trigger_phrases short and specific.\n"
        "Make instructions concrete and actionable.\n\n"
        f"User request:\n{prompt}"
    )
    result = await cursor_agent.run(
        author_prompt,
        cwd=workspace_dir or str(settings.workspace_dir),
        model=model,
    )
    if not result.get("ok"):
        raise ValueError(result.get("error", "agent authoring failed"))
    payload = _extract_json_object(result.get("result", ""))
    return AgentSpec.model_validate(payload)


async def create_from_prompt(
    prompt: str,
    *,
    workspace_dir: str | None = None,
    model: str | None = None,
) -> AgentRecord:
    spec = await draft_spec_from_prompt(prompt, workspace_dir=workspace_dir, model=model)
    return await create_from_spec(spec)
