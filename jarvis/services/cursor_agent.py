import asyncio
import json
import logging
import os

from cursor_sdk import Agent, AgentOptions, CloudAgentOptions, CloudRepository, CursorAgentError, LocalAgentOptions

from jarvis.config import settings
from jarvis.services import mcp_config, skill_domains, skills

log = logging.getLogger("jarvis.cursor_agent")

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

REASON_HINTS = (
    "why",
    "how does",
    "explain",
    "compare",
    "pros and cons",
    "should i",
    "recommend",
    "plan",
    "strategy",
    "think through",
    "reason about",
)

CURSOR_RULES = """You are the cloud reasoning tier for William Agent, Willy's Mac mini assistant.
Rules:
- Address Willy as "boss".
- For voice output: ONE short sentence, max 15 words, no markdown, no lists, no humor.
- Be factual. Use only provided context; never invent.
- For code tasks: implement fully, then summarize what you did in one sentence.
- Do not restate the question. Do not add filler."""


def should_escalate(text: str) -> bool:
    lowered = text.lower()
    if len(text) > 600:
        return True
    return any(hint in lowered for hint in COMPLEX_HINTS)


def should_reason(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in REASON_HINTS) or len(text) > 200


def _agent_options(
    *,
    api_key: str,
    model: str,
    cwd: str | None = None,
    repo_url: str | None = None,
    branch: str | None = None,
    runtime: str = "local",
) -> AgentOptions:
    mcp_servers = mcp_config.load_mcp_servers()
    if runtime == "cloud" and repo_url:
        opts = AgentOptions(
            api_key=api_key,
            model=model,
            cloud=CloudAgentOptions(
                repos=[CloudRepository(url=repo_url, starting_ref=branch or "main")],
                auto_create_pr=False,
                work_on_current_branch=True,
            ),
        )
        if mcp_servers:
            return AgentOptions(api_key=api_key, model=model, cloud=opts.cloud, mcp_servers=mcp_servers)
        return opts
    local_opts = LocalAgentOptions(
        cwd=cwd or str(settings.workspace_dir),
        setting_sources=["project", "user"],
    )
    if mcp_servers:
        return AgentOptions(api_key=api_key, model=model, local=local_opts, mcp_servers=mcp_servers)
    return AgentOptions(api_key=api_key, model=model, local=local_opts)


def _cursor_prompt(
    prompt: str,
    api_key: str,
    model: str,
    *,
    cwd: str | None = None,
    repo_url: str | None = None,
    branch: str | None = None,
    runtime: str = "local",
) -> dict:
    try:
        result = Agent.prompt(
            prompt,
            _agent_options(
                api_key=api_key,
                model=model,
                cwd=cwd,
                repo_url=repo_url,
                branch=branch,
                runtime=runtime,
            ),
        )
        return {
            "ok": result.status != "error",
            "status": result.status,
            "result": result.result or "",
            "run_id": getattr(result, "id", None),
            "runtime": runtime,
        }
    except CursorAgentError as exc:
        return {"ok": False, "error": str(exc), "retryable": exc.is_retryable, "runtime": runtime}


def _cursor_run_traced(
    prompt: str,
    api_key: str,
    model: str,
    *,
    cwd: str | None = None,
    repo_url: str | None = None,
    branch: str | None = None,
    runtime: str = "local",
) -> dict:
    """Run via Agent.create and collect thinking + assistant + tool messages."""
    from jarvis.services import cursor_trace

    events: list[tuple[int, dict]] = []
    agent_id: str | None = None
    try:
        with Agent.create(
            _agent_options(
                api_key=api_key,
                model=model,
                cwd=cwd,
                repo_url=repo_url,
                branch=branch,
                runtime=runtime,
            ),
        ) as agent:
            agent_id = getattr(agent, "id", None) or getattr(agent, "agent_id", None)
            run = agent.send(prompt)
            seq = 0
            for msg in run.messages():
                events.append((seq, cursor_trace.message_to_entry(msg)))
                seq += 1
            terminal = run.wait()
            return {
                "ok": terminal.status != "error",
                "status": terminal.status,
                "result": terminal.result or "",
                "run_id": terminal.id,
                "agent_id": agent_id,
                "events": events,
                "runtime": runtime,
            }
    except CursorAgentError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "retryable": exc.is_retryable,
            "events": events,
            "agent_id": agent_id,
        }


async def _persist_trace(
    *,
    prompt: str,
    source: str,
    result: dict,
) -> int | None:
    if not settings.cursor_trace_enabled:
        return None
    from jarvis.services import cursor_trace

    db_id = await cursor_trace.start_run(
        prompt=prompt,
        source=source,
        run_id=result.get("run_id"),
        agent_id=result.get("agent_id"),
    )
    for seq, entry in result.get("events") or []:
        await cursor_trace.append_event(db_id, seq, entry)
    await cursor_trace.finish_run(
        db_id,
        run_id=result.get("run_id"),
        agent_id=result.get("agent_id"),
        status=result.get("status"),
        result=result.get("result"),
    )
    result["trace_db_id"] = db_id
    return db_id


async def _screen_context_block(query: str | None = None) -> str:
    if not settings.screen_watch_enabled:
        return ""
    from jarvis.services import screen_observer

    block = await screen_observer.get_recent_context(minutes=30, query=query)
    return f"\n\nSCREEN CONTEXT:\n{block}" if block else ""


async def _build_full_prompt(
    prompt: str,
    *,
    domains: list[skill_domains.SkillDomain] | None = None,
) -> str:
    detected = list(domains or skill_domains.detect_domains(prompt))
    if "cursor" not in detected:
        detected.append("cursor")
    skill_block = skills.load_skills_block(
        domains=detected,
        include_external=False,
    )
    screen_block = await _screen_context_block(prompt)
    full_prompt = CURSOR_RULES
    if skill_block:
        full_prompt += f"\n\n{skill_block}"
    if screen_block:
        full_prompt += screen_block
    full_prompt += f"\n\n{prompt}"
    return full_prompt


async def run(
    prompt: str,
    *,
    cwd: str | None = None,
    model: str | None = None,
    source: str = "cursor_agent",
    handle_popups: bool = True,
    trace: bool | None = None,
    runtime: str | None = None,
    repo_url: str | None = None,
    branch: str | None = None,
    domains: list[skill_domains.SkillDomain] | None = None,
) -> dict:
    api_key = settings.resolved_cursor_api_key()
    if not api_key:
        return {
            "ok": False,
            "error": "CURSOR_API_KEY not set — add to ~/.jarvis-core/.env or export it",
        }
    workdir = cwd or str(settings.workspace_dir)
    rt = (runtime or "local").lower()
    if rt == "cloud" and not repo_url:
        return {"ok": False, "error": "cloud runtime requires repo_url"}
    full_prompt = await _build_full_prompt(prompt, domains=domains)
    use_trace = settings.cursor_trace_enabled if trace is None else trace
    use_popups = handle_popups and settings.popup_handler_enabled and rt == "local"

    popup_note = ""
    pre: dict = {"ok": True, "handled": False}
    if use_popups:
        from jarvis.services import popup_handler

        pre = await popup_handler.handle_popups(full_control=True)
        if pre.get("handled"):
            titles = [a.get("title") for a in pre.get("actions", []) if a.get("title")]
            popup_note = f"\n\nSYSTEM: A dialog was dismissed before your run ({', '.join(titles) or 'popup'}). Continue."

    runner = _cursor_run_traced if use_trace else _cursor_prompt
    run_kwargs = {
        "cwd": workdir,
        "repo_url": repo_url,
        "branch": branch,
        "runtime": rt,
    }
    result = await asyncio.to_thread(
        runner,
        full_prompt + popup_note,
        api_key,
        model or settings.cursor_model,
        **run_kwargs,
    )

    if use_trace:
        await _persist_trace(prompt=prompt, source=source, result=result)

    if use_popups:
        from jarvis.services import popup_handler

        post = await popup_handler.handle_popups(full_control=True)
        result["popup_before"] = pre
        result["popup_after"] = post
        if post.get("needs_reprompt") and result.get("ok"):
            reprompt = (
                "A system dialog appeared during your run and was dismissed. "
                "Verify your changes applied and continue if needed."
            )
            followup = await asyncio.to_thread(
                _cursor_run_traced if use_trace else _cursor_prompt,
                await _build_full_prompt(reprompt),
                api_key,
                model or settings.cursor_model,
                **run_kwargs,
            )
            if use_trace:
                await _persist_trace(prompt=reprompt, source=f"{source}_reprompt", result=followup)
            if followup.get("ok") and followup.get("result"):
                result["result"] = (result.get("result") or "") + "\n" + followup["result"]
            result["reprompt"] = followup

    return result


async def run_reasoning(text: str, *, context: str = "") -> dict:
    """Short voice/web answers — prefer Vigil Anthropic proxy when configured."""
    from jarvis.services import vigil_proxy

    prompt = f"Question: {text}\n"
    if context:
        prompt += f"\nGrounding context:\n{context}\n"
    prompt += "\nAnswer in one short sentence for voice."

    if vigil_proxy.configured():
        try:
            reply = await vigil_proxy.chat(
                system=CURSOR_RULES,
                prompt=prompt,
            )
            return {"ok": True, "result": reply, "engine": "vigil-anthropic"}
        except Exception as exc:
            log.warning("vigil reasoning failed, falling back to cursor: %s", exc)

    return await run(prompt, handle_popups=False)


async def plan_tasks(text: str) -> list[str]:
    """Use Cursor (Claude-tier) to split a compound request into imperative subtasks."""
    prompt = (
        f'User request: "{text[:500]}"\n\n'
        "Split into 2-5 independent imperative tasks ordered by execution speed "
        "(local actions like open app / play music first, heavy code last).\n"
        'Reply ONLY with a JSON array of strings, e.g. ["open Spotify","play liked songs"].'
    )
    result = await run(
        prompt,
        cwd=str(settings.workspace_dir),
        handle_popups=False,
        trace=False,
    )
    if not result.get("ok"):
        return []
    raw = result.get("result", "")
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start < 0 or end <= start:
        return []
    try:
        parsed = json.loads(raw[start:end])
        items = [str(x).strip() for x in parsed if str(x).strip()]
        return items[:6] if len(items) >= 2 else []
    except json.JSONDecodeError:
        return []
