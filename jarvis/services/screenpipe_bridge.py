"""Optional bridge to screenpipe localhost API for richer capture history."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from jarvis.config import settings
from jarvis.services import screen_observer

log = logging.getLogger("jarvis.screenpipe")


async def health() -> dict:
    if not settings.screenpipe_bridge_enabled:
        return {"ok": False, "enabled": False}
    url = f"{settings.screenpipe_base_url.rstrip('/')}/health"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
            return {"ok": resp.status_code < 400, "status": resp.status_code}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def pull_recent(*, limit: int = 20) -> dict:
    if not settings.screenpipe_bridge_enabled:
        return {"ok": False, "skipped": True}
    base = settings.screenpipe_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{base}/search", params={"content_type": "ocr", "limit": limit})
            if resp.status_code >= 400:
                return {"ok": False, "error": resp.text[:200]}
            data = resp.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    events: list[dict] = []
    for item in data if isinstance(data, list) else data.get("data", []):
        if not isinstance(item, dict):
            continue
        ts = item.get("timestamp") or item.get("created_at") or datetime.now(timezone.utc).isoformat()
        events.append(
            {
                "ts": ts,
                "app": item.get("app_name") or item.get("app"),
                "window_title": item.get("window_title") or item.get("title"),
                "ocr_text": item.get("text") or item.get("ocr_text") or "",
                "phash": item.get("frame_id") or item.get("id"),
            }
        )
    if not events:
        return {"ok": True, "ingested": 0}
    result = await screen_observer.ingest_events(events)
    return {**result, "source": "screenpipe"}
