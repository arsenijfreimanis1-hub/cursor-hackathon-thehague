import re
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from jarvis.config import settings
from jarvis.paths import venv_python
from jarvis.services import approvals, cursor_agent, security

SANDBOX_PREFIX = "sandbox/"

SELF_MODIFY_PREFIX = re.compile(
    r"^(?:self-?modify|improve yourself|fix yourself|change your(?:\s+own)?\s+code)[:]\s*",
    re.I,
)
IMPROVE_RUN_PREFIX = re.compile(
    r"^(?:improve-?run|autonomous improve|run improve loop)(?:\s+for)?\s*:?\s*(\d+)?",
    re.I,
)
_JARVIS_SELF_HINTS = (
    "your code",
    "your own code",
    "jarvis-core",
    "william agent",
    "improve yourself",
    "fix yourself",
    "self-modify",
    "self modify",
    "change yourself",
)


def looks_like_self_modify(text: str) -> bool:
    stripped = text.strip()
    if SELF_MODIFY_PREFIX.match(stripped):
        return True
    lowered = stripped.lower()
    if not any(hint in lowered for hint in _JARVIS_SELF_HINTS):
        return False
    return any(
        kw in lowered
        for kw in ("fix", "add", "change", "update", "improve", "refactor", "implement", "remove")
    )


def extract_description(text: str) -> str:
    stripped = text.strip()
    match = SELF_MODIFY_PREFIX.match(stripped)
    if match:
        return stripped[match.end():].strip() or stripped
    return stripped


def looks_like_improve_run(text: str) -> bool:
    return bool(IMPROVE_RUN_PREFIX.match(text.strip()))


def improve_run_minutes(text: str, *, default: int = 30) -> int:
    match = IMPROVE_RUN_PREFIX.match(text.strip())
    if not match:
        return default
    raw = (match.group(1) or "").strip()
    if not raw:
        return default
    try:
        return max(5, min(180, int(raw)))
    except ValueError:
        return default


def _run_git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or settings.workspace_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def ensure_repo() -> None:
    root = settings.workspace_dir
    if (root / ".git").exists():
        return
    _run_git("init", cwd=root)
    _run_git("config", "user.email", "william@jarvis.local", cwd=root)
    _run_git("config", "user.name", "William Agent", cwd=root)
    _run_git("checkout", "-b", "main", cwd=root)
    _run_git("add", ".", cwd=root)
    commit = _run_git("commit", "-m", "Initial JarvisCore snapshot", cwd=root)
    if commit.returncode != 0:
        _run_git("commit", "--allow-empty", "-m", "Initial JarvisCore snapshot", cwd=root)


def current_branch() -> str:
    result = _run_git("branch", "--show-current")
    return (result.stdout or "").strip() or "unknown"


async def status() -> dict:
    ensure_repo()
    branch = current_branch()
    diff = _run_git("diff", "--stat", "main...HEAD") if branch.startswith("sandbox/") else _run_git("diff", "--stat")
    return {
        "branch": branch,
        "on_sandbox": branch.startswith(SANDBOX_PREFIX),
        "diff_stat": (diff.stdout or diff.stderr or "").strip(),
    }


async def propose(description: str) -> dict:
    ensure_repo()
    branch = f"{SANDBOX_PREFIX}{datetime.now():%Y%m%d-%H%M%S}"
    base = current_branch()
    if base != "main":
        _run_git("checkout", "main")

    checkout = _run_git("checkout", "-b", branch)
    if checkout.returncode != 0:
        return {"ok": False, "error": checkout.stderr or "failed to create branch"}

    prompt = (
        f"You are improving William Agent (JarvisCore) at {settings.workspace_dir}. "
        f"Task: {description}\n"
        "Only edit files inside this repo. Keep changes minimal and working. "
        "Do not touch secrets or system paths outside the repo."
    )
    result = await cursor_agent.run(prompt, cwd=str(settings.workspace_dir))
    diff = _run_git("diff", "--stat")
    stat = await status()

    if not result.get("ok"):
        return {
            "ok": False,
            "branch": branch,
            "error": result.get("error"),
            "status": stat,
        }

    if await security.is_full_access():
        merge = await merge_sandbox(branch)
        return {
            "ok": merge.get("ok", False),
            "branch": branch,
            "diff": (diff.stdout or "").strip(),
            "merged": merge,
            "auto_executed": True,
            "cursor_status": result.get("status"),
            "status": stat,
        }

    approval = await approvals.request_approval(
        action="self_modify_merge",
        detail=f"Merge sandbox branch {branch}: {description}",
    )
    return {
        "ok": True,
        "branch": branch,
        "diff": (diff.stdout or "").strip(),
        "approval_id": approval["id"],
        "cursor_status": result.get("status"),
        "status": stat,
    }


async def run_tests() -> dict:
    python = venv_python()
    proc = await asyncio.create_subprocess_exec(
        str(python),
        "-m",
        "pytest",
        "tests/",
        "-q",
        "--tb=line",
        cwd=settings.workspace_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode()
    err = stderr.decode()
    ok = proc.returncode == 0
    return {
        "ok": ok,
        "stdout": out,
        "stderr": err,
        "summary": (out or err).strip().splitlines()[-1] if (out or err).strip() else "",
    }


async def merge_sandbox(branch: str | None = None) -> dict:
    ensure_repo()
    target = branch or current_branch()
    if not target.startswith(SANDBOX_PREFIX):
        return {"ok": False, "error": "not on a sandbox branch"}

    tests = await run_tests()
    if not tests["ok"]:
        return {"ok": False, "error": "tests failed", "tests": tests}

    _run_git("checkout", "main")
    merge = _run_git("merge", "--no-ff", target, "-m", f"Merge {target} via approval")
    if merge.returncode != 0:
        return {"ok": False, "error": merge.stderr or "merge failed"}

    pushed = None
    try:
        from jarvis.services import github_sync, state_export

        if github_sync.configured():
            pushed = await state_export.export_all()
    except Exception:
        pushed = None

    return {"ok": True, "merged": target, "tests": tests, "github_sync": pushed}
