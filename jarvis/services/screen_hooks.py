"""William-native lifecycle hooks for screen context (Claude Code hook patterns)."""

from __future__ import annotations

import logging

from jarvis.services import screen_observer, sessions

log = logging.getLogger("jarvis.screen_hooks")


async def on_session_start(*, conversation_id: str | None = None, query: str | None = None) -> str:
    """SessionStart — inject compact screen index."""
    return await screen_observer.get_recent_context(minutes=30, query=query)


async def on_user_prompt(*, text: str, conversation_id: str | None = None) -> str:
    """UserPromptSubmit — relevance-gated screen context."""
    return await screen_observer.get_recent_context(minutes=30, query=text)


async def on_pre_compact() -> dict:
    """PreCompact — snapshot screen state before memory compression."""
    summary = await screen_observer.build_window_summary()
    return {"ok": True, "snapshot": summary}


async def on_session_end(*, conversation_id: str | None, messages: list[dict]) -> dict:
    """SessionEnd — extract session + rate usefulness."""
    from jarvis.services import notion_sync

    result: dict = {"ok": True}
    if notion_sync.configured() and len(messages) >= 2:
        screen_block = await screen_observer.get_activity_index(minutes=60, limit=6)
        alignment = f"Screen log:\n{screen_block}" if screen_block else None
        notion_result = await notion_sync.sync_session_summary(
            conversation_id=conversation_id or "unknown",
            source="chat",
            messages=messages,
            alignment_notes=alignment,
        )
        result["notion"] = notion_result

    recent_ids: list[int] = []
    index = await screen_observer.get_activity_index(minutes=30, limit=5)
    if index:
        import re

        recent_ids = [int(m) for m in re.findall(r"#(\d+)", index)][:5]
    useful = len(messages) > 2
    await screen_observer.rate_context_usefulness(
        session_id=conversation_id,
        summary_ids=recent_ids,
        was_useful=useful,
    )
    return result


def is_ambiguous_query(text: str) -> bool:
    import re

    return bool(
        re.search(
            r"\b(this|that|it|where i left off|what was i doing|continue where|why is this failing)\b",
            text,
            re.I,
        )
    )
