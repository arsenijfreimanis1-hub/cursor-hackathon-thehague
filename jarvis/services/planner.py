import re
import uuid

from jarvis.services import approvals, event_log, goal_runner, learning, memory, notion_sync, router, security, sessions, task_priority, task_splitter, tasks, worker

SENSITIVE_KEYWORDS = ("delete", "deploy", "purchase", "api key", "credential")
GOAL_PREFIX = re.compile(r"^(?:goal|autonomous goal):\s*", re.I)
VOICE_COMMAND_HINTS = (
    "play", "open", "weather", "spotify", "remember", "what", "who", "how",
    "time", "pause", "stop", "skip", "close", "search", "tell", "check",
    "music", "volume", "youtube", "launch", "focus", "goodbye", "thanks",
)


def _looks_like_voice_noise(text: str) -> bool:
    words = text.split()
    if len(words) <= 18:
        return False
    lowered = text.lower()
    return not any(hint in lowered for hint in VOICE_COMMAND_HINTS)


async def _queue_batch(
    text: str,
    subtasks: list[str],
    *,
    source: str,
    voice: bool,
    conversation_id: str,
    speaker_verified: bool = True,
) -> dict:
    if not speaker_verified:
        reply = "I don't recognize your voice, boss. Say enroll my voice to set that up."
        await sessions.add_message(conversation_id, "assistant", reply, engine="blocked")
        return {
            "reply": reply,
            "engine": "blocked",
            "session_id": conversation_id,
            "intent": "blocked",
        }

    ordered = task_priority.sort_by_speed(subtasks)
    batch_id = uuid.uuid4().hex[:10]
    parent = await tasks.create_task(
        title=f"Plan: {text[:90]}",
        body=text,
        source=source,
        status="running",
        batch_id=batch_id,
        priority=0,
    )
    child_ids: list[int] = []
    fast_notes: list[str] = []
    queued_count = 0

    for part in ordered:
        prio, _ = task_priority.estimate_priority(part)
        child = await tasks.create_task(
            title=part[:120],
            body=part,
            source=source,
            status="running",
            parent_id=parent["id"],
            batch_id=batch_id,
            priority=prio,
        )
        child_ids.append(child["id"])
        routed = await router.route(
            part,
            voice=voice,
            conversation_id=conversation_id,
            task_id=child["id"],
        )
        if routed.get("deferred"):
            await tasks.update_task_status(child["id"], "queued")
            queued_count += 1
        else:
            await tasks.update_task_status(child["id"], "done")
            fast_notes.append(routed.get("reply", "Done."))

    if queued_count:
        worker.notify()

    deferred = queued_count > 0
    plan_line = task_priority.plan_summary(ordered, voice=voice)
    if voice:
        if fast_notes and deferred:
            reply = f"{plan_line} On it for the rest, boss."
        elif fast_notes:
            reply = plan_line or fast_notes[0]
        elif deferred:
            reply = f"{plan_line} Queued {len(deferred)} background tasks, boss."
        else:
            reply = f"Split into {len(ordered)} tasks, boss."
    else:
        lines = "\n".join(f"{i + 1}. {part}" for i, part in enumerate(ordered))
        reply = f"Plan ({len(ordered)} tasks, fastest first):\n{lines}"
        if fast_notes:
            reply += f"\n\nDone immediately:\n" + "\n".join(f"- {n}" for n in fast_notes)
        if deferred:
            reply += f"\n\nQueued in background: {len(deferred)} task(s)"

    await sessions.add_message(conversation_id, "assistant", reply, engine="batch")
    return {
        "reply": reply,
        "task_id": parent["id"],
        "task_ids": child_ids,
        "subtasks": ordered,
        "batch_id": batch_id,
        "engine": "batch",
        "deferred": bool(deferred),
        "session_id": conversation_id,
        "intent": "action",
    }


async def handle_message(
    text: str,
    source: str = "web",
    *,
    session_id: str | None = None,
    speaker_verified: bool | None = None,
    speaker_confidence: float | None = None,
) -> dict:
    voice = source == "voice"
    conversation_id, is_new_session = await sessions.get_or_create(session_id, source=source, message=text)
    await sessions.add_message(conversation_id, "user", text)

    verified = True if speaker_verified is None else speaker_verified
    if voice and speaker_verified is False:
        reply = "I don't recognize your voice, boss. Say enroll my voice to teach me."
        await sessions.add_message(conversation_id, "assistant", reply, engine="blocked")
        await event_log.log_interaction(
            source=source,
            user_message=text,
            assistant_reply=reply,
            intent="blocked",
            engine="voice_auth",
            conversation_id=conversation_id,
            metadata={"speaker_confidence": speaker_confidence},
        )
        return {
            "reply": reply,
            "engine": "blocked",
            "session_id": conversation_id,
            "intent": "blocked",
        }

    if voice and _looks_like_voice_noise(text):
        reply = "I didn't catch a command there, boss. Say hey Willie again?"
        await sessions.add_message(conversation_id, "assistant", reply, engine="ignored")
        await event_log.log_interaction(
            source=source,
            user_message=text,
            assistant_reply=reply,
            intent="ignored",
            engine="ignored",
            conversation_id=conversation_id,
        )
        return {
            "reply": reply,
            "engine": "ignored",
            "session_id": conversation_id,
            "intent": "ignored",
        }

    goal_match = GOAL_PREFIX.match(text.strip())
    if goal_match:
        prompt = GOAL_PREFIX.sub("", text.strip()).strip()
        if prompt:
            created = await goal_runner.create_goal(prompt, source=source)
            subtasks = created.get("subtasks") or []
            if voice:
                reply = (
                    f"I've drafted a {len(subtasks)}-step plan for approval, boss. "
                    "Open the kiosk to review and approve it."
                )
            else:
                lines = "\n".join(f"{i + 1}. {part}" for i, part in enumerate(subtasks))
                reply = f"Goal #{created['id']} awaiting approval ({len(subtasks)} steps):\n{lines}"
            await sessions.add_message(conversation_id, "assistant", reply, engine="goal")
            await event_log.log_interaction(
                source=source,
                user_message=text,
                assistant_reply=reply,
                intent="goal",
                engine="goal",
                conversation_id=conversation_id,
                metadata={"goal_id": created.get("id"), "subtasks": len(subtasks)},
            )
            return {
                "reply": reply,
                "goal_id": created.get("id"),
                "subtasks": subtasks,
                "engine": "goal",
                "session_id": conversation_id,
                "intent": "goal",
            }

    lowered = text.lower()
    if not await security.is_full_access() and any(kw in lowered for kw in SENSITIVE_KEYWORDS):
        task = await tasks.create_task(title=text[:120], body=text, source=source)
        approval = await approvals.request_approval(
            action="sensitive_action",
            detail=text,
        )
        await tasks.update_task_status(task["id"], "awaiting_approval")
        reply = (
            "That looks sensitive, boss. I've queued it for your approval."
            if voice
            else "That looks sensitive — I've queued it for your approval in the inbox."
        )
        await sessions.add_message(conversation_id, "assistant", reply, engine="blocked")
        await event_log.log_interaction(
            source=source,
            user_message=text,
            assistant_reply=reply,
            intent="blocked",
            task_id=task["id"],
            task_status="awaiting_approval",
            engine="blocked",
            conversation_id=conversation_id,
        )
        return {
            "reply": reply,
            "task_id": task["id"],
            "approval_id": approval["id"],
            "engine": "blocked",
            "session_id": conversation_id,
        }

    try:
        subtasks = [text]
        if not voice or len(text) > 80 or task_splitter.looks_compound(text):
            subtasks = await task_splitter.split_prompt(text)
        if len(subtasks) > 1:
            result = await _queue_batch(
                text,
                subtasks,
                source=source,
                voice=voice,
                conversation_id=conversation_id,
                speaker_verified=verified,
            )
            await learning.observe_turn(text, result)
            await event_log.log_interaction(
                source=source,
                user_message=text,
                assistant_reply=result["reply"],
                intent="action",
                task_id=result.get("task_id"),
                task_status="running",
                engine="batch",
                conversation_id=conversation_id,
                metadata={"batch_id": result.get("batch_id"), "subtasks": len(subtasks)},
            )
            return result

        task = await tasks.create_task(title=text[:120], body=text, source=source)
        routed = await router.route(
            text,
            voice=voice,
            conversation_id=conversation_id,
            task_id=task["id"],
        )

        if routed.get("deferred"):
            await tasks.update_task_status(task["id"], "queued")
            worker.notify()
        elif routed.get("end_session"):
            await tasks.update_task_status(task["id"], "done")
        else:
            await tasks.update_task_status(task["id"], "done")

        task_status = "queued" if routed.get("deferred") else "done"
        logged = await event_log.log_interaction(
            source=source,
            user_message=text,
            assistant_reply=routed["reply"],
            intent=routed.get("intent"),
            task_id=task["id"],
            task_status=task_status,
            engine=routed.get("engine"),
            conversation_id=conversation_id,
            metadata={
                "run_id": routed.get("run_id"),
                "command": routed.get("command"),
                "agent_name": routed.get("agent_name"),
                "agent_version": routed.get("agent_version"),
            },
        )

        if routed.get("engine") == "cursor":
            await event_log.log_integration(
                "cursor_escalation",
                source=source,
                detail=text[:200],
                task_id=task["id"],
                metadata={"run_id": routed.get("run_id")},
            )

        await sessions.add_message(
            conversation_id,
            "assistant",
            routed["reply"],
            engine=routed.get("engine"),
        )
        await learning.observe_turn(text, routed)

        if logged.get("alignment_score", 1) < 0.4:
            await learning.record_struggle(
                user_message=text,
                failure_kind="misaligned",
                intent=routed.get("intent"),
                engine=routed.get("engine"),
                detail=logged.get("alignment_notes"),
            )

        remember_payload = memory.wants_remember(text)
        if remember_payload and routed.get("intent") != "remember":
            await memory.store(remember_payload, kind="preference", importance=3, source=conversation_id)

        return {
            "reply": routed["reply"],
            "task_id": task["id"],
            "engine": routed.get("engine", "ollama"),
            "run_id": routed.get("run_id"),
            "escalation": routed.get("escalation"),
            "session_id": conversation_id,
            "is_new_session": is_new_session,
            "executed": routed.get("executed", False),
            "deferred": routed.get("deferred", False),
            "end_session": routed.get("end_session", False),
            "intent": routed.get("intent"),
            "command": routed.get("command"),
            "stdout": routed.get("stdout"),
            "agent_name": routed.get("agent_name"),
            "agent_version": routed.get("agent_version"),
        }
    except Exception as exc:
        if "task" in locals():
            await tasks.update_task_status(task["id"], "failed")
        reply = "Trouble right now, boss." if voice else f"Agent unavailable: {exc}"
        await sessions.add_message(conversation_id, "assistant", reply, engine="error")
        await event_log.log_interaction(
            source=source,
            user_message=text,
            assistant_reply=reply,
            intent="unknown",
            task_id=locals().get("task", {}).get("id") if "task" in locals() else None,
            task_status="failed",
            engine="error",
            conversation_id=conversation_id,
            metadata={"error": str(exc)},
        )
        await learning.observe_turn(
            text,
            {"reply": reply, "engine": "error", "intent": "unknown"},
            error=str(exc),
        )
        return {
            "reply": reply,
            "task_id": locals().get("task", {}).get("id") if "task" in locals() else None,
            "error": str(exc),
            "engine": "error",
            "session_id": conversation_id,
        }
