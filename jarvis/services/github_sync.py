"""GitHub persistence — william-hub state repo + per-project repos."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from jarvis.config import settings

log = logging.getLogger("jarvis.github_sync")

API_BASE = "https://api.github.com"


def configured() -> bool:
    return bool(resolved_token() and resolved_owner())


def resolved_token() -> str:
    import os

    for candidate in (
        getattr(settings, "github_token", ""),
        os.environ.get("GITHUB_TOKEN", ""),
        os.environ.get("GH_TOKEN", ""),
        os.environ.get("JARVIS_GITHUB_TOKEN", ""),
    ):
        if candidate and len(candidate) >= 20 and not candidate.endswith("..."):
            return candidate.strip()
    return ""


def resolved_owner() -> str:
    import os

    for candidate in (
        getattr(settings, "github_owner", ""),
        os.environ.get("GITHUB_OWNER", ""),
        os.environ.get("JARVIS_GITHUB_OWNER", ""),
    ):
        if candidate and candidate.strip():
            return candidate.strip()
    return ""


def hub_repo_name() -> str:
    return getattr(settings, "william_hub_repo", "william-hub") or "william-hub"


def hub_repo_url() -> str:
    owner = resolved_owner()
    return f"https://github.com/{owner}/{hub_repo_name()}.git"


def auth_clone_url(https_url: str) -> str:
    token = resolved_token()
    if not token or not https_url.startswith("https://github.com/"):
        return https_url
    return https_url.replace("https://github.com/", f"https://x-access-token:{quote(token)}@github.com/")


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _api_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {resolved_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _api_request(method: str, path: str, *, json_body: dict | None = None) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, headers=_api_headers(), json=json_body)
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": resp.text[:500]}
        if resp.status_code == 204:
            return {"ok": True}
        try:
            data = resp.json()
        except Exception:
            data = {}
        return {"ok": True, "data": data}


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return slug[:60] or "project"


async def ensure_repo(
    name: str,
    *,
    description: str = "",
    private: bool = True,
    is_hub: bool = False,
) -> dict[str, Any]:
    """Create GitHub repo if it does not exist."""
    if not configured():
        return {"ok": False, "error": "GitHub not configured (GITHUB_TOKEN + GITHUB_OWNER)"}

    owner = resolved_owner()
    get = await _api_request("GET", f"/repos/{owner}/{name}")
    if get.get("ok") and get.get("data"):
        data = get["data"]
        return {
            "ok": True,
            "created": False,
            "name": data.get("name"),
            "html_url": data.get("html_url"),
            "clone_url": data.get("clone_url"),
            "private": data.get("private"),
        }

    body = {
        "name": name,
        "description": description or ("William Agent state hub" if is_hub else f"William build project: {name}"),
        "private": private,
        "auto_init": True,
    }
    org = getattr(settings, "github_org", "") or ""
    if org and org != owner:
        created = await _api_request("POST", f"/orgs/{org}/repos", json_body=body)
        owner = org
    else:
        created = await _api_request("POST", "/user/repos", json_body=body)

    if not created.get("ok"):
        return created
    data = created.get("data") or {}
    return {
        "ok": True,
        "created": True,
        "name": data.get("name"),
        "html_url": data.get("html_url"),
        "clone_url": data.get("clone_url"),
        "private": data.get("private"),
    }


async def ensure_hub_repo() -> dict[str, Any]:
    return await ensure_repo(
        hub_repo_name(),
        description="William Agent — persistent state, builds, agents, memory exports",
        private=True,
        is_hub=True,
    )


async def create_project_repo(build_prompt: str, *, build_id: int) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    name = f"william-project-{build_id}-{_slug(build_prompt)[:30]}-{ts}"
    return await ensure_repo(
        name,
        description=f"William build #{build_id}: {build_prompt[:200]}",
        private=getattr(settings, "github_projects_private", True),
    )


def ensure_remote(repo_path: Path, url: str, *, name: str = "origin") -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    existing = _run_git("remote", "get-url", name, cwd=repo_path)
    auth_url = auth_clone_url(url)
    if existing.returncode != 0:
        _run_git("remote", "add", name, auth_url, cwd=repo_path)
    elif existing.stdout.strip() != auth_url:
        _run_git("remote", "set-url", name, auth_url, cwd=repo_path)


def clone_or_init(repo_path: Path, clone_url: str, *, branch: str = "main") -> dict[str, Any]:
    """Clone remote repo or init local and connect remote."""
    if (repo_path / ".git").exists() or (repo_path / ".git").is_file():
        ensure_remote(repo_path, clone_url)
        pull = _run_git("pull", "origin", branch, cwd=repo_path)
        return {"ok": pull.returncode == 0, "action": "pull", "stderr": pull.stderr[:300]}

    repo_path.parent.mkdir(parents=True, exist_ok=True)
    if repo_path.exists() and any(repo_path.iterdir()):
        _run_git("init", cwd=repo_path)
        _run_git("checkout", "-b", branch, cwd=repo_path)
        ensure_remote(repo_path, clone_url)
        _run_git("add", "-A", cwd=repo_path)
        _run_git("commit", "-m", "Initial William project scaffold", cwd=repo_path)
        push = _run_git("push", "-u", "origin", branch, cwd=repo_path)
        return {"ok": push.returncode == 0, "action": "init_push", "stderr": push.stderr[:300]}

    clone = _run_git("clone", auth_clone_url(clone_url), str(repo_path), cwd=repo_path.parent)
    return {"ok": clone.returncode == 0, "action": "clone", "stderr": clone.stderr[:300]}


def push_branch(repo_path: Path, branch: str, *, set_upstream: bool = True) -> dict[str, Any]:
    if not (repo_path / ".git").exists() and not (repo_path / ".git").is_file():
        return {"ok": False, "error": "not a git repo"}
    checkout = _run_git("checkout", branch, cwd=repo_path)
    if checkout.returncode != 0:
        _run_git("checkout", "-b", branch, cwd=repo_path)
    _run_git("add", "-A", cwd=repo_path)
    status = _run_git("status", "--porcelain", cwd=repo_path)
    if (status.stdout or "").strip():
        _run_git("commit", "-m", f"sync: {branch} @ {datetime.now(timezone.utc).isoformat()}", cwd=repo_path)
    args = ["push", "origin", branch]
    if set_upstream:
        args = ["push", "-u", "origin", branch]
    push = _run_git(*args, cwd=repo_path)
    return {"ok": push.returncode == 0, "branch": branch, "stderr": (push.stderr or push.stdout or "")[:400]}


def pull_branch(repo_path: Path, branch: str) -> dict[str, Any]:
    _run_git("fetch", "origin", cwd=repo_path)
    checkout = _run_git("checkout", branch, cwd=repo_path)
    if checkout.returncode != 0:
        _run_git("checkout", "-b", branch, f"origin/{branch}", cwd=repo_path)
    pull = _run_git("pull", "origin", branch, cwd=repo_path)
    return {"ok": pull.returncode == 0, "stderr": (pull.stderr or "")[:300]}


def ensure_branch(repo_path: Path, branch: str, *, from_ref: str = "main") -> dict[str, Any]:
    current = _run_git("branch", "--show-current", cwd=repo_path)
    exists = _run_git("show-ref", "--verify", f"refs/heads/{branch}", cwd=repo_path)
    if exists.returncode == 0:
        _run_git("checkout", branch, cwd=repo_path)
    else:
        _run_git("checkout", "-b", branch, from_ref, cwd=repo_path)
    return {"ok": True, "branch": branch, "previous": (current.stdout or "").strip()}


async def sync_hub_directory(hub_path: Path) -> dict[str, Any]:
    """Push state/ directory contents to william-hub."""
    hub = await ensure_hub_repo()
    if not hub.get("ok"):
        return hub

    clone_url = hub.get("clone_url") or hub_repo_url()
    ensure_remote(hub_path, clone_url)
    if not (hub_path / ".git").exists():
        _run_git("init", cwd=hub_path)
        _run_git("checkout", "-b", "main", cwd=hub_path)
        readme = hub_path / "README.md"
        if not readme.is_file():
            readme.write_text(
                "# William Hub\n\nPersistent state for William Agent — builds, agents, exports.\n",
                encoding="utf-8",
            )

    push = push_branch(hub_path, "main")
    return {**hub, "push": push}


def hub_state_path() -> Path:
    return settings.data_dir / "william-hub"


async def export_build_manifest(build_id: int, *, github_repo_url: str = "") -> dict[str, Any]:
    """Copy build artifacts into hub state/builds/{id}/."""
    from jarvis.services import prd_store

    hub = hub_state_path()
    dest = hub / "state" / "builds" / str(build_id)
    dest.mkdir(parents=True, exist_ok=True)

    artifact = prd_store.build_artifact_dir(build_id)
    for name in ("slices.json", "PRD.md", "registry.json", "transcript.md"):
        src = artifact / name
        if src.is_file():
            dest.joinpath(name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "build_id": build_id,
        "github_repo_url": github_repo_url,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    dest.joinpath("manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(dest)}


async def bootstrap_project_github(
    project_path: Path,
    *,
    build_id: int,
    prompt: str,
) -> dict[str, Any]:
    """Create per-project GitHub repo and connect local workspace."""
    if not configured():
        return {"ok": False, "error": "GitHub not configured", "skipped": True}

    repo = await create_project_repo(prompt, build_id=build_id)
    if not repo.get("ok"):
        return repo

    clone_url = repo.get("clone_url") or ""
    init = clone_or_init(project_path, clone_url)
    ensure_remote(project_path, clone_url)

    from jarvis.services.worktree_manager import INTEGRATION_BRANCH

    _run_git("branch", INTEGRATION_BRANCH, cwd=project_path)
    push_main = push_branch(project_path, "main")

    return {
        "ok": init.get("ok", True) and push_main.get("ok", True),
        "github_repo_url": repo.get("html_url") or clone_url.replace(".git", ""),
        "clone_url": clone_url,
        "repo_name": repo.get("name"),
        "created": repo.get("created"),
    }
