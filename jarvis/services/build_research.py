"""Per-slice deep dive research for build pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from jarvis.config import settings
from jarvis.services import build_intake, cursor_agent, prd_store, web

log = logging.getLogger("jarvis.build_research")

_PARALLEL = 4


def _parse_research(text: str, title: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    options: list[dict[str, str]] = []
    for i, line in enumerate(lines[:6]):
        if len(line) < 12:
            continue
        options.append({"name": f"option-{i + 1}", "summary": line[:400]})
    if not options and text.strip():
        options = [{"name": "analysis", "summary": text.strip()[:600]}]
    recommendation = options[0]["summary"][:400] if options else f"Implement {title} using project stack"
    return {
        "options": options[:3],
        "recommendation": recommendation,
        "raw": text[:8000],
        "deep_dive": True,
    }


async def _deep_dive_slice(
    slice_item: dict,
    *,
    intake: dict[str, Any],
    master_prompt: str,
) -> dict:
    """Cursor-powered deep dive per slice — not shallow web search."""
    title = slice_item.get("title", "")
    slice_type = slice_item.get("slice_type", "implementation")
    intake_block = build_intake.intake_summary_for_prompt(intake, max_chars=4000)

    dive_prompt = (
        f"You are doing a DEEP DIVE on one workstream of a master product blueprint.\n\n"
        f"COMPREHENSION (from full read-through):\n{intake_block}\n\n"
        f"YOUR SLICE: {title}\n"
        f"SLICE TYPE: {slice_type}\n"
        f"SOURCE PARTS: {', '.join(slice_item.get('source_parts') or []) or 'see slice prompt'}\n\n"
        f"SLICE SCOPE:\n{slice_item.get('prompt', '')}\n\n"
        f"ACCEPTANCE CRITERIA:\n"
        + "\n".join(f"- {c}" for c in (slice_item.get("acceptance_criteria") or []))
        + "\n\n"
        "Requirements:\n"
        "- Be exhaustive and concrete — no generic brainstorming\n"
        "- Include tables, state machines, examples with numbers where relevant\n"
        "- Challenge weak assumptions from the master prompt\n"
        "- Separate MVP from post-MVP clearly\n"
        "- Flag legal, fraud, UX, and ops risks specific to this slice\n"
        "- If payment/billing slice: include Mollie + crypto architecture explicitly\n"
        "- Output as structured markdown ready to save as a doc artifact\n\n"
        f"MASTER PROMPT EXCERPT (for cross-reference):\n{master_prompt[:6000]}"
    )

    if settings.cursor_configured():
        try:
            result = await cursor_agent.run(
                dive_prompt,
                cwd=str(settings.workspace_dir),
                handle_popups=False,
                trace=True,
                source="build_deep_dive",
            )
            if result.get("ok") and result.get("result"):
                research = _parse_research(result["result"], title)
                research["analysis"] = result["result"][:12000]
                return {**slice_item, "research": research, "deep_dive": {"status": "complete"}}
        except Exception as exc:
            log.warning("deep dive failed for %s: %s", title, exc)

    query = f"{title} {slice_item.get('prompt', '')[:200]} best practices MVP"
    try:
        result = await web.research(query, depth=3)
        text = result.get("text", "")
    except Exception as exc:
        log.warning("web research fallback failed for %s: %s", title, exc)
        text = ""
    research = _parse_research(text, title)
    return {**slice_item, "research": research, "deep_dive": {"status": "web_fallback"}}


async def _research_one(slice_item: dict, stack_hint: str = "") -> dict:
    title = slice_item.get("title", "")
    query = f"{title} implementation approaches {stack_hint} {slice_item.get('prompt', '')[:120]}"
    try:
        result = await web.research(query, depth=2)
        text = result.get("text", "")
    except Exception as exc:
        log.warning("research failed for %s: %s", title, exc)
        text = ""
    research = _parse_research(text, title)
    return {**slice_item, "research": research}


async def research_slices(
    slices: list[dict],
    *,
    stack_hint: str = "",
    parallel: int | None = None,
    intake: dict[str, Any] | None = None,
    master_prompt: str = "",
    build_id: int | None = None,
) -> list[dict]:
    """Deep dive each slice in parallel (capped for quality)."""
    if not slices:
        return []

    if intake is None and build_id is not None:
        intake = prd_store.load_comprehension(build_id)
    if not master_prompt and build_id is not None:
        master_prompt = prd_store.load_transcript_prompt(build_id)

    prompt_class = (intake or {}).get("prompt_class", "implementation")
    use_deep_dive = prompt_class in ("blueprint", "hybrid") or len(master_prompt) > 3000

    cap = parallel or min(getattr(settings, "build_parallel", 3), _PARALLEL)
    sem = asyncio.Semaphore(cap)

    async def _run(sl: dict) -> dict:
        async with sem:
            if use_deep_dive and intake:
                return await _deep_dive_slice(sl, intake=intake, master_prompt=master_prompt)
            return await _research_one(sl, stack_hint)

    return list(await asyncio.gather(*[_run(sl) for sl in slices]))
