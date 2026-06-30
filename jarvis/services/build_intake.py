"""Full read-through comprehension before decomposition."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from jarvis.config import settings
from jarvis.services import cursor_agent, ollama, prd_store

log = logging.getLogger("jarvis.build_intake")

PromptClass = Literal["blueprint", "implementation", "hybrid"]

_BLUEPRINT_MARKERS = (
    "part 1",
    "what you must produce",
    "user flows",
    "data model",
    "mvp vs",
    "prd",
    "product architect",
    "implementation plan",
    "workstream",
    "state machine",
    "go-to-market",
)

_IMPLEMENTATION_MARKERS = (
    "scaffold",
    "implement",
    "create app",
    "build api",
    "write tests",
    "npm install",
    "repository structure",
)

_PART_HEADER_RE = re.compile(
    r"^PART\s+(\d+)\s*[—\-–:]\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def extract_explicit_parts(prompt: str) -> list[dict[str, Any]]:
    """Parse PART N — TITLE sections from structured master prompts."""
    matches = list(_PART_HEADER_RE.finditer(prompt))
    if len(matches) < 2:
        return []

    parts: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
        body = prompt[start:end].strip()
        part_num = int(match.group(1))
        title = match.group(2).strip()
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        summary = " ".join(lines[:10])[:2000]
        requirements = [ln.lstrip("-•* ").strip() for ln in lines if ln.startswith(("-", "•", "*"))][:12]
        parts.append({
            "id": f"part-{part_num}",
            "title": f"PART {part_num} — {title}",
            "summary": summary,
            "requirements": requirements,
            "deliverables": [],
        })
    return parts


def _merge_identified_parts(
    ai_parts: list[dict[str, Any]],
    explicit_parts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prefer explicit PART headers; enrich with AI summaries where available."""
    if not explicit_parts:
        return ai_parts

    explicit_by_id = {p["id"]: p for p in explicit_parts}
    ai_by_id = {p["id"]: p for p in ai_parts}

    if len(ai_parts) >= len(explicit_parts):
        merged: list[dict[str, Any]] = []
        for part in ai_parts:
            explicit = explicit_by_id.get(part.get("id", ""), {})
            merged.append({**explicit, **part})
        seen = {p["id"] for p in merged}
        for explicit in explicit_parts:
            if explicit["id"] not in seen:
                merged.append(explicit)
        return merged[:24]

    merged = []
    for explicit in explicit_parts:
        ai = ai_by_id.get(explicit["id"], {})
        merged.append({**explicit, **{k: v for k, v in ai.items() if v}})
    return merged[:24]


def classify_prompt(prompt: str) -> PromptClass:
    """Detect whether this is a product blueprint, code build, or both."""
    lowered = prompt.lower()
    blueprint_score = sum(1 for m in _BLUEPRINT_MARKERS if m in lowered)
    impl_score = sum(1 for m in _IMPLEMENTATION_MARKERS if m in lowered)

    if len(prompt) > 4000 or re.search(r"\bpart\s+\d+", lowered):
        blueprint_score += 3
    if blueprint_score >= 3 and impl_score >= 2:
        return "hybrid"
    if blueprint_score >= 2:
        return "blueprint"
    return "implementation"


def _parse_intake_json(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start:end])
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _normalize_intake(raw: dict[str, Any], prompt: str) -> dict[str, Any]:
    prompt_class = raw.get("prompt_class") or classify_prompt(prompt)
    parts = raw.get("identified_parts") or raw.get("parts") or []
    if not isinstance(parts, list):
        parts = []

    normalized_parts: list[dict[str, Any]] = []
    for i, part in enumerate(parts[:24]):
        if not isinstance(part, dict):
            continue
        normalized_parts.append({
            "id": str(part.get("id") or f"part-{i + 1}"),
            "title": str(part.get("title", ""))[:200],
            "summary": str(part.get("summary", ""))[:2000],
            "requirements": [str(r) for r in (part.get("requirements") or [])][:12],
            "deliverables": [str(d) for d in (part.get("deliverables") or [])][:8],
        })

    explicit_parts = extract_explicit_parts(prompt)
    normalized_parts = _merge_identified_parts(normalized_parts, explicit_parts)

    workstreams = raw.get("parallel_workstreams") or raw.get("workstreams") or []
    if not isinstance(workstreams, list):
        workstreams = []

    return {
        "prompt_class": prompt_class,
        "one_line_pitch": str(raw.get("one_line_pitch") or raw.get("pitch") or "")[:300],
        "product_summary": str(raw.get("product_summary") or raw.get("summary") or "")[:4000],
        "core_problem": str(raw.get("core_problem") or "")[:1000],
        "target_users": [str(u) for u in (raw.get("target_users") or [])][:8],
        "mvp_scope": str(raw.get("mvp_scope") or "")[:2000],
        "post_mvp": str(raw.get("post_mvp") or "")[:2000],
        "do_not_build_yet": [str(x) for x in (raw.get("do_not_build_yet") or [])][:12],
        "tech_stack": raw.get("tech_stack") if isinstance(raw.get("tech_stack"), dict) else {},
        "risks": [str(r) for r in (raw.get("risks") or [])][:15],
        "assumptions": [str(a) for a in (raw.get("assumptions") or [])][:15],
        "open_questions": [str(q) for q in (raw.get("open_questions") or [])][:15],
        "identified_parts": normalized_parts,
        "parallel_workstreams": workstreams[:6],
        "decomposition_strategy": str(raw.get("decomposition_strategy") or "")[:1500],
    }


def _comprehend_prompt(prompt: str, *, history: str = "", prompt_class: PromptClass) -> str:
    class_note = {
        "blueprint": (
            "This is a PRODUCT BLUEPRINT request — not a shallow code scaffold. "
            "Read every section. Identify all PARTs/sections. Map MVP vs post-MVP. "
            "Capture payment, legal, fraud, and ops constraints."
        ),
        "implementation": (
            "This is an IMPLEMENTATION request. Identify modules, dependencies, and file ownership."
        ),
        "hybrid": (
            "This is a HYBRID request: exhaustive product blueprint PLUS implementation plan. "
            "Read the full document first, then identify blueprint deliverables and code workstreams."
        ),
    }[prompt_class]

    body = f"{class_note}\n\n"
    if history.strip():
        body += f"Conversation context:\n{history.strip()}\n\n"
    body += (
        "MASTER PROMPT (read in full — do not skim):\n"
        f"{'=' * 40}\n"
        f"{prompt}\n"
        f"{'=' * 40}\n\n"
        "Produce a comprehension brief as JSON only:\n"
        "{\n"
        '  "prompt_class": "blueprint|implementation|hybrid",\n'
        '  "one_line_pitch": "...",\n'
        '  "product_summary": "2-4 paragraphs showing you understood the full idea",\n'
        '  "core_problem": "...",\n'
        '  "target_users": ["..."],\n'
        '  "mvp_scope": "ruthless MVP boundary",\n'
        '  "post_mvp": "what comes after MVP",\n'
        '  "do_not_build_yet": ["things to explicitly defer"],\n'
        '  "tech_stack": {"frontend": "...", "backend": "...", "database": "..."},\n'
        '  "risks": ["legal, fraud, ops, technical risks"],\n'
        '  "assumptions": ["weak assumptions to challenge"],\n'
        '  "open_questions": ["founder decisions needed"],\n'
        '  "identified_parts": [\n'
        '    {"id": "part-1", "title": "...", "summary": "...", "requirements": ["..."], "deliverables": ["..."]}\n'
        "  ],\n"
        '  "parallel_workstreams": [\n'
        '    {"id": "ws-1", "name": "...", "scope": "...", "owned_areas": ["..."], "depends_on": []}\n'
        "  ],\n"
        '  "decomposition_strategy": "how to split into parallel slices without collisions"\n'
        "}\n"
        "Be concrete. Challenge weak ideas. Separate MVP from fantasy."
    )
    return body


async def comprehend(
    prompt: str,
    *,
    build_id: int | None = None,
    history: str = "",
) -> dict[str, Any]:
    """
    Full read-through of the master prompt before any decomposition.
    Stores result to comprehension.json when build_id is provided.
    """
    prompt = prompt.strip()
    if not prompt:
        return {}

    prompt_class = classify_prompt(prompt)
    comprehend_text = _comprehend_prompt(prompt, history=history, prompt_class=prompt_class)
    intake: dict[str, Any] = {}

    if settings.cursor_configured():
        try:
            result = await cursor_agent.run(
                comprehend_text,
                cwd=str(settings.workspace_dir),
                handle_popups=False,
                trace=True,
                source="build_intake",
            )
            if result.get("ok"):
                intake = _normalize_intake(_parse_intake_json(result.get("result", "")), prompt)
        except Exception as exc:
            log.warning("cursor comprehend failed: %s", exc)

    if not intake.get("product_summary"):
        try:
            raw = await ollama.chat(
                comprehend_text,
                system="You comprehend complex product and engineering prompts. Reply with JSON only.",
            )
            intake = _normalize_intake(_parse_intake_json(raw), prompt)
        except Exception as exc:
            log.warning("ollama comprehend failed: %s", exc)

    if not intake.get("product_summary"):
        explicit = extract_explicit_parts(prompt)
        intake = _normalize_intake({
            "prompt_class": prompt_class,
            "product_summary": prompt[:3000],
            "identified_parts": explicit,
            "decomposition_strategy": (
                f"Split into {len(explicit)} slices aligned to explicit PART sections."
                if explicit
                else "Split by major sections in the master prompt."
            ),
        }, prompt)

    intake["prompt_class"] = intake.get("prompt_class") or prompt_class
    intake["prompt_length"] = len(prompt)

    if build_id is not None:
        prd_store.save_comprehension(build_id, intake)

    return intake


def intake_summary_for_prompt(intake: dict[str, Any], *, max_chars: int = 8000) -> str:
    """Compact intake brief for downstream agents."""
    if not intake:
        return ""
    parts = [
        f"Prompt class: {intake.get('prompt_class', 'unknown')}",
        f"Pitch: {intake.get('one_line_pitch', '')}",
        f"Summary:\n{intake.get('product_summary', '')}",
        f"MVP scope:\n{intake.get('mvp_scope', '')}",
        f"Do NOT build yet: {', '.join(intake.get('do_not_build_yet') or [])}",
    ]
    risks = intake.get("risks") or []
    if risks:
        parts.append("Risks:\n" + "\n".join(f"- {r}" for r in risks[:8]))
    open_q = intake.get("open_questions") or []
    if open_q:
        parts.append("Open questions:\n" + "\n".join(f"- {q}" for q in open_q[:8]))
    strategy = intake.get("decomposition_strategy", "")
    if strategy:
        parts.append(f"Decomposition strategy:\n{strategy}")
    text = "\n\n".join(p for p in parts if p.strip())
    return text[:max_chars]
