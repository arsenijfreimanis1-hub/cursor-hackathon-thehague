"""Tests for skill domain detection and skills loading."""

from jarvis.services import skill_domains, skills


def test_detect_cad_domain():
    domains = skill_domains.detect_domains("build a planetary gear assembly in STEP format")
    assert "cad" in domains


def test_detect_cursor_domain():
    domains = skill_domains.detect_domains("refactor jarvis-core and improve yourself")
    assert "cursor" in domains


def test_detect_media_domain():
    domains = skill_domains.detect_domains("create a promo video with ffmpeg captions")
    assert "media" in domains


def test_detect_web_automation_domain():
    domains = skill_domains.detect_domains("scrape product prices using browser automation")
    assert "web_automation" in domains


def test_detect_slice_domains():
    sl = {
        "title": "Export STL",
        "prompt": "Generate gear model with build123d",
        "files": ["cad/gear.py", "exports/gear.stl"],
        "registry_hints": ["GearPart"],
        "acceptance_criteria": [],
    }
    domains = skill_domains.detect_slice_domains(sl)
    assert "cad" in domains


def test_stack_hints_for_cad():
    hints = skill_domains.stack_hints_for_domains(["cad"])
    assert hints.get("cad_engine") == "build123d"


def test_load_skills_block_includes_core():
    block = skills.load_skills_block()
    assert "OPERATIONAL SKILLS" in block
    assert "grounding" in block.lower() or "Skill: grounding" in block


def test_load_skills_block_domain_filter():
    block = skills.load_skills_block(domains=["cad"], include_external=False)
    assert "cad-design" in block.lower() or "CAD" in block


def test_load_domain_block_empty_for_generic():
    block = skills.load_domain_block("what time is it")
    assert block == ""


def test_external_skill_matches():
    assert skill_domains.external_skill_matches("gsd-plan-phase", "gsd")
    assert skill_domains.external_skill_matches("cad-export", "cad")
