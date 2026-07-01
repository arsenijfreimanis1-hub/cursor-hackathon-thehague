"""Real-time activity broadcast for SSE clients (live agent timeline)."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

from jarvis.config import settings

_subscribers: set[asyncio.Queue] = set()
_FRAMES_DIR = settings.data_dir / "activity" / "frames"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def subscribe() -> AsyncIterator[dict[str, Any]]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.add(queue)
    try:
        while True:
            event = await queue.get()
            yield event
    finally:
        _subscribers.discard(queue)


async def broadcast(event: dict[str, Any]) -> None:
    payload = {**event, "ts": event.get("ts") or _now()}
    dead: list[asyncio.Queue] = []
    for queue in list(_subscribers):
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(queue)
    for queue in dead:
        _subscribers.discard(queue)


async def emit(
    kind: str,
    title: str,
    *,
    detail: str = "",
    status: str = "running",
    engine: str | None = None,
    image_url: str | None = None,
    metadata: dict | None = None,
) -> None:
    await broadcast(
        {
            "kind": kind,
            "title": title,
            "detail": detail,
            "status": status,
            "engine": engine,
            "image_url": image_url,
            "metadata": metadata or {},
        }
    )


async def store_frame(source_path: str) -> str | None:
    """Copy a screenshot into activity storage and return frame id."""
    src = Path(source_path)
    if not src.is_file():
        return None
    _FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    frame_id = uuid.uuid4().hex[:12]
    dest = _FRAMES_DIR / f"{frame_id}.png"
    try:
        await asyncio.to_thread(shutil.copy2, src, dest)
    except OSError:
        return None
    return frame_id


def frame_path(frame_id: str) -> Path | None:
    if not frame_id or "/" in frame_id or ".." in frame_id:
        return None
    path = _FRAMES_DIR / f"{frame_id}.png"
    return path if path.is_file() else None


def event_to_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"
