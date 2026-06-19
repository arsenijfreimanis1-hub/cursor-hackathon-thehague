from jarvis.services import cursor_agent, ollama

LOCAL_SYSTEM = """You are William Agent, Willy's local-first assistant on a Mac mini.
Be concise and practical. Prefer local reasoning for simple questions."""


async def route(text: str) -> dict:
    if cursor_agent.should_escalate(text):
        escalated = await cursor_agent.run(
            f"You are William Agent helping Willy on his Mac mini. Task:\n{text}"
        )
        if escalated.get("ok"):
            return {
                "reply": escalated["result"],
                "engine": "cursor",
                "run_id": escalated.get("run_id"),
            }
        if "CURSOR_API_KEY" in escalated.get("error", ""):
            local = await ollama.chat(
                text + "\n\n(Note: this looks complex — set CURSOR_API_KEY to escalate to Cursor.)",
                system=LOCAL_SYSTEM,
            )
            return {"reply": local, "engine": "ollama", "escalation": "unavailable"}
        local = await ollama.chat(text, system=LOCAL_SYSTEM)
        return {
            "reply": local,
            "engine": "ollama",
            "escalation_error": escalated.get("error"),
        }

    reply = await ollama.chat(text, system=LOCAL_SYSTEM)
    return {"reply": reply, "engine": "ollama"}
