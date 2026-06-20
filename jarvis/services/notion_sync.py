"""Optional Notion export: session summaries, task outcomes, screenshots."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import httpx

from jarvis.config import settings

log = logging.getLogger("jarvis.notion")

NOTION_VERSION = "2022-06-28"


def configured() -> bool:
    return settings.notion_configured()


def _api_key() -> str:
    return settings.resolved_notion_api_key()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, *, json: dict | None = None) -> dict:
    if not configured():
        return {"ok": False, "error": "notion not configured"}
    url = f"https://api.notion.com/v1{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request(method, url, headers=_headers(), json=json)
            if resp.status_code >= 400:
                return {"ok": False, "error": resp.text, "status": resp.status_code}
            return {"ok": True, **resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def _rich(text: str) -> list[dict]:
    chunks = [text[i : i + 1800] for i in range(0, max(len(text), 1), 1800)] or [""]
    return [{"type": "text", "text": {"content": c}} for c in chunks]


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich(text)}}


def _heading(text: str, level: int = 2) -> dict:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich(text)}}


async def create_learning_page(
    *,
    title: str,
    body: str,
    tags: list[str] | None = None,
) -> dict:
    """Create a child page under the configured parent."""
    if not configured():
        return {"ok": False, "error": "set JARVIS_NOTION_API_KEY and JARVIS_NOTION_PARENT_PAGE_ID"}

    children = [_heading(title, 2), _paragraph(body)]
    if tags:
        children.append(_paragraph(f"Tags: {', '.join(tags)}"))

    payload = {
        "parent": {"page_id": settings.notion_parent_page_id},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title[:100]}}]},
        },
        "children": children,
    }
    result = await _request("POST", "/pages", json=payload)
    if result.get("ok"):
        return {"ok": True, "page_id": result.get("id"), "url": result.get("url")}
    return result


async def sync_session_summary(
    *,
    conversation_id: str,
    source: str,
    messages: list[dict],
    alignment_notes: str | None = None,
) -> dict:
    if not configured() or len(messages) < 2:
        return {"ok": False, "skipped": True}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"William session {source} · {now}"
    lines = [f"Session `{conversation_id[:8]}` · source: {source}", ""]
    for msg in messages[-12:]:
        role = msg.get("role", "?")
        eng = msg.get("engine") or ""
        content = (msg.get("content") or "")[:400]
        lines.append(f"**{role}**{f' ({eng})' if eng else ''}: {content}")
    if alignment_notes:
        lines.extend(["", f"Alignment notes: {alignment_notes}"])
    return await create_learning_page(title=title, body="\n".join(lines), tags=[source, "session"])


async def sync_task_outcome(
    *,
    task_id: int,
    title: str,
    body: str,
    status: str,
    alignment_score: float | None = None,
    alignment_notes: str | None = None,
    screenshot_path: str | None = None,
) -> dict:
    if not configured():
        return {"ok": False, "skipped": True}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    page_title = f"Task #{task_id} {status} · {now}"
    text = (
        f"**{title}**\n\n{body}\n\n"
        f"Status: {status}\n"
        f"Alignment: {alignment_score if alignment_score is not None else 'n/a'}"
    )
    if alignment_notes:
        text += f"\nNotes: {alignment_notes}"

    result = await create_learning_page(title=page_title, body=text, tags=["task", status])
    if not result.get("ok") or not screenshot_path:
        return result

    path = Path(screenshot_path)
    if not path.is_file():
        return result

    page_id = result.get("page_id")
    if not page_id:
        return result

  # Upload screenshot as file block (external URL not available — embed as note)
    note = f"Screenshot captured: {path.name} ({path.stat().st_size} bytes)"
    await _request(
        "PATCH",
        f"/blocks/{page_id}/children",
        json={"children": [_paragraph(note)]},
    )
    return {**result, "screenshot_noted": True}


async def capture_significant_task(
    *,
    task_id: int,
    title: str,
    body: str,
    status: str,
    alignment_score: float | None,
    alignment_notes: str | None,
) -> dict:
    """Screenshot + Notion note for significant tasks (cursor, failed, or misaligned)."""
    from jarvis.services import macos

    significant = (
        status == "failed"
        or (alignment_score is not None and alignment_score < 0.4)
        or any(kw in (title + body).lower() for kw in ("cursor", "deploy", "implement", "refactor"))
    )
    if not significant:
        return {"ok": False, "skipped": True, "reason": "not significant"}

    shot = await macos.screenshot()
    return await sync_task_outcome(
        task_id=task_id,
        title=title,
        body=body,
        status=status,
        alignment_score=alignment_score,
        alignment_notes=alignment_notes,
        screenshot_path=shot.get("path") if shot.get("ok") else None,
    )


async def export_recent_events(events: list[dict]) -> dict:
    """Batch export chat log events to Notion (one summary page)."""
    if not configured() or not events:
        return {"ok": False, "skipped": True}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"William event export · {now}"
    lines = []
    for ev in events[:40]:
        lines.append(
            f"- `{ev.get('created_at', '')}` [{ev.get('source')}/{ev.get('event_type')}] "
            f"{(ev.get('user_message') or ev.get('assistant_reply') or '')[:120]}"
        )
    return await create_learning_page(title=title, body="\n".join(lines), tags=["export", "events"])


async def sync_improvement_insight(
    *,
    title: str,
    body: str,
    tags: list[str] | None = None,
) -> dict:
    return await create_learning_page(
        title=title[:100],
        body=body,
        tags=tags or ["improvement", "screen"],
    )


async def ensure_screen_database() -> dict:
    """Create or return William Screen Log database under parent page."""
    if not configured():
        return {"ok": False, "error": "notion not configured"}

    cached = getattr(ensure_screen_database, "_db_id", None)
    if cached:
        return {"ok": True, "database_id": cached}

    from jarvis.services import screen_observer

    existing = await screen_observer.get_meta("notion_screen_db_id")
    if existing:
        ensure_screen_database._db_id = existing  # type: ignore[attr-defined]
        return {"ok": True, "database_id": existing}

    payload = {
        "parent": {"page_id": settings.notion_parent_page_id},
        "title": [{"type": "text", "text": {"content": "William Screen Log"}}],
        "properties": {
            "Entry": {"title": {}},
            "Timestamp": {"date": {}},
            "App": {"rich_text": {}},
            "Category": {"select": {"options": []}},
            "Productivity": {"select": {"options": []}},
            "Type": {"rich_text": {}},
            "Summary": {"rich_text": {}},
        },
    }
    result = await _request("POST", "/databases", json=payload)
    if not result.get("ok"):
        return result
    db_id = result.get("id")
    if db_id:
        await screen_observer.set_meta("notion_screen_db_id", db_id)
        ensure_screen_database._db_id = db_id  # type: ignore[attr-defined]
    return {"ok": True, "database_id": db_id, "url": result.get("url")}


async def sync_screen_summary(summary: dict) -> dict:
    """Write a 60s screen summary to Notion."""
    if not configured():
        return {"ok": False, "skipped": True}

    obs_type = summary.get("observation_type", "other")
    title = summary.get("title") or "Screen activity"
    page_title = f"{title} · {datetime.now().strftime('%H:%M')}"
    body = (
        f"**{title}**\n\n{summary.get('summary', '')}\n\n"
        f"Type: {obs_type}\n"
        f"Category: {summary.get('category', 'n/a')}\n"
        f"State: {summary.get('productivity_state', 'n/a')}\n"
        f"Apps: {', '.join(summary.get('apps') or [])}"
    )
    tags = ["screen", obs_type, summary.get("category") or "activity"]
    if obs_type in ("gotcha", "problem-solution", "trade-off"):
        await sync_improvement_insight(
            title=f"Screen signal: {title}",
            body=body,
            tags=tags + ["friction"],
        )
    return await create_learning_page(title=page_title, body=body, tags=tags)
