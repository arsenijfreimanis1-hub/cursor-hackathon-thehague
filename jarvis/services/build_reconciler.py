"""Cross-slice consistency pass for build pipeline."""

from __future__ import annotations

import json
import logging
from typing import Any

from jarvis.config import settings
from jarvis.services import build_intake, cursor_agent, ollama, prd_store

log = logging.getLogger("jarvis.build_reconciler")


def _parse_reconciled(raw: str, original: list[dict]) -> list[dict]:
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start < 0 or end <= start:
        return original
    try:
        parsed = json.loads(raw[start:end])
    except json.JSONDecodeError:
        return original
    if not isinstance(parsed, list) or not parsed:
        return original

    by_id = {sl["id"]: sl for sl in original}
    result: list[dict] = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        sid = item.get("id") or f"slice-{i + 1}"
        base = by_id.get(sid, original[min(i, len(original) - 1)])
        merged = {**base, **item}
        merged["research"] = base.get("research") or item.get("research") or {}
        merged["ordinal"] = i + 1
        merged["status"] = "pending"
        result.append(merged)
    return result if result else original


async def reconcile(
    prompt: str,
    slices: list[dict],
    *,
    intake: dict[str, Any] | None = None,
    build_id: int | None = None,
) -> list[dict]:
    """Ensure slices are consistent in naming, stack, and file ownership."""
    if not slices:
        return []

    if intake is None and build_id is not None:
        intake = prd_store.load_comprehension(build_id)
    if build_id is not None:
        stored = prd_store.load_transcript_prompt(build_id)
        if stored and len(stored) > len(prompt):
            prompt = stored

    intake_block = build_intake.intake_summary_for_prompt(intake or {}, max_chars=3000)

    summary = json.dumps(
        [
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "prompt": s.get("prompt"),
                "deps": s.get("deps"),
                "files": s.get("files"),
                "registry_hints": s.get("registry_hints"),
                "research": (s.get("research") or {}).get("recommendation", ""),
            }
            for s in slices
        ],
        indent=2,
    )[:8000]

    reconcile_prompt = (
        f'Original build request (full context preserved).\n\n'
    )
    if intake_block:
        reconcile_prompt += f"COMPREHENSION BRIEF:\n{intake_block}\n\n"
    reconcile_prompt += (
        f"Master prompt excerpt:\n{prompt[:4000]}\n\n"
        f"Proposed slices:\n{summary}\n\n"
        "Reconcile these slices for 100% consistency:\n"
        "- Every identified PART from comprehension must be covered by a slice\n"
        "- Resolve duplicate concepts and naming conflicts\n"
        "- Align tech stack across slices\n"
        "- Assign disjoint file/doc ownership (no two slices own the same file)\n"
        "- Fix dependency references to use exact slice ids\n"
        "- Ensure registry_hints use consistent canonical names\n"
        "- Blueprint slices must have concrete acceptance criteria, not vague goals\n"
        "Reply ONLY with the finalized JSON array of slice objects (same schema)."
    )

    if settings.cursor_configured():
        try:
            result = await cursor_agent.run(
                reconcile_prompt,
                cwd=str(settings.workspace_dir),
                handle_popups=False,
                trace=False,
                source="build_reconciler",
            )
            if result.get("ok"):
                return _parse_reconciled(result.get("result", ""), slices)
        except Exception as exc:
            log.warning("cursor reconcile failed: %s", exc)

    try:
        raw = await ollama.chat(
            reconcile_prompt,
            system="You reconcile software implementation plans. Reply with JSON array only.",
        )
        return _parse_reconciled(raw, slices)
    except Exception as exc:
        log.warning("ollama reconcile failed: %s", exc)
        return slices
