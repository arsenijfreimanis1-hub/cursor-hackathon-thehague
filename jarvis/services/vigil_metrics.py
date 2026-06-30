"""Vigil Cloud signals — optional telemetry via app.vigil-agent.com (NOT the LLM proxy URL)."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx

from jarvis.config import settings

log = logging.getLogger("jarvis.vigil")

_client: httpx.AsyncClient | None = None
_queue: asyncio.Queue[dict] | None = None
_worker_task: asyncio.Task | None = None


def configured() -> bool:
    return bool(settings.vigil_enabled and settings.resolved_vigil_api_key())


def status() -> dict:
    from jarvis.services import vigil_proxy

    return {
        "enabled": settings.vigil_enabled,
        "configured": configured(),
        "agent": settings.vigil_agent_id,
        "cloud_api": bool(settings.resolved_vigil_api_key()),
        "cloud_api_url": settings.vigil_api_url,
        "proxy": vigil_proxy.status(),
        "note": "api.vigil.wtf is an LLM proxy — not for custom signal POSTs. Use vigil_proxy for LLM metrics.",
        "queue_depth": _queue.qsize() if _queue else 0,
        "worker_running": _worker_task is not None and not _worker_task.done(),
    }


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=5.0))
    return _client


async def close() -> None:
    global _client, _worker_task, _queue
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    if _queue:
        _queue = None
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def start() -> None:
    global _queue, _worker_task
    if not configured():
        return
    if _worker_task and not _worker_task.done():
        return
    _queue = asyncio.Queue(maxsize=500)
    _worker_task = asyncio.create_task(_worker_loop())


async def _worker_loop() -> None:
    assert _queue is not None
    while True:
        item = await _queue.get()
        try:
            await _deliver(item)
        except Exception as exc:
            log.debug("vigil deliver failed: %s", exc)
        finally:
            _queue.task_done()


def _enqueue(payload: dict) -> None:
    if not configured() or _queue is None:
        return
    try:
        _queue.put_nowait(payload)
    except asyncio.QueueFull:
        log.warning("vigil queue full — dropping event")


async def _post_json(url: str, body: dict, *, headers: dict | None = None) -> bool:
    client = await _get_client()
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    try:
        resp = await client.post(url, json=body, headers=hdrs)
        if resp.status_code >= 400:
            log.debug("vigil POST %s -> %s %s", url, resp.status_code, resp.text[:200])
            return False
        return True
    except httpx.HTTPError as exc:
        log.debug("vigil POST %s failed: %s", url, exc)
        return False


async def _deliver(item: dict) -> None:
    api_key = settings.resolved_vigil_api_key()
    if not api_key:
        return
    base = settings.vigil_api_url.rstrip("/")
    agent = settings.vigil_agent_id

    if item.get("kind") == "signal":
        await _post_json(
            f"{base}/api/signal",
            {
                "agent": agent,
                "content": item["content"][:800],
                "signal_type": item.get("signal_type", "observation"),
            },
            headers={"Authorization": f"Bearer {api_key}"},
        )


def emit_signal(content: str, *, signal_type: str = "observation", metadata: dict | None = None) -> None:
    if metadata:
        content = f"{content} | {metadata.get('event', '')}"
    _enqueue({"kind": "signal", "content": content, "signal_type": signal_type})


def record_tool_call(
    tool: str,
    duration_ms: float,
    *,
    status: str = "ok",
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    # Tool metrics only go to Vigil Cloud if API key is set — never to the LLM proxy URL.
    if not configured():
        return
    emit_signal(
        f"[tool/{status}] {tool} {duration_ms:.0f}ms",
        signal_type="alert" if status == "error" else "observation",
        metadata={"tool": tool, "duration_ms": duration_ms, "status": status, "error": error, **(metadata or {})},
    )


@asynccontextmanager
async def track_tool(tool: str, **metadata: Any):
    started = time.perf_counter()
    status = "ok"
    err: str | None = None
    try:
        yield
    except Exception as exc:
        status = "error"
        err = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        record_tool_call(tool, duration_ms, status=status, error=err, metadata=metadata or None)


def emit_interaction(
    *,
    source: str,
    user_message: str,
    assistant_reply: str,
    intent: str | None,
    engine: str | None,
    task_status: str | None,
    alignment_score: float | None,
    metadata: dict | None = None,
) -> None:
    if not configured():
        return
    score = f"{alignment_score:.2f}" if alignment_score is not None else "?"
    content = (
        f"[{source}/{engine or '?'}] intent={intent or '?'} status={task_status or '-'} "
        f"align={score} — {user_message[:120]}"
    )
    signal_type = "alert" if alignment_score is not None and alignment_score < 0.4 else "observation"
    emit_signal(content, signal_type=signal_type, metadata=metadata)


def emit_task_outcome(
    *,
    source: str,
    user_message: str,
    reply: str,
    task_status: str,
    engine: str | None,
    alignment_score: float | None,
) -> None:
    if not configured():
        return
    content = f"[task/{task_status}] {engine or '?'} — {user_message[:100]}"
    signal_type = "alert" if task_status == "failed" else "observation"
    emit_signal(content, signal_type=signal_type)


def emit_integration(integration: str, *, detail: str | None = None, metadata: dict | None = None) -> None:
    if not configured():
        return
    content = f"[integration/{integration}] {(detail or '')[:200]}"
    emit_signal(content, signal_type="observation", metadata=metadata)
