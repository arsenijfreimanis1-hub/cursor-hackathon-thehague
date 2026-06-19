from jarvis.services import approvals, router, tasks

SENSITIVE_KEYWORDS = ("delete", "deploy", "purchase", "api key", "credential")


async def handle_message(text: str, source: str = "web") -> dict:
    task = await tasks.create_task(title=text[:120], body=text, source=source)

    lowered = text.lower()
    if any(kw in lowered for kw in SENSITIVE_KEYWORDS):
        approval = await approvals.request_approval(
            action="sensitive_action",
            detail=text,
        )
        await tasks.update_task_status(task["id"], "awaiting_approval")
        return {
            "reply": "That looks sensitive — I've queued it for your approval in the inbox.",
            "task_id": task["id"],
            "approval_id": approval["id"],
            "engine": "blocked",
        }

    try:
        routed = await router.route(text)
        await tasks.update_task_status(task["id"], "done")
        return {
            "reply": routed["reply"],
            "task_id": task["id"],
            "engine": routed.get("engine", "ollama"),
            "run_id": routed.get("run_id"),
            "escalation": routed.get("escalation"),
        }
    except Exception as exc:
        await tasks.update_task_status(task["id"], "error")
        return {
            "reply": f"Agent unavailable: {exc}",
            "task_id": task["id"],
            "error": str(exc),
            "engine": "error",
        }
