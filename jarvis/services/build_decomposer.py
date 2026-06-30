"""Deep decomposition of build prompts into implementation slices."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from jarvis.config import settings
from jarvis.services import build_intake, cursor_agent, ollama, prd_store, skill_domains, skills

log = logging.getLogger("jarvis.build_decomposer")

MAX_SLICES = 24
MAX_SLICES_SIMPLE = 12


def _normalize_slice(raw: dict, ordinal: int, *, prompt_class: str = "implementation") -> dict:
    sid = raw.get("id") or f"slice-{ordinal}"
    sid = re.sub(r"[^a-zA-Z0-9_-]", "-", str(sid)).strip("-").lower()[:40]
    if not sid.startswith("slice-"):
        sid = f"slice-{sid}" if sid else f"slice-{ordinal}"
    slice_type = raw.get("slice_type") or ("blueprint" if prompt_class == "blueprint" else "implementation")
    return {
        "id": sid,
        "ordinal": ordinal,
        "title": str(raw.get("title", raw.get("prompt", ""))[:120]).strip(),
        "prompt": str(raw.get("prompt", raw.get("title", ""))).strip(),
        "deps": [str(d) for d in (raw.get("deps") or [])],
        "acceptance_criteria": [str(c) for c in (raw.get("acceptance_criteria") or [])][:8],
        "files": [str(f) for f in (raw.get("files") or [])][:20],
        "registry_hints": [str(n) for n in (raw.get("registry_hints") or [])][:12],
        "source_parts": [str(p) for p in (raw.get("source_parts") or [])][:6],
        "slice_type": slice_type,
        "research": raw.get("research") or {},
        "deep_dive": raw.get("deep_dive") or {},
        "status": "pending",
    }


def _parse_slices_json(raw: str, *, prompt_class: str = "implementation") -> list[dict]:
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start < 0 or end <= start:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return []
        try:
            parsed = json.loads(raw[start:end])
            items = parsed.get("slices", parsed) if isinstance(parsed, dict) else parsed
        except json.JSONDecodeError:
            return []
    else:
        try:
            items = json.loads(raw[start:end])
        except json.JSONDecodeError:
            return []
    if not isinstance(items, list):
        return []
    cap = MAX_SLICES if prompt_class in ("blueprint", "hybrid") else MAX_SLICES_SIMPLE
    return [
        _normalize_slice(item, i + 1, prompt_class=prompt_class)
        for i, item in enumerate(items[:cap])
        if isinstance(item, dict)
    ]


def _fallback_slices_from_intake(prompt: str, intake: dict[str, Any]) -> list[dict]:
    """Derive slices from identified parts when AI decomposition fails."""
    parts = intake.get("identified_parts") or []
    prompt_class = intake.get("prompt_class", "blueprint")
    if not parts:
        return _fallback_slices(prompt, prompt_class)

    slices: list[dict] = []
    prev_id: str | None = None
    for i, part in enumerate(parts[:MAX_SLICES]):
        sid = f"slice-{part.get('id', i + 1)}".lower().replace(" ", "-")[:40]
        deps = [prev_id] if prev_id and prompt_class == "hybrid" else []
        deliverables = part.get("deliverables") or []
        files = [f"docs/{part.get('id', i+1)}.md"] if prompt_class != "implementation" else []
        if deliverables:
            files = [str(d) for d in deliverables[:5]]

        slices.append(_normalize_slice({
            "id": sid,
            "title": part.get("title", f"Part {i + 1}"),
            "prompt": (
                f"Deep dive and produce exhaustive deliverables for: {part.get('title', '')}\n\n"
                f"Summary: {part.get('summary', '')}\n\n"
                f"Requirements:\n" + "\n".join(f"- {r}" for r in (part.get("requirements") or []))
            ),
            "deps": deps,
            "source_parts": [str(part.get("id", ""))],
            "slice_type": "blueprint" if prompt_class != "implementation" else "implementation",
            "acceptance_criteria": [
                "Concrete output — no generic brainstorming",
                "MVP vs post-MVP clearly separated",
                "Edge cases and failure states covered",
            ],
            "files": files,
        }, i + 1, prompt_class=prompt_class))
        prev_id = sid
    return slices


def _fallback_slices(prompt: str, prompt_class: str = "implementation") -> list[dict]:
    return [
        _normalize_slice(
            {
                "id": "slice-1",
                "title": "Implement project",
                "prompt": prompt,
                "deps": [],
                "acceptance_criteria": ["Project runs without errors", "Core requirements implemented"],
            },
            1,
            prompt_class=prompt_class,
        )
    ]


def _decompose_prompt(
    prompt: str,
    intake: dict[str, Any],
    *,
    history: str = "",
) -> str:
    prompt_class = intake.get("prompt_class") or build_intake.classify_prompt(prompt)
    intake_block = build_intake.intake_summary_for_prompt(intake)
    parts_json = json.dumps(intake.get("identified_parts") or [], indent=2)[:6000]
    workstreams = json.dumps(intake.get("parallel_workstreams") or [], indent=2)[:3000]

    domains = skill_domains.detect_domains(prompt, always_include_gsd=True)
    gsd_block = skills.load_skills_block(domains=["gsd"], include_external=False)

    body = "You have already read and comprehended the master prompt.\n\n"
    if intake_block:
        body += f"COMPREHENSION BRIEF:\n{intake_block}\n\n"
    if parts_json.strip() not in ("[]", ""):
        body += f"IDENTIFIED PARTS:\n{parts_json}\n\n"
    if workstreams.strip() not in ("[]", ""):
        body += f"PARALLEL WORKSTREAMS:\n{workstreams}\n\n"
    if history.strip():
        body += f"Conversation context:\n{history[:2000]}\n\n"
    if gsd_block:
        body += f"{gsd_block}\n\n"

    if prompt_class in ("blueprint", "hybrid"):
        body += (
            "Decompose into parallel WORKSTREAM SLICES aligned to the identified parts.\n"
            "Each slice = one deep-dive workstream that produces concrete blueprint artifacts.\n"
            "Rules:\n"
            "- Map slices to source PARTs from the master prompt (use source_parts field)\n"
            "- Each slice prompt must restate the specific deliverables expected\n"
            "- Disjoint file/doc ownership — no collisions between slices\n"
            "- Order: product framing → core logic → architecture → GTM/legal → repo plan → roadmap\n"
            "- slice_type: 'blueprint' for docs/analysis, 'implementation' for code\n"
            "- For hybrid: final slices can be implementation scaffolds that depend on blueprint slices\n"
            f"- Target {min(len(intake.get('identified_parts') or []) or 8, MAX_SLICES)} slices for thorough coverage\n"
        )
    else:
        body += (
            "Decompose into 3-12 implementation slices for parallel development.\n"
            "Each slice must be independently implementable with clear file ownership.\n"
            "Order: scaffold → domain work → integration. Lock tech stack in slice 1.\n"
        )

    body += (
        "Reply ONLY with JSON array of objects:\n"
        '[{"id":"slice-product","title":"...","prompt":"detailed scope...",'
        '"deps":[],"source_parts":["part-1"],"slice_type":"blueprint",'
        '"acceptance_criteria":["..."],"files":["docs/..."],"registry_hints":["Name"]}]\n'
        "Use consistent naming. Dependencies must reference exact slice ids.\n\n"
        "MASTER PROMPT (full text for reference):\n"
        f"{prompt}"
    )
    return body


async def decompose(
    prompt: str,
    *,
    history: str = "",
    intake: dict[str, Any] | None = None,
    build_id: int | None = None,
) -> list[dict]:
    """Split a build prompt into structured slices after comprehension."""
    prompt = prompt.strip()
    if not prompt:
        return []

    if build_id is not None:
        stored = prd_store.load_transcript_prompt(build_id)
        if stored and len(stored) > len(prompt):
            prompt = stored

    if intake is None and build_id is not None:
        intake = prd_store.load_comprehension(build_id)
    if not intake:
        intake = await build_intake.comprehend(prompt, build_id=build_id, history=history)

    prompt_class = intake.get("prompt_class", build_intake.classify_prompt(prompt))
    system_prompt = _decompose_prompt(prompt, intake, history=history)

    slices: list[dict] = []
    if settings.cursor_configured():
        try:
            result = await cursor_agent.run(
                system_prompt,
                cwd=str(settings.workspace_dir),
                handle_popups=False,
                trace=True,
                source="build_decomposer",
            )
            if result.get("ok"):
                slices = _parse_slices_json(result.get("result", ""), prompt_class=prompt_class)
        except Exception as exc:
            log.warning("cursor decompose failed: %s", exc)

    if len(slices) < 2:
        try:
            raw = await ollama.chat(
                system_prompt[:12000] + "\nReply ONLY JSON array of slice objects.",
                system="You decompose complex product blueprints into parallel workstream slices. JSON only.",
            )
            slices = _parse_slices_json(raw, prompt_class=prompt_class)
        except Exception as exc:
            log.warning("ollama decompose failed: %s", exc)

    if len(slices) < 2:
        slices = _fallback_slices_from_intake(prompt, intake)

    seen: set[str] = set()
    for sl in slices:
        base = sl["id"]
        n = 2
        while sl["id"] in seen:
            sl["id"] = f"{base}-{n}"
            n += 1
        seen.add(sl["id"])

    return slices
