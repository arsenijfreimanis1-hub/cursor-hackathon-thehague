"""Domain detection and skill routing for CAD, GSD, web automation, and media."""

from __future__ import annotations

import re
from typing import Literal

SkillDomain = Literal["cad", "gsd", "web_automation", "media", "cursor"]

_DOMAIN_KEYWORDS: dict[SkillDomain, tuple[str, ...]] = {
    "cad": (
        "cad",
        "step file",
        ".step",
        ".stl",
        "build123d",
        "opencascade",
        "gear",
        "planetary",
        "3d model",
        "3d print",
        "robotics",
        "urdf",
        "sdf",
        "hardware design",
        "fabrication",
        "text-to-cad",
        "cadskills",
    ),
    "gsd": (
        "get-shit-done",
        "gsd",
        "spec-driven",
        "prd",
        "roadmap",
        "phase plan",
        "milestone",
        "workstream",
    ),
    "web_automation": (
        "scrape",
        "scraping",
        "browser automation",
        "selenium",
        "helium",
        "web automation",
        "fill form",
        "click button on",
        "navigate to",
        "headless browser",
        "playwright",
    ),
    "media": (
        "video edit",
        "video editor",
        "ffmpeg",
        "remotion",
        "higgsfield",
        "palmier",
        "render video",
        "video production",
        "ai video",
        "image generation",
        "motion graphics",
        "caption",
        "subtitle",
    ),
    "cursor": (
        "cursor sdk",
        "cursor agent",
        "refactor",
        "implement",
        "codebase",
        "pull request",
        "write tests",
        "fix bug",
        "add feature",
        "self-modify",
        "improve yourself",
        "change your code",
        "jarvis-core",
    ),
}

# Jarvis skill files that map to each domain (stem names under jarvis/skills/)
_DOMAIN_SKILL_FILES: dict[SkillDomain, str] = {
    "cad": "cad-design",
    "gsd": "gsd-planning",
    "web_automation": "web-automation",
    "media": "media-production",
    "cursor": "cursor-sdk",
}

# External skill directory name prefixes to pull from ~/.agents/skills etc.
_EXTERNAL_SKILL_PREFIXES: dict[SkillDomain, tuple[str, ...]] = {
    "cad": ("cad", "text-to-cad", "build123d", "robotics"),
    "gsd": ("gsd-", "get-shit-done"),
    "web_automation": ("helium", "web-automation", "browser"),
    "media": ("video", "media", "ffmpeg", "remotion"),
    "cursor": ("cursor", "codex", "composer"),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def detect_domains(text: str, *, always_include_gsd: bool = False) -> list[SkillDomain]:
    """Return matching skill domains for a prompt or slice, ordered by relevance."""
    lowered = _normalize(text)
    matched: list[SkillDomain] = []
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            matched.append(domain)
    if always_include_gsd and "gsd" not in matched:
        matched.insert(0, "gsd")
    return matched


def detect_slice_domains(slice_item: dict) -> list[SkillDomain]:
    """Detect domains from a build slice's title, prompt, files, and registry hints."""
    parts = [
        slice_item.get("title", ""),
        slice_item.get("prompt", ""),
        " ".join(slice_item.get("files") or []),
        " ".join(slice_item.get("registry_hints") or []),
        " ".join(slice_item.get("acceptance_criteria") or []),
    ]
    return detect_domains(" ".join(parts))


def domain_skill_filename(domain: SkillDomain) -> str:
    return _DOMAIN_SKILL_FILES[domain]


def external_skill_matches(name: str, domain: SkillDomain) -> bool:
    lowered = name.lower()
    return any(lowered.startswith(prefix) or prefix in lowered for prefix in _EXTERNAL_SKILL_PREFIXES[domain])


def stack_hints_for_domains(domains: list[SkillDomain]) -> dict[str, str]:
    """Return PRD stack hints based on detected domains."""
    hints: dict[str, str] = {}
    if "cad" in domains:
        hints.update({"domain": "cad", "language": "python", "cad_engine": "build123d"})
    if "web_automation" in domains:
        hints.update({"domain": "web_automation", "language": "python", "automation": "helium"})
    if "media" in domains:
        hints.update({"domain": "media", "language": "typescript", "media_tool": "ffmpeg"})
    if "gsd" in domains:
        hints.setdefault("planning", "gsd")
    if "cursor" in domains:
        hints.setdefault("execution_engine", "cursor_sdk")
    return hints
