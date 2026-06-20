"""Load skill markdown files that extend William's operational knowledge."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def load_skills_block() -> str:
    if not SKILLS_DIR.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        parts.append(f"### Skill: {path.stem}\n{text}")
    if not parts:
        return ""
    return "OPERATIONAL SKILLS:\n" + "\n\n".join(parts)
