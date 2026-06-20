"""Goal-approved autonomous loop — self-prompt after batch completion."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from jarvis.services import approvals, goals, macos, ollama, tasks, worker
from jarvis.services.planner import SENSITIVE_KEYWORDS

log = logging.getLogger("jarvis.goal_runner")

MAX_ITERATIONS = 10
MAX_WALL_SECONDS = 30 * 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _wall_elapsed_seconds(goal: dict) -> float:
    started = goal.get("started_at")
    if not started:
        return 0.0
    try:
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - start).total_seconds()
    except ValueError:
        return 0.0


def _needs_approval(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in SENSITIVE_KEYWORDS)


async def _notify_goal(title: str, message: str, *, speak: bool = False) -> None:
    await macos.notify(title, message, speak=speak)
    if speak:
        await macos.speak_when_clear(message)


async def approve_goal(goal_id: int) -> dict:
    goal = await goals.get_goal(goal_id)
    if not goal:
        return {"ok": False, "error": "goal not found"}
    if goal["status"] != goals.GOAL_STATUS_AWAITING:
        return {"ok": False, "error": f"goal status is {goal['status']}, expected awaiting_approval"}

    await goals.update_goal_status(
        goal_id,
        goals.GOAL_STATUS_RUNNING,
        started_at=_now_iso(),
    )
    goal_tasks = await goals.list_goal_tasks(goal_id)
    parent = next((t for t in goal_tasks if not t.get("parent_id")), None)
    if parent:
        await tasks.update_task_status(parent["id"], "running")

    await _queue_next_child(goal_id)
    detail = await goals.get_goal_detail(goal_id)
    return {"ok": True, **(detail or {})}


async def _queue_next_child(goal_id: int) -> bool:
    goal_tasks = await goals.list_goal_tasks(goal_id)
    children = [t for t in goal_tasks if t.get("parent_id")]
    in_flight = [c for c in children if c["status"] in ("queued", "running")]
    if in_flight:
        return False
    pending = sorted(
        [c for c in children if c["status"] == "pending"],
        key=lambda t: (t.get("priority", 50), t["id"]),
    )
    if not pending:
        return False
    await tasks.update_task_status(pending[0]["id"], "queued")
    worker.notify()
    return True


async def _self_prompt(goal: dict) -> dict:
    goal_tasks = await goals.list_goal_tasks(goal["id"])
    children = [t for t in goal_tasks if t.get("parent_id")]
    summary_lines = [
        f"- [{t['status']}] {t.get('title', t.get('body', ''))[:120]}"
        for t in children[-12:]
    ]
    prompt = (
        f'Goal: "{goal["prompt"][:400]}"\n\n'
        f"Completed subtasks:\n" + "\n".join(summary_lines) + "\n\n"
        "What's the next step toward completing this goal?\n"
        'Reply ONLY with JSON: {"done": bool, "next_tasks": ["task1", ...]}\n'
        "Set done=true only when the goal is fully achieved. Max 4 next_tasks."
    )
    raw = await ollama.chat(
        prompt,
        system=(
            "You are William Agent's goal planner. Assess progress and propose next steps. "
            "JSON only, no markdown."
        ),
    )
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {"done": False, "next_tasks": [], "parse_error": True}
    try:
        parsed = json.loads(raw[start:end])
    except json.JSONDecodeError:
        return {"done": False, "next_tasks": [], "parse_error": True}
    next_tasks = parsed.get("next_tasks") or []
    if not isinstance(next_tasks, list):
        next_tasks = []
    cleaned = [str(t).strip() for t in next_tasks if str(t).strip()][:4]
    return {"done": bool(parsed.get("done")), "next_tasks": cleaned}


async def _append_tasks(goal: dict, parts: list[str]) -> list[int]:
    goal_tasks = await goals.list_goal_tasks(goal["id"])
    parent = next((t for t in goal_tasks if not t.get("parent_id")), None)
    if not parent:
        return []
    batch_id = goal.get("batch_id") or parent.get("batch_id")
    from jarvis.services import task_priority

    ids: list[int] = []
    for part in parts:
        if _needs_approval(part):
            prio, _ = task_priority.estimate_priority(part)
            child = await tasks.create_task(
                title=part[:120],
                body=part,
                source=goal.get("source", "goal"),
                status="awaiting_approval",
                parent_id=parent["id"],
                batch_id=batch_id,
                priority=prio,
                goal_id=goal["id"],
            )
            await approvals.request_approval(
                "sensitive_action",
                part[:500],
            )
            await goals.update_goal_status(
                goal["id"],
                goals.GOAL_STATUS_BLOCKED,
                error=f"approval required: {part[:120]}",
            )
            await _notify_goal(
                "William Agent",
                f"Goal paused — approval needed for: {part[:80]}",
                speak=False,
            )
            ids.append(child["id"])
            return ids
        prio, _ = task_priority.estimate_priority(part)
        child = await tasks.create_task(
            title=part[:120],
            body=part,
            source=goal.get("source", "goal"),
            status="pending",
            parent_id=parent["id"],
            batch_id=batch_id,
            priority=prio,
            goal_id=goal["id"],
        )
        ids.append(child["id"])
    return ids


async def on_task_done(task: dict) -> None:
    goal_id = task.get("goal_id")
    if not goal_id:
        return

    goal = await goals.get_goal(goal_id)
    if not goal or goal["status"] != goals.GOAL_STATUS_RUNNING:
        return

    await _queue_next_child(goal_id)

    goal_tasks = await goals.list_goal_tasks(goal_id)
    children = [t for t in goal_tasks if t.get("parent_id")]
    if not children:
        return

    if any(c["status"] in ("queued", "running", "pending") for c in children):
        return

    if not all(c["status"] in ("done", "failed") for c in children):
        return

    if goal["iteration_count"] >= MAX_ITERATIONS:
        await goals.update_goal_status(
            goal_id,
            goals.GOAL_STATUS_PAUSED,
            error="max self-prompt iterations (10)",
        )
        await _notify_goal("William Agent", f"Goal paused: max iterations reached.", speak=True)
        return

    if _wall_elapsed_seconds(goal) >= MAX_WALL_SECONDS:
        await goals.update_goal_status(
            goal_id,
            goals.GOAL_STATUS_PAUSED,
            error="max wall time (30 min)",
        )
        await _notify_goal("William Agent", "Goal paused: 30 minute time cap reached.", speak=True)
        return

    await goals.increment_iteration(goal_id)
    goal = await goals.get_goal(goal_id)
    assert goal is not None

    result = await _self_prompt(goal)
    if result.get("done"):
        await goals.update_goal_status(goal_id, goals.GOAL_STATUS_COMPLETE, completed_at=_now_iso())
        parent = next((t for t in goal_tasks if not t.get("parent_id")), None)
        if parent:
            failed = sum(1 for c in children if c["status"] == "failed")
            status = "failed" if failed == len(children) else "done"
            await tasks.update_task_status(parent["id"], status)
        await _notify_goal("William Agent", "Goal complete, boss.", speak=True)
        return

    next_tasks = result.get("next_tasks") or []
    if not next_tasks:
        await goals.update_goal_status(
            goal_id,
            goals.GOAL_STATUS_BLOCKED,
            error="self-prompt returned no next tasks",
        )
        await _notify_goal("William Agent", "Goal blocked — no next steps from planner.", speak=True)
        return

    new_ids = await _append_tasks(goal, next_tasks)
    if not new_ids:
        await goals.update_goal_status(
            goal_id,
            goals.GOAL_STATUS_BLOCKED,
            error="next tasks require approval",
        )
        return

    await _queue_next_child(goal_id)


async def create_goal(prompt: str, *, source: str = "web") -> dict:
    """Create a goal with split subtasks pending approval."""
    detail = await goals.create_goal_from_prompt(prompt, source=source)
    return {"ok": True, **detail}
