import re
from datetime import datetime
from zoneinfo import ZoneInfo

from jarvis.config import settings
from jarvis.services import (
    agent_runtime,
    capabilities,
    cursor_agent,
    event_log,
    executor,
    grounding,
    intent,
    learning,
    memory,
    ollama,
    orchestrator,
    screen_hooks,
    security,
    sessions,
    system_control,
    terminal,
    web,
)

TIME_QUERY = re.compile(r"\b(what time|time is it|current time|what's the time)\b", re.I)
DATE_QUERY = re.compile(r"\b(what day|what date|what's the date|today's date)\b", re.I)
WAKE_ONLY = re.compile(
    r"^(hey\s+)?(willy|willie|william|will|woody|wil)\s*[?.!]*$",
    re.I,
)


def _local_time_reply(text: str, *, voice: bool) -> str | None:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    if TIME_QUERY.search(text):
        spoken = now.strftime("%I:%M %p").lstrip("0")
        return f"{spoken}, boss." if voice else f"{now.strftime('%H:%M')} ({settings.timezone})"
    if DATE_QUERY.search(text):
        spoken = now.strftime("%A, %d %B")
        return f"{spoken}, boss." if voice else spoken
    return None


def _history_messages(history: list[dict]) -> list[dict]:
    return [{"role": h["role"], "content": h["content"]} for h in history if h["role"] in ("user", "assistant")]


def _finish(reply: str, *, voice: bool) -> str:
    return capabilities.trim_reply(reply, voice=voice)


async def _build_system(
    *,
    voice: bool,
    text: str,
    lessons: str,
    conversation_id: str | None = None,
    messaging: bool = False,
) -> str:
    mem = await memory.get_block(text)
    timeline = await event_log.get_timeline_block(limit=5)
    screen_block = ""
    if settings.screen_watch_enabled and not messaging:
        screen_block = await screen_hooks.on_user_prompt(text=text, conversation_id=conversation_id)
    memory_block = "\n\n".join(p for p in (mem, timeline, screen_block) if p)
    conversation = ""
    if conversation_id:
        limit = sessions.VOICE_HISTORY_LIMIT if voice else sessions.HISTORY_LIMIT
        hist = await sessions.get_history(conversation_id, limit=limit)
        conversation = sessions.format_context(hist, limit=10 if voice else 8)
    return capabilities.full_system(
        voice=voice, lessons=lessons, memory=memory_block, conversation=conversation
    )


async def _answer_facts(
    text: str,
    *,
    voice: bool,
    system: str,
    history: list[dict],
    kind: str,
) -> dict:
    facts = await web.research(text)
    confidence = facts.get("confidence", "none")
    fact_text = facts.get("text", "")

    if not fact_text or confidence in ("low", "none"):
        if voice:
            reply = grounding.UNVERIFIED_VOICE
        else:
            reply = grounding.UNVERIFIED_WEB
        return {"reply": reply, "engine": "local", "intent": kind, "web": confidence or "no_results"}

    if confidence == "low" and voice:
        reply = grounding.UNVERIFIED_VOICE
        return {"reply": reply, "engine": "local", "intent": kind, "web": confidence}

    if confidence in ("low", "none") and cursor_agent.should_reason(text) and not voice:
        cloud = await cursor_agent.run_reasoning(text, context=fact_text)
        if cloud.get("ok"):
            reply = grounding.enforce_grounded_reply(
                cloud["result"], voice=voice, had_facts=True, confidence=confidence
            )
            return {
                "reply": _finish(reply, voice=voice),
                "engine": "cursor",
                "intent": kind,
                "web": confidence,
            }

    prompt = grounding.fact_answer_prompt(text, fact_text, voice=voice)
    msgs = _history_messages(history)
    msgs.append({"role": "user", "content": prompt})
    reply = await ollama.chat(system=system, messages=msgs)
    reply = grounding.enforce_grounded_reply(
        reply, voice=voice, had_facts=True, confidence=confidence
    )
    return {
        "reply": _finish(reply, voice=voice),
        "engine": "ollama",
        "intent": kind,
        "web": confidence,
    }


async def _answer_chat(
    text: str,
    *,
    voice: bool,
    system: str,
    history: list[dict],
) -> dict:
    if grounding.needs_grounding(text):
        return await _answer_facts(text, voice=voice, system=system, history=history, kind="fact")

    lowered = text.lower().strip()
    open_ended = (
        "what are we gonna do",
        "what should we do",
        "what do you think",
        "what now",
        "any ideas",
    )
    if any(phrase in lowered for phrase in open_ended):
        reply = "What would you like to tackle first, boss?" if voice else "What would you like to do?"
        return {"reply": reply, "engine": "local", "intent": "chat"}

    msgs = _history_messages(history)
    msgs.append({
        "role": "user",
        "content": (
            f"{text}\n\n"
            "Reply naturally using conversation context. "
            "Do not invent facts, names, or past events not in context."
        ),
    })
    reply = await ollama.chat(system=system, messages=msgs)
    reply = grounding.enforce_grounded_reply(reply, voice=voice, had_facts=False)
    return {"reply": _finish(reply, voice=voice), "engine": "ollama", "intent": "chat"}


async def route(
    text: str,
    *,
    voice: bool = False,
    conversation_id: str | None = None,
    task_id: int | None = None,
    messaging: bool = False,
) -> dict:
    # 1. Execute local macOS / terminal actions first (never hallucinate "opening Spotify").
    local = await executor.try_local_execute(text, voice=voice)
    if local:
        return local

    agent_invocation = await agent_runtime.resolve_invocation(text)
    if agent_invocation:
        agent, task = agent_invocation
        executed = await agent_runtime.execute_agent(
            agent,
            task,
            voice=voice,
            conversation_id=conversation_id,
        )
        if executed.get("ok"):
            return executed
        return {
            "reply": _finish(
                executed.get("error", f"Agent {agent.name} is unavailable right now."),
                voice=voice,
            ),
            "engine": "agent",
            "intent": "agent",
            "agent_name": agent.name,
        }

    kind = intent.classify(text) if voice else await intent.classify_async(text)
    lessons = await learning.get_lessons_block()
    system = await _build_system(
        voice=voice, text=text, lessons=lessons, conversation_id=conversation_id, messaging=messaging
    )

    if WAKE_ONLY.match(text.strip()):
        return {"reply": "Yes, boss?", "engine": "local", "intent": "chat"}

    if kind == "exit":
        if not intent.EXIT_PHRASES.search(text):
            kind = "chat"
        else:
            return {"reply": "Goodbye, boss.", "engine": "local", "end_session": True, "intent": kind}

    if kind == "cancel":
        return {"reply": "Cancelled, boss.", "engine": "local", "intent": kind}

    blocked = None if await security.is_full_access() else capabilities.cannot_do_reply(text, voice=voice)
    if blocked:
        return {"reply": blocked, "engine": "local", "intent": "blocked"}

    if kind == "remember":
        payload = memory.wants_remember(text)
        if payload:
            await memory.store(payload, kind="preference", importance=3, source=conversation_id)
            reply = "Got it, boss. I'll remember that." if voice else f"Remembered: {payload}"
        else:
            reply = "What should I remember, boss?" if voice else "Tell me what to remember."
        return {"reply": reply, "engine": "local", "intent": kind}

    if kind == "recall":
        hits = await memory.retrieve(text, limit=3)
        if hits:
            summary = hits[0]["content"]
            reply = _finish(summary, voice=voice)
        else:
            reply = "I don't have that in memory yet, boss." if voice else "No matching memory found."
        return {"reply": reply, "engine": "memory", "intent": kind}

    if kind == "terminal":
        full_access = await security.is_full_access()
        result = await terminal.execute(text, full_access=full_access, voice=voice)
        if result.get("ok"):
            await event_log.log_integration(
                "terminal",
                source="voice" if voice else "web",
                detail=result.get("command") or text[:200],
                metadata={"stdout_len": len(result.get("stdout") or "")},
            )
            return {
                "reply": _finish(result["reply"], voice=voice),
                "engine": "terminal",
                "intent": kind,
                "command": result.get("command"),
                "stdout": result.get("stdout"),
            }
        if result.get("error") != "not a terminal command":
            return {
                "reply": _finish(result.get("reply", result.get("error", "Cannot run that, boss.")), voice=voice),
                "engine": "terminal",
                "intent": kind,
            }

    if kind == "system":
        result = await system_control.execute(text)
        if result.get("ok"):
            return {
                "reply": _finish(result["reply"], voice=voice),
                "engine": "system",
                "intent": kind,
                "executed": True,
            }
        return {
            "reply": _finish(result.get("reply", "Cannot do that, boss."), voice=voice),
            "engine": "system",
            "intent": kind,
            "executed": False,
        }

    local = _local_time_reply(text, voice=voice)
    if local:
        return {"reply": local, "engine": "local", "intent": "time"}

    history = []
    if conversation_id:
        limit = sessions.VOICE_HISTORY_LIMIT if voice else sessions.HISTORY_LIMIT
        history = await sessions.get_history(conversation_id, limit=limit)

    if kind == "action" and task_id:
        routed = await orchestrator.queue_action(text, task_id=task_id, voice=voice)
        routed["intent"] = kind
        return routed

    if kind == "code" or cursor_agent.should_escalate(text):
        escalated = await cursor_agent.run(f"{system}\n\nTask (be brief):\n{text}")
        if escalated.get("ok"):
            return {
                "reply": _finish(escalated["result"], voice=voice),
                "engine": "cursor",
                "run_id": escalated.get("run_id"),
                "intent": kind,
            }
        if "CURSOR_API_KEY" in escalated.get("error", ""):
            return await _answer_chat(text, voice=voice, system=system, history=history)

    if kind in ("fact", "reason") or grounding.needs_grounding(text):
        # Reasoning / planning → Cursor when configured, else web + Ollama.
        if cursor_agent.should_reason(text) and settings.cursor_configured():
            cloud = await cursor_agent.run_reasoning(text)
            if cloud.get("ok"):
                return {
                    "reply": _finish(cloud["result"], voice=voice),
                    "engine": "cursor",
                    "intent": kind,
                    "executed": False,
                    "run_id": cloud.get("run_id"),
                }
        return await _answer_facts(text, voice=voice, system=system, history=history, kind=kind)

    return await _answer_chat(text, voice=voice, system=system, history=history)
