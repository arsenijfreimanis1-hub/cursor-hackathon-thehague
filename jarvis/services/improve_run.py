"""Autonomous self-improvement run — full control for a time-limited session."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone

import aiosqlite

from jarvis.config import settings
from jarvis.database import DB_PATH
from jarvis.services import cursor_agent, desktop, improve_tests, macos, openclaw, screen_observer, security, self_modify, web

log = logging.getLogger("jarvis.improve_run")

_active_task: asyncio.Task | None = None
_run_id: int | None = None
_stop_requested = False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS improve_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'running',
    duration_minutes INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    finished_at TEXT,
    log TEXT NOT NULL DEFAULT '[]',
    findings TEXT NOT NULL DEFAULT '[]',
    fixes_applied INTEGER NOT NULL DEFAULT 0
);
"""


async def ensure_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _append_log(run_id: int, message: str, *, level: str = "info") -> None:
    entry = {"ts": _now().isoformat(), "level": level, "message": message}
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT log FROM improve_runs WHERE id = ?", (run_id,))).fetchone()
        logs = json.loads(row[0] if row else "[]")
        logs.append(entry)
        if len(logs) > 200:
            logs = logs[-200:]
        await db.execute("UPDATE improve_runs SET log = ? WHERE id = ?", (json.dumps(logs), run_id))
        await db.commit()
    log.info("improve_run[%s]: %s", run_id, message)


async def _save_findings(run_id: int, findings: list[dict]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE improve_runs SET findings = ? WHERE id = ?",
            (json.dumps(findings), run_id),
        )
        await db.commit()


async def _increment_fixes(run_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE improve_runs SET fixes_applied = fixes_applied + 1 WHERE id = ?",
            (run_id,),
        )
        await db.commit()


async def is_running() -> bool:
    return _active_task is not None and not _active_task.done()


async def get_status(run_id: int | None = None) -> dict:
    await ensure_tables()
    rid = run_id or _run_id
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if rid:
            row = await (await db.execute("SELECT * FROM improve_runs WHERE id = ?", (rid,))).fetchone()
        else:
            row = await (
                await db.execute("SELECT * FROM improve_runs ORDER BY id DESC LIMIT 1")
            ).fetchone()
        if not row:
            return {"running": False}
        data = dict(row)
        data["log"] = json.loads(data.get("log") or "[]")
        data["findings"] = json.loads(data.get("findings") or "[]")
        data["running"] = data["status"] == "running" and await is_running()
        ends = datetime.fromisoformat(data["ends_at"].replace("Z", "+00:00"))
        data["seconds_remaining"] = max(0, int((ends - _now()).total_seconds()))
        return data


async def stop() -> dict:
    global _stop_requested
    _stop_requested = True
    if _active_task and not _active_task.done():
        _active_task.cancel()
    if _run_id:
        await _append_log(_run_id, "Stop requested by user", level="warn")
    await security.set_full_access(False)
    return {"ok": True, "stopping": True}


async def start(*, duration_minutes: int = 30) -> dict:
    global _active_task, _run_id, _stop_requested

    if await is_running():
        return {"ok": False, "error": "improvement run already active", "run_id": _run_id}

    duration_minutes = max(5, min(180, duration_minutes))
    await ensure_tables()
    _stop_requested = False

    started = _now()
    ends = started + timedelta(minutes=duration_minutes)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO improve_runs (status, duration_minutes, started_at, ends_at)
            VALUES ('running', ?, ?, ?)
            """,
            (duration_minutes, started.isoformat(), ends.isoformat()),
        )
        await db.commit()
        _run_id = cursor.lastrowid

    await security.set_full_access(True)
    await _append_log(_run_id, f"Self-improvement run started — {duration_minutes} min, full control enabled")

    _active_task = asyncio.create_task(_run_loop(_run_id, ends))
    return {
        "ok": True,
        "run_id": _run_id,
        "duration_minutes": duration_minutes,
        "ends_at": ends.isoformat(),
        "full_access": True,
    }


async def _restart_services() -> None:
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    for label in ("com.willy.jarvis-core", "com.willy.jarvis-helper"):
        subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"],
            check=False,
            capture_output=True,
        )
    await asyncio.sleep(4)


async def _open_test_surfaces() -> None:
    subprocess.run(["open", f"http://127.0.0.1:{settings.port}/"], check=False)
    await asyncio.sleep(1)


_PERMISSION_TESTS = {"accessibility"}

_FIX_TIMEOUT_SEC = 90


async def _handle_permission_failure(failure: dict, run_id: int) -> bool:
    name = failure.get("name", "")
    if name == "accessibility":
        await _append_log(run_id, "Bootstrapping Accessibility permission for JarvisHelper")
        from jarvis.services import permissions

        result = await permissions.bootstrap(force_settings=True)
        granted = result.get("accessibility")
        if granted:
            await _append_log(run_id, "Accessibility granted")
            return True
        await _append_log(run_id, "Accessibility still needed — enable JarvisHelper in System Settings", level="warn")
        return False
    return False


async def _attempt_fix(failure: dict, run_id: int) -> bool:
    name = failure.get("name", "unknown")
    err = failure.get("error", "")
    await _append_log(run_id, f"Investigating failure: {name} — {err[:120]}", level="warn")

    if name in _PERMISSION_TESTS:
        return await _handle_permission_failure(failure, run_id)

    research = await web.research(f"jarvis python fastapi {name} {err[:100]} fix")
    research_text = (research.get("text") or "")[:1200]
    screen_ctx = ""
    if settings.screen_watch_enabled:
        screen_ctx = await screen_observer.get_recent_context(minutes=20, query=name)

    prompt = (
        f"Self-improvement automated test failed.\n"
        f"Test: {name}\n"
        f"Error: {err}\n"
        f"Detail: {failure.get('detail', '')}\n\n"
        f"Web research:\n{research_text}\n\n"
    )
    if screen_ctx:
        prompt += f"Screen context (what boss was doing):\n{screen_ctx[:800]}\n\n"
    prompt += (
        f"Repository: {settings.workspace_dir}\n"
        "Fix the root cause with minimal changes. Only edit files inside jarvis-core. "
        "Do not remove tests. Summarize what you fixed."
    )
    try:
        result = await asyncio.wait_for(
            cursor_agent.run(
                prompt,
                cwd=str(settings.workspace_dir),
                source="improve_run",
            ),
            timeout=_FIX_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        await _append_log(run_id, f"Cursor fix timed out for {name}", level="warn")
        return False
    if not result.get("ok"):
        await _append_log(run_id, f"Cursor fix failed for {name}: {result.get('error', '')[:120]}", level="error")
        return False

    trace_id = result.get("trace_db_id")
    if trace_id:
        from jarvis.services import cursor_trace

        transcript = await cursor_trace.format_transcript(trace_id)
        if transcript:
            await _append_log(run_id, f"Cursor trace #{trace_id}: {transcript[:200]}")

    if result.get("popup_before", {}).get("handled") or result.get("popup_after", {}).get("handled"):
        await _append_log(run_id, "Popup dismissed during Cursor run", level="info")

    await _append_log(run_id, f"Cursor applied fix for {name}: {(result.get('result') or '')[:200]}")
    await _increment_fixes(run_id)
    await _restart_services()
    return True


async def _ui_probe(run_id: int) -> None:
    await _append_log(run_id, "UI probe: screenshot + vision analysis")
    await _open_test_surfaces()
    from jarvis.services import popup_handler

    popups = await popup_handler.handle_popups(full_control=True)
    if popups.get("handled"):
        await _append_log(run_id, f"Popup handled: {popups.get('actions')}", level="info")
    screen_ctx = ""
    if settings.screen_watch_enabled:
        screen_ctx = await screen_observer.get_recent_context(minutes=15)
        if screen_ctx:
            await _append_log(run_id, f"Screen context: {screen_ctx[:120]}")
    analysis = await desktop.analyze_and_act(full_control=True)
    if analysis.get("ok"):
        await _append_log(run_id, f"Vision: {(analysis.get('analysis') or '')[:180]}")
        if analysis.get("acted"):
            await _append_log(run_id, f"Desktop action: {analysis.get('action_result')}")
    else:
        await _append_log(run_id, f"Vision probe failed: {analysis.get('error', '')}", level="warn")


async def _run_loop(run_id: int, deadline: datetime) -> None:
    global _stop_requested, _active_task
    all_findings: list[dict] = []
    cycle = 0
    status = "completed"

    try:
        self_modify.ensure_repo()
        await _open_test_surfaces()
        from jarvis.services import permissions

        await permissions.bootstrap()

        oc = await openclaw.health()
        if not oc.get("whatsapp"):
            await _append_log(run_id, "OpenClaw WhatsApp offline — restarting gateway", level="warn")
            await openclaw.ensure_whatsapp()

        while _now() < deadline and not _stop_requested:
            cycle += 1
            await _append_log(run_id, f"--- Test cycle {cycle} ---")

            results = await improve_tests.run_all()
            failures = [r for r in results if not r.get("ok")]
            passes = len(results) - len(failures)
            await _append_log(run_id, f"Tests: {passes}/{len(results)} passed")

            all_findings = results
            await _save_findings(run_id, all_findings)

            if failures:
                for failure in failures[:3]:
                    if _now() >= deadline or _stop_requested:
                        break
                    fixed = await _attempt_fix(failure, run_id)
                    if fixed:
                        retest = await improve_tests.run_single(failure["name"])
                        if retest and retest.get("ok"):
                            await _append_log(run_id, f"Re-test passed: {failure['name']}", level="info")
                        else:
                            await _append_log(run_id, f"Re-test still failing: {failure['name']}", level="warn")
            else:
                await _append_log(run_id, "All automated tests passed")

            if cycle % 2 == 0:
                await _ui_probe(run_id)

            if _now() >= deadline:
                break
            await asyncio.sleep(20)

        status = "stopped" if _stop_requested else "completed"
        await _append_log(run_id, f"Run {status}")
    except asyncio.CancelledError:
        status = "stopped"
        await _append_log(run_id, "Run cancelled", level="warn")
    except Exception as exc:
        status = "failed"
        log.exception("improve_run failed")
        await _append_log(run_id, f"Run failed: {exc}", level="error")
    finally:
        await security.set_full_access(False)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE improve_runs SET status = ?, finished_at = ? WHERE id = ?",
                (status, _now().isoformat(), run_id),
            )
            await db.commit()
        _active_task = None
        _stop_requested = False
