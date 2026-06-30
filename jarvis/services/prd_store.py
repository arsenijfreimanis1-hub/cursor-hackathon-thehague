"""Living PRD and variable registry for multi-agent builds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.config import settings

PRD_FILENAME = "PRD.md"
REGISTRY_FILENAME = "registry.json"
SLICES_FILENAME = "slices.json"
TRANSCRIPT_FILENAME = "transcript.md"
COMPREHENSION_FILENAME = "comprehension.json"


def build_artifact_dir(build_id: int) -> Path:
    path = settings.data_dir / "builds" / str(build_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / "worktrees").mkdir(exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    return path


def slices_path(build_id: int) -> Path:
    return build_artifact_dir(build_id) / SLICES_FILENAME


def prd_path(build_id: int) -> Path:
    return build_artifact_dir(build_id) / PRD_FILENAME


def registry_path(build_id: int) -> Path:
    return build_artifact_dir(build_id) / REGISTRY_FILENAME


def transcript_path(build_id: int) -> Path:
    return build_artifact_dir(build_id) / TRANSCRIPT_FILENAME


def comprehension_path(build_id: int) -> Path:
    return build_artifact_dir(build_id) / COMPREHENSION_FILENAME


def load_slices(build_id: int) -> list[dict[str, Any]]:
    path = slices_path(build_id)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_slices(build_id: int, slices: list[dict[str, Any]]) -> None:
    slices_path(build_id).write_text(
        json.dumps(slices, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_registry(build_id: int) -> dict[str, Any]:
    path = registry_path(build_id)
    if not path.is_file():
        return {"version": 1, "entries": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "entries" not in data:
        data = {"version": data.get("version", 1), "entries": data}
    return data


def save_registry(build_id: int, registry: dict[str, Any]) -> None:
    registry_path(build_id).write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def bump_registry_version(build_id: int) -> int:
    registry = load_registry(build_id)
    registry["version"] = int(registry.get("version", 1)) + 1
    save_registry(build_id, registry)
    return registry["version"]


def merge_registry_entries(build_id: int, new_entries: dict[str, Any]) -> int:
    registry = load_registry(build_id)
    entries = registry.setdefault("entries", {})
    for name, meta in new_entries.items():
        if isinstance(meta, dict):
            entries[name] = {**entries.get(name, {}), **meta}
        else:
            entries[name] = {"type": str(meta)}
    registry["version"] = int(registry.get("version", 1)) + 1
    save_registry(build_id, registry)
    return registry["version"]


def load_prd(build_id: int) -> str:
    path = prd_path(build_id)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def save_prd(build_id: int, content: str) -> None:
    prd_path(build_id).write_text(content, encoding="utf-8")


def save_transcript(build_id: int, prompt: str, *, history: str = "") -> None:
    body = f"# Transcript\n\n{prompt.strip()}\n"
    if history.strip():
        body += f"\n## Conversation context\n\n{history.strip()}\n"
    transcript_path(build_id).write_text(body, encoding="utf-8")


def load_transcript_prompt(build_id: int) -> str:
    path = transcript_path(build_id)
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if text.startswith("# Transcript"):
        text = text.split("\n", 2)[-1]
    return text.strip()


def save_comprehension(build_id: int, intake: dict[str, Any]) -> None:
    comprehension_path(build_id).write_text(
        json.dumps(intake, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_comprehension(build_id: int) -> dict[str, Any]:
    path = comprehension_path(build_id)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _registry_markdown(registry: dict[str, Any]) -> str:
    entries = registry.get("entries") or {}
    if not entries:
        return "_No registry entries yet._\n"
    lines = ["| Name | Type | File | Notes |", "|------|------|------|-------|"]
    for name, meta in sorted(entries.items()):
        if not isinstance(meta, dict):
            meta = {"type": str(meta)}
        lines.append(
            f"| `{name}` | {meta.get('type', '')} | {meta.get('file', '')} | {meta.get('notes', '')} |"
        )
    return "\n".join(lines) + "\n"


def _slice_contracts_markdown(slices: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for sl in slices:
        sid = sl.get("id", "")
        lines.append(f"### {sid}: {sl.get('title', '')}")
        lines.append(f"- **Prompt:** {sl.get('prompt', '')}")
        deps = sl.get("deps") or []
        if deps:
            lines.append(f"- **Depends on:** {', '.join(deps)}")
        files = sl.get("files") or []
        if files:
            lines.append(f"- **Files:** {', '.join(files)}")
        criteria = sl.get("acceptance_criteria") or []
        if criteria:
            lines.append("- **Acceptance criteria:**")
            for c in criteria:
                lines.append(f"  - {c}")
        lines.append("")
    return "\n".join(lines)


def generate_prd(
    build_id: int,
    *,
    prompt: str,
    slices: list[dict[str, Any]],
    stack: dict[str, Any] | None = None,
    feedback: str = "",
) -> tuple[str, dict[str, Any]]:
    """Draft PRD.md and seed registry from slices."""
    stack = stack or _infer_stack(slices, prompt)
    registry = load_registry(build_id)
    entries = registry.setdefault("entries", {})

    for sl in slices:
        for name in sl.get("registry_hints") or []:
            if name not in entries:
                entries[name] = {
                    "type": "pending",
                    "file": (sl.get("files") or [""])[0] if sl.get("files") else "",
                    "slice": sl.get("id", ""),
                }

    registry["version"] = int(registry.get("version", 1))
    save_registry(build_id, registry)

    product_summary = prompt.strip()[:2000]
    stack_lines = "\n".join(f"- **{k}:** {v}" for k, v in stack.items())

    prd = f"""# Product Requirements Document

**Build ID:** {build_id}
**PRD Version:** {registry['version']}

## 1. Product summary

{product_summary}

## 2. Tech stack (locked)

{stack_lines}

## 3. Architecture

```mermaid
flowchart TB
  subgraph slices [Implementation slices]
"""
    for sl in slices:
        prd += f"    {sl.get('id', 'slice').replace('-', '_')}[{sl.get('title', '')[:40]}]\n"
    prd += """  end
```

## 4. Variable registry

"""
    prd += _registry_markdown(registry)
    prd += """
## 5. Slice contracts

"""
    prd += _slice_contracts_markdown(slices)
    prd += """
## 6. Integration checklist

- [ ] All slices merged to integration branch
- [ ] Project builds without errors
- [ ] Tests pass
- [ ] Registry names used consistently across files
"""
    if feedback.strip():
        prd += f"\n## Revision notes\n\n{feedback.strip()}\n"

    save_prd(build_id, prd)
    return prd, registry


def _infer_stack(slices: list[dict[str, Any]], prompt: str) -> dict[str, str]:
    from jarvis.services import skill_domains

    blob = (prompt + " " + " ".join(sl.get("prompt", "") for sl in slices)).lower()
    domains = skill_domains.detect_domains(blob, always_include_gsd=False)
    stack: dict[str, str] = {"language": "python", "runtime": "local"}
    stack.update(skill_domains.stack_hints_for_domains(domains))
    if any(k in blob for k in ("react", "next.js", "nextjs", "typescript", "frontend")):
        stack["frontend"] = "react"
        stack["language"] = "typescript"
    if any(k in blob for k in ("fastapi", "api", "backend")):
        stack["backend"] = "fastapi"
    if any(k in blob for k in ("postgres", "sqlite", "database")):
        stack["database"] = "sqlite"
    if "node" in blob or "npm" in blob:
        stack["package_manager"] = "npm"
    return stack


def prd_context_for_slice(build_id: int, slice_id: str, *, max_chars: int = 12000) -> str:
    """PRD excerpt + registry for agent prompts."""
    prd = load_prd(build_id)
    registry = load_registry(build_id)
    slices = load_slices(build_id)
    sl = next((s for s in slices if s.get("id") == slice_id), None)

    parts = [
        f"PRD (v{registry.get('version', 1)}):\n{prd[:max_chars // 2]}",
        f"Variable registry (use exact names):\n{json.dumps(registry.get('entries', {}), indent=2)[:max_chars // 3]}",
    ]
    if sl:
        parts.append(f"Your slice contract:\n{json.dumps(sl, indent=2)[:max_chars // 4]}")
    return "\n\n".join(parts)[:max_chars]


def parse_new_registry_entries(agent_result: str) -> dict[str, Any]:
    """Extract NEW_REGISTRY_ENTRIES JSON block from agent output."""
    marker = "NEW_REGISTRY_ENTRIES"
    if marker not in agent_result:
        return {}
    start = agent_result.find("{", agent_result.find(marker))
    end = agent_result.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(agent_result[start:end])
        if isinstance(parsed, dict):
            return parsed.get("entries", parsed)
    except json.JSONDecodeError:
        pass
    return {}
