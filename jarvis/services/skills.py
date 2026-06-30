"""Load skill markdown files that extend William's operational knowledge."""

from __future__ import annotations

from pathlib import Path

from jarvis.config import ROOT, settings
from jarvis.services import skill_domains

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

GLOBAL_SKILL_ROOTS = [
    ROOT / ".agents" / "skills",
    Path.home() / ".agents" / "skills",
    Path.home() / ".cursor" / "skills",
    Path.home() / ".codex" / "skills",
]


def _read_skill(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _discover_external_skills(
    *,
    domains: list[skill_domains.SkillDomain] | None = None,
) -> list[tuple[str, str]]:
    """Discover SKILL.md files from global skill directories."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for root in GLOBAL_SKILL_ROOTS:
        if not root.is_dir():
            continue
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            name = skill_dir.name
            if name in seen:
                continue
            if domains and not any(
                skill_domains.external_skill_matches(name, domain) for domain in domains
            ):
                continue
            text = _read_skill(skill_file)
            if text:
                found.append((name, text))
                seen.add(name)
    return found


def _load_jarvis_skills(
    *,
    domains: list[skill_domains.SkillDomain] | None = None,
    include_core: bool = True,
) -> list[tuple[str, str]]:
    """Load jarvis/skills/*.md — core skills always, domain skills when matched."""
    if not SKILLS_DIR.is_dir():
        return []

    domain_files = {skill_domains.domain_skill_filename(d) for d in (domains or [])}
    core_stems = {
        "grounding", "research", "voice", "cursor-escalation",
        "screen-observer", "skills-bridge",
    }

    parts: list[tuple[str, str]] = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        stem = path.stem
        include = False
        if include_core and stem in core_stems:
            include = True
        elif domains and stem in domain_files:
            include = True
        if not include:
            continue
        text = _read_skill(path)
        if text:
            parts.append((stem, text))
    return parts


def load_skills_block(
    *,
    domains: list[skill_domains.SkillDomain] | None = None,
    include_external: bool = True,
) -> str:
    """Build the OPERATIONAL SKILLS block for agent prompts."""
    parts: list[str] = []

    for name, text in _load_jarvis_skills(domains=domains):
        parts.append(f"### Skill: {name}\n{text}")

    if include_external and settings.external_skills_enabled:
        for name, text in _discover_external_skills(domains=domains):
            parts.append(f"### External Skill: {name}\n{text}")

    if not parts:
        return ""
    return "OPERATIONAL SKILLS:\n" + "\n\n".join(parts)


def load_domain_block(text: str) -> str:
    """Load skills matched to a prompt or slice text."""
    domains = skill_domains.detect_domains(text)
    if not domains:
        return ""
    return load_skills_block(domains=domains)


def list_installed_skills() -> list[dict[str, str]]:
    """Return metadata for dashboard / API."""
    items: list[dict[str, str]] = []
    for name, _ in _load_jarvis_skills(include_core=True, domains=None):
        items.append({"name": name, "source": "jarvis"})
    for name, _ in _discover_external_skills():
        items.append({"name": name, "source": "external"})
    return items
