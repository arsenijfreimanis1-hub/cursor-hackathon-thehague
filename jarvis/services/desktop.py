from jarvis.services import approvals, macos, ollama

VISION_PROMPT = """Describe what is on this Mac screen in 2-3 sentences.
Then suggest ONE concrete UI action William Agent could take (e.g. "click the Safari icon").
Format:
DESCRIPTION: ...
ACTION: ..."""


async def analyze_screen() -> dict:
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
