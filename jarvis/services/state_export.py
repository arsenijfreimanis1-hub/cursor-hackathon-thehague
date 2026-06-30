"""Export William Agent state to william-hub for GitHub persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from jarvis.config import settings
from jarvis.services import github_sync

log = logging.getLogger("jarvis.state_export")


async def export_agents(hub: Path) -> int:
    from jarvis.services import agent_registry

    dest = hub / "state" / "agents"
    dest.mkdir(parents=True, exist_ok=True)
    agents = await agent_registry.list_agents(status=None)
    serializable = [a.model_dump() if hasattr(a, "model_dump") else dict(a) for a in agents]
    path = dest / "registry.json"
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return len(agents)


async def export_builds_index(hub: Path) -> int:
    from jarvis.services import build_pipeline

    dest = hub / "state" / "builds"
    dest.mkdir(parents=True, exist_ok=True)
    builds = await build_pipeline.list_builds(limit=50)
    index = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "builds": builds,
    }
    (dest / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return len(builds)


async def export_skills(hub: Path) -> int:
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    dest = hub / "state" / "skills"
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    if skills_dir.is_dir():
        for skill in skills_dir.glob("*.md"):
            dest.joinpath(skill.name).write_text(skill.read_text(encoding="utf-8"), encoding="utf-8")
            count += 1
    return count


async def export_memory_snapshot(hub: Path) -> dict:
    from jarvis.services import memory

    dest = hub / "state" / "memory"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        items = await memory.list_recent(limit=100)
        path = dest / "recent.json"
        path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        return {"ok": True, "count": len(items)}
    except Exception as exc:
        log.warning("memory export failed: %s", exc)
        return {"ok": False, "error": str(exc)}


async def export_all() -> dict:
    """Export full William state and push to william-hub."""
    if not github_sync.configured():
        return {"ok": False, "error": "GitHub not configured"}

    hub = github_sync.hub_state_path()
    hub.mkdir(parents=True, exist_ok=True)

    manifest = {
        "agent": settings.agent_name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workspace_dir": str(settings.workspace_dir),
        "data_dir": str(settings.data_dir),
    }
    (hub / "state").mkdir(parents=True, exist_ok=True)
    (hub / "state" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    agents_n = await export_agents(hub)
    builds_n = await export_builds_index(hub)
    skills_n = await export_skills(hub)
    memory = await export_memory_snapshot(hub)

    sync = await github_sync.sync_hub_directory(hub)
    return {
        "ok": sync.get("ok", False),
        "agents": agents_n,
        "builds": builds_n,
        "skills": skills_n,
        "memory": memory,
        "hub_url": sync.get("html_url") or github_sync.hub_repo_url(),
        "push": sync.get("push"),
    }
