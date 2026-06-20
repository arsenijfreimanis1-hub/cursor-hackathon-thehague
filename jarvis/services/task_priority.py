"""Estimate task speed and sort compound plans — fast actions first."""

import re

from jarvis.services import intent

# Lower number = faster / runs sooner.
SPEED_TIERS: dict[str, int] = {
    "exit": 1,
    "cancel": 1,
    "time": 2,
    "system": 3,
    "remember": 4,
    "recall": 4,
    "chat": 5,
    "terminal": 6,
    "fact": 7,
    "reason": 8,
    "action": 9,
    "code": 10,
}

# Rough spoken ETA for planning replies.
ETA_SECONDS: dict[str, int] = {
    "exit": 1,
    "cancel": 1,
    "time": 1,
    "system": 3,
    "remember": 2,
    "recall": 2,
    "chat": 5,
    "terminal": 10,
    "fact": 20,
    "reason": 25,
    "action": 30,
    "code": 180,
}

IMMEDIATE_INTENTS = frozenset({"system", "time", "exit", "cancel", "remember", "recall", "terminal", "chat"})

_FIRST = re.compile(r"\bfirst\b", re.I)
_LAST = re.compile(
    r"\b(last|after that|finally|afterwards|at the end|when you(?:'re| are) done)\b",
    re.I,
)


def estimate_priority(text: str) -> tuple[int, str]:
    """Return (priority_score, intent) — lower score runs first."""
    kind = intent.classify(text)
    base = SPEED_TIERS.get(kind, 8)
    if _FIRST.search(text):
        base = 0
    elif _LAST.search(text):
        base = min(base + 6, 99)
    return base, kind


def eta_seconds(text: str) -> int:
    kind = intent.classify(text)
    return ETA_SECONDS.get(kind, 30)


def sort_by_speed(subtasks: list[str]) -> list[str]:
    """Stable sort: fastest estimated tasks first."""
    scored = [(estimate_priority(t)[0], i, t) for i, t in enumerate(subtasks)]
    scored.sort(key=lambda item: (item[0], item[1]))
    return [text for _, _, text in scored]


def split_immediate_deferred(subtasks: list[str]) -> tuple[list[str], list[str]]:
    """Split sorted subtasks into inline vs background work."""
    immediate: list[str] = []
    deferred: list[str] = []
    for text in sort_by_speed(subtasks):
        kind = intent.classify(text)
        if kind in IMMEDIATE_INTENTS:
            immediate.append(text)
        else:
            deferred.append(text)
    return immediate, deferred


def plan_summary(subtasks: list[str], *, voice: bool) -> str:
    """Human-readable execution order for batch replies."""
    ordered = sort_by_speed(subtasks)
    if len(ordered) <= 1:
        return ""

    labels: list[str] = []
    for i, part in enumerate(ordered, 1):
        kind = intent.classify(part)
        if kind == "system":
            labels.append(part[:50])
        elif kind == "code":
            labels.append("the build")
        else:
            labels.append(part[:40])

    if voice:
        if len(labels) == 2:
            return f"{labels[0].capitalize()} first, then {labels[1]}, boss."
        return f"Doing {len(labels)} tasks quickest first, boss."

    lines = "\n".join(f"{i}. {part} (~{eta_seconds(part)}s)" for i, part in enumerate(ordered, 1))
    return f"Execution order (fastest first):\n{lines}"
