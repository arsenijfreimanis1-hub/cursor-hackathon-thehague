"""Validation and auto-fix for build pipeline slices."""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any

from jarvis.config import settings
from jarvis.services import cursor_agent, prd_store

log = logging.getLogger("jarvis.build_validator")

_FIX_TIMEOUT_SEC = 120


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": (proc.stdout or "")[:2000],
            "stderr": (proc.stderr or "")[:2000],
            "code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "code": -1}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "code": -1}


def detect_checks(worktree_path: Path, stack: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Determine which validation commands to run."""
    stack = stack or {}
    checks: list[dict[str, Any]] = []
    path = worktree_path

    if (path / "pyproject.toml").is_file() or (path / "requirements.txt").is_file():
        checks.append({"name": "pytest", "cmd": ["python3", "-m", "pytest", "-q", "--tb=no"], "optional": True})
        checks.append({"name": "compileall", "cmd": ["python3", "-m", "compileall", "-q", "."], "optional": False})
    elif list(path.glob("**/*.py")):
        checks.append({"name": "compileall", "cmd": ["python3", "-m", "compileall", "-q", "."], "optional": False})

    if (path / "package.json").is_file():
        checks.append({"name": "npm_install", "cmd": ["npm", "ci"], "optional": True})
        checks.append({"name": "npm_test", "cmd": ["npm", "test", "--", "--passWithNoTests"], "optional": True})
        if stack.get("language") == "typescript" or (path / "tsconfig.json").is_file():
            checks.append({"name": "tsc", "cmd": ["npx", "tsc", "--noEmit"], "optional": True})

    if not checks:
        checks.append({"name": "compileall", "cmd": ["python3", "-m", "compileall", "-q", "."], "optional": True})

    has_cad = stack.get("domain") == "cad" or any(path.glob("**/*.step")) or any(path.glob("**/*.stl"))
    if has_cad:
        for cad_file in list(path.glob("**/*.step")) + list(path.glob("**/*.stp")) + list(path.glob("**/*.stl")):
            checks.append({
                "name": f"cad_file_{cad_file.name}",
                "cmd": ["test", "-s", str(cad_file.relative_to(path))],
                "optional": False,
            })

    has_media = stack.get("domain") == "media" or any(path.glob("**/*.mp4"))
    if has_media:
        for media_file in list(path.glob("**/*.mp4"))[:3]:
            checks.append({
                "name": f"ffprobe_{media_file.name}",
                "cmd": ["ffprobe", "-v", "error", "-show_entries", "format=duration", str(media_file.relative_to(path))],
                "optional": True,
            })

    return checks


async def validate_slice(
    worktree_path: Path,
    *,
    stack: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run stack-appropriate checks on a slice worktree."""
    checks = detect_checks(worktree_path, stack)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for check in checks:
        result = await asyncio.to_thread(_run_cmd, check["cmd"], worktree_path)
        result["name"] = check["name"]
        results.append(result)
        if not result.get("ok") and not check.get("optional"):
            failures.append(result)
        elif not result.get("ok") and check.get("optional"):
            log.debug("optional check %s failed: %s", check["name"], result.get("stderr", "")[:80])

    return {
        "ok": len(failures) == 0,
        "checks": results,
        "failures": failures,
    }


async def attempt_fix(
    build_id: int,
    slice_item: dict,
    worktree_path: Path,
    validation: dict[str, Any],
) -> bool:
    """One Cursor auto-fix pass for a failed slice validation."""
    failures = validation.get("failures") or validation.get("checks", [])
    err_text = "\n".join(
        f"{f.get('name')}: {f.get('stderr', f.get('error', ''))[:200]}"
        for f in failures
        if not f.get("ok")
    )[:800]

    prd_ctx = prd_store.prd_context_for_slice(build_id, slice_item.get("id", ""))
    prompt = (
        f"Build validation failed for slice {slice_item.get('id')}: {slice_item.get('title')}\n"
        f"Errors:\n{err_text}\n\n"
        f"{prd_ctx}\n\n"
        f"Fix the root cause with minimal changes. Use exact registry names.\n"
        "If you add registry entries, end with NEW_REGISTRY_ENTRIES JSON block."
    )
    try:
        result = await asyncio.wait_for(
            cursor_agent.run(
                prompt,
                cwd=str(worktree_path),
                source="build_validator_fix",
            ),
            timeout=_FIX_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        return False
    if not result.get("ok"):
        return False

    new_entries = prd_store.parse_new_registry_entries(result.get("result", ""))
    if new_entries:
        prd_store.merge_registry_entries(build_id, new_entries)

    from jarvis.services.worktree_manager import commit_worktree

    commit_worktree(worktree_path, f"fix: {slice_item.get('id')} validation")
    return True


async def validate_integration(
    project_path: Path,
    *,
    stack: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Final integration validation on merged project."""
    return await validate_slice(project_path, stack=stack)


async def update_prd_after_slice(
    build_id: int,
    slice_item: dict,
    agent_result: str = "",
) -> int:
    """Merge agent discoveries into PRD and bump version."""
    new_entries = prd_store.parse_new_registry_entries(agent_result)
    if new_entries:
        version = prd_store.merge_registry_entries(build_id, new_entries)
    else:
        version = prd_store.bump_registry_version(build_id)

    slices = prd_store.load_slices(build_id)
    for sl in slices:
        if sl.get("id") == slice_item.get("id"):
            sl["status"] = "done"
    prd_store.save_slices(build_id, slices)

    build_row = await _get_build_prompt(build_id)
    prd_store.generate_prd(
        build_id,
        prompt=build_row,
        slices=slices,
    )
    return version


async def _get_build_prompt(build_id: int) -> str:
    import aiosqlite
    from jarvis.database import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT prompt FROM builds WHERE id = ?", (build_id,))).fetchone()
        return row[0] if row else ""
