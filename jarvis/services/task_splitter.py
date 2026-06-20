import json
import re

from jarvis.config import settings
from jarvis.services import cursor_agent, ollama

_SPLIT_MARKERS = re.compile(
    r"\s+and then\s+|\s+then\s+|\s+also\s+|\s+after that\s+|\s+;\s+|\s+\band\b\s+",
    re.I,
)
_MULTI_HINT = re.compile(
    r"\b(and then|also|first|second|third|next|after that|as well as|plus)\b",
    re.I,
)
_NUMBERED_LINE = re.compile(r"^\s*\d+[\).\]]\s+", re.M)


def _clean_part(text: str) -> str:
    return re.sub(r"^\d+[\).\]]\s*", "", text.strip()).strip(" ,.")


def _heuristic_split(text: str) -> list[str]:
    parts = [text]
    for _ in range(4):
        expanded: list[str] = []
        changed = False
        for part in parts:
            sub = [_clean_part(p) for p in _SPLIT_MARKERS.split(part) if _clean_part(p)]
            if len(sub) > 1:
                expanded.extend(sub)
                changed = True
            else:
                expanded.append(part)
        parts = expanded
        if not changed:
            break

    if len(parts) >= 2 and all(len(p) >= 4 for p in parts):
        return parts[:6]

    lines = [_clean_part(line) for line in text.splitlines() if _clean_part(line)]
    if len(lines) >= 2 and all(len(line) >= 4 for line in lines):
        return lines[:6]

    if text.count(",") >= 2:
        comma_parts = [_clean_part(p) for p in text.split(",") if _clean_part(p)]
        if len(comma_parts) >= 2 and all(len(p) >= 6 for p in comma_parts):
            return comma_parts[:6]

    return []


def looks_compound(text: str) -> bool:
    """Fast check — skip Ollama split for simple single commands."""
    text = text.strip()
    if len(text) < 14:
        return False
    return bool(_MULTI_HINT.search(text)) or text.count(",") >= 2 or bool(_NUMBERED_LINE.search(text))


async def split_prompt(text: str) -> list[str]:
    """Split a compound prompt into separate executable tasks."""
    text = text.strip()
    if len(text) < 14:
        return [text]

    if not looks_compound(text):
        return [text]

    parts = _heuristic_split(text)
    if len(parts) >= 2:
        return parts

    if settings.cursor_configured():
        try:
            planned = await cursor_agent.plan_tasks(text)
            if len(planned) >= 2:
                return planned
        except Exception:
            pass

    try:
        raw = await ollama.chat(
            f'Prompt: "{text[:480]}"\n\n'
                "Split into separate actionable tasks. JSON array of strings only. "
                "Tasks may be reordered by speed (e.g. play music before building an app).",
            system=(
                "You split user requests into independent tasks. "
                'Reply ONLY with a JSON array like ["open Spotify","play liked songs"]. '
                "Max 5 tasks. Imperative phrases. No markdown."
            ),
        )
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            items = [_clean_part(str(item)) for item in parsed if _clean_part(str(item))]
            if len(items) >= 2:
                return items[:6]
    except Exception:
        pass

    return [text]
