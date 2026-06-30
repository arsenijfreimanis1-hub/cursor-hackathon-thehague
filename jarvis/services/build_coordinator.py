"""Parallel Cursor SDK execution for build slices."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from jarvis.config import settings
from jarvis.services import compute_fleet, github_sync, prd_store, skill_domains, skills, worktree_manager

log = logging.getLogger("jarvis.build_coordinator")

_SLICE_TIMEOUT_SEC = 300


def _build_agent_prompt(
    build_id: int,
    slice_item: dict,
    *,
    prd_version: int,
    completed_deps: list[str],
) -> str:
    ctx = prd_store.prd_context_for_slice(build_id, slice_item.get("id", ""))
    criteria = slice_item.get("acceptance_criteria") or []
    criteria_text = "\n".join(f"- {c}" for c in criteria) or "- Implement as specified"
    deps_text = ", ".join(completed_deps) if completed_deps else "none"
    files = slice_item.get("files") or []
    files_text = "\n".join(f"- {f}" for f in files) if files else "- Assign files per slice contract"

    research = slice_item.get("research") or {}
    deep_analysis = research.get("analysis") or research.get("raw") or ""
    research_block = ""
    if deep_analysis:
        research_block = f"\n\nPRIOR DEEP DIVE (use this, do not redo from scratch):\n{deep_analysis[:8000]}\n"

    domains = skill_domains.detect_slice_domains(slice_item)
    domain_block = ""
    if domains:
        domain_block = skills.load_skills_block(domains=domains, include_external=True)
        if domain_block:
            domain_block = f"\n\nDOMAIN SKILLS ({', '.join(domains)}):\n{domain_block}\n"

    return (
        f"You are slice {slice_item.get('id')}: {slice_item.get('title')}\n"
        f"Project PRD version: {prd_version}\n\n"
        f"{ctx}\n"
        f"{domain_block}"
        f"{research_block}\n"
        f"Your scope:\n{slice_item.get('prompt', '')}\n\n"
        f"Files to create/edit:\n{files_text}\n\n"
        f"Dependencies already merged: {deps_text}\n\n"
        f"Acceptance criteria:\n{criteria_text}\n\n"
        "Rules:\n"
        "- Use EXACT names from the variable registry\n"
        "- Only edit files in your slice contract\n"
        "- Implement fully; do not leave TODOs\n"
        "- Commit your changes when done\n"
        "- Push only when this slice is running against a GitHub-backed project\n"
        "- If you must add a registry entry, end with:\n"
        '  NEW_REGISTRY_ENTRIES\n  {"entries": {"Name": {"type": "class", "file": "path"}}}\n'
    )


async def execute_slice(
    build_id: int,
    slice_item: dict,
    *,
    project_path: Path,
    worktrees_dir: Path,
    prd_version: int,
    completed_deps: list[str],
    github_repo_url: str = "",
    clone_url: str = "",
) -> dict[str, Any]:
    """Run one slice with local workers by default, cloud optionally."""
    slice_id = slice_item.get("id", "slice-unknown")
    branch = f"slice/{slice_id}"
    prompt = _build_agent_prompt(
        build_id,
        slice_item,
        prd_version=prd_version,
        completed_deps=completed_deps,
    )

    runtime = compute_fleet.resolve_runtime()
    use_cloud = runtime == "cloud" and bool(clone_url or github_repo_url)
    repo_ref = clone_url or (f"{github_repo_url}.git" if github_repo_url and not github_repo_url.endswith(".git") else github_repo_url)

    wt_path = worktree_manager.create_worktree(
        project_path,
        worktrees_dir,
        slice_id,
        base_branch=worktree_manager.INTEGRATION_BRANCH,
    )

    if use_cloud and repo_ref:
        github_sync.ensure_branch(project_path, branch, from_ref=worktree_manager.INTEGRATION_BRANCH)
        github_sync.push_branch(project_path, branch)
        result = await compute_fleet.dispatch_slice(
            prompt,
            build_id=build_id,
            slice_id=slice_id,
            repo_url=repo_ref,
            branch=branch,
            runtime=runtime,
            source="build_pipeline",
            timeout_sec=_SLICE_TIMEOUT_SEC,
        )
        if result.get("ok"):
            github_sync.pull_branch(project_path, branch)
            worktree_manager.commit_worktree(wt_path, f"feat: {slice_id} — cloud sync")
    else:
        try:
            from jarvis.services import cursor_agent

            slice_domains = skill_domains.detect_slice_domains(slice_item)
            result = await asyncio.wait_for(
                cursor_agent.run(
                    prompt,
                    cwd=str(wt_path),
                    source="build_pipeline",
                    runtime="local",
                    domains=slice_domains or None,
                ),
                timeout=_SLICE_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            return {"ok": False, "error": "slice timed out", "slice_id": slice_id, "worktree_path": str(wt_path)}
        worktree_manager.commit_worktree(wt_path, f"feat: {slice_id} — {slice_item.get('title', '')[:60]}")
        if clone_url:
            github_sync.push_branch(project_path, branch)

    return {
        "ok": result.get("ok", False),
        "slice_id": slice_id,
        "worktree_path": str(wt_path),
        "result": result.get("result", ""),
        "error": result.get("error", ""),
        "trace_db_id": result.get("trace_db_id"),
        "runtime": result.get("runtime", runtime),
    }


async def execute_build_slices(
    build_id: int,
    *,
    project_path: Path,
    slices: list[dict],
    prd_version: int,
    on_slice_done: Any | None = None,
    github_repo_url: str = "",
    clone_url: str = "",
) -> dict[str, Any]:
    """Execute all slices respecting dependencies with parallel cap."""
    parallel = compute_fleet.effective_parallel()
    worktrees_dir = prd_store.build_artifact_dir(build_id) / "worktrees"
    completed: set[str] = set()
    failed: list[str] = []
    sem = asyncio.Semaphore(parallel)
    in_flight: dict[str, asyncio.Task] = {}

    async def _run_one(sl: dict) -> dict:
        async with sem:
            deps_done = [d for d in (sl.get("deps") or []) if d in completed]
            registry = prd_store.load_registry(build_id)
            version = int(registry.get("version", prd_version))
            return await execute_slice(
                build_id,
                sl,
                project_path=project_path,
                worktrees_dir=worktrees_dir,
                prd_version=version,
                completed_deps=deps_done,
                github_repo_url=github_repo_url,
                clone_url=clone_url,
            )

    remaining = {sl["id"]: sl for sl in slices if sl.get("status") != "done"}

    while remaining:
        ready = worktree_manager.ready_slices(list(remaining.values()), completed)
        ready = [sl for sl in ready if sl["id"] not in in_flight]

        for sl in ready:
            if len(in_flight) >= parallel:
                break
            task = asyncio.create_task(_run_one(sl))
            in_flight[sl["id"]] = task
            sl["status"] = "running"
            prd_store.save_slices(build_id, slices)

        if not in_flight:
            break

        done, _ = await asyncio.wait(in_flight.values(), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            sid = next(k for k, t in in_flight.items() if t is task)
            del in_flight[sid]
            outcome = await task
            sl = remaining.get(sid)
            if not sl:
                continue

            if outcome.get("ok"):
                sl["status"] = "done"
                completed.add(sid)
                merge = worktree_manager.merge_slice_to_integration(project_path, sid)
                if not merge.get("ok"):
                    sl["status"] = "failed"
                    sl["error"] = merge.get("error", "merge failed")
                    failed.append(sid)
                    completed.discard(sid)
                else:
                    if clone_url:
                        github_sync.push_branch(project_path, worktree_manager.INTEGRATION_BRANCH)
                    if on_slice_done:
                        await on_slice_done(build_id, sl, outcome)
            else:
                sl["status"] = "failed"
                sl["error"] = outcome.get("error", "execution failed")
                failed.append(sid)

            prd_store.save_slices(build_id, slices)
            if sid in remaining and sl.get("status") in ("done", "failed"):
                del remaining[sid]

    prd_store.save_slices(build_id, slices)
    return {
        "ok": len(failed) == 0 and not remaining,
        "completed": list(completed),
        "failed": failed,
        "remaining": list(remaining.keys()),
    }
