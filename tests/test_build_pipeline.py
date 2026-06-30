import asyncio
import json
from pathlib import Path

import pytest

from jarvis.services import build_decomposer, build_pipeline, build_reconciler, prd_store


def test_build_start_and_micro_approval(monkeypatch, tmp_path):
    slices = [
        {
            "id": "slice-1",
            "ordinal": 1,
            "title": "Setup",
            "prompt": "Create project scaffold",
            "deps": [],
            "acceptance_criteria": ["README exists"],
            "files": ["README.md"],
            "registry_hints": ["App"],
            "research": {},
            "status": "pending",
        },
        {
            "id": "slice-2",
            "ordinal": 2,
            "title": "API",
            "prompt": "Add API routes",
            "deps": ["slice-1"],
            "acceptance_criteria": ["Routes respond"],
            "files": ["src/api.py"],
            "registry_hints": ["ApiRouter"],
            "research": {},
            "status": "pending",
        },
    ]

    async def fake_comprehend(prompt, *, build_id=None, history=""):
        return {
            "prompt_class": "implementation",
            "product_summary": prompt[:500],
            "identified_parts": [],
            "decomposition_strategy": "standard",
        }

    async def fake_decompose(prompt, *, history="", intake=None, build_id=None):
        return slices

    async def fake_research(s, **kwargs):
        return [{**sl, "research": {"recommendation": "use fastapi"}} for sl in s]

    async def fake_reconcile(prompt, s, **kwargs):
        return s

    async def fake_notify(*args, **kwargs):
        return None

    monkeypatch.setattr("jarvis.services.build_intake.comprehend", fake_comprehend)
    monkeypatch.setattr(build_decomposer, "decompose", fake_decompose)
    monkeypatch.setattr("jarvis.services.build_research.research_slices", fake_research)
    monkeypatch.setattr(build_reconciler, "reconcile", fake_reconcile)
    monkeypatch.setattr(build_pipeline.macos, "notify", fake_notify)
    monkeypatch.setattr(build_pipeline.macos, "speak_when_clear", fake_notify)
    monkeypatch.setattr(build_pipeline, "_default_workspace", lambda p: tmp_path / "proj")

    async def _run():
        created = await build_pipeline.start("build: todo app with api", source="web")
        assert created["ok"] is True
        build_id = created["build_id"]

        task = build_pipeline._active_tasks.get(build_id)
        if task:
            await task

        detail = await build_pipeline.get_build_detail(build_id)
        assert detail["phase"] == build_pipeline.PHASE_AWAITING_MICRO
        assert len(detail["slices"]) == 2

        approved = await build_pipeline.approve_micro_prompts(build_id)
        assert approved["ok"] is True

        task2 = build_pipeline._active_tasks.get(build_id)
        if task2:
            await task2

        detail2 = await build_pipeline.get_build_detail(build_id)
        assert detail2["phase"] == build_pipeline.PHASE_AWAITING_PRD
        assert prd_store.load_prd(build_id)
        assert prd_store.load_registry(build_id).get("entries")

    asyncio.run(_run())


def test_prd_store_generate_and_registry():
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        from jarvis.config import settings

        old = settings.data_dir
        settings.data_dir = Path(td)
        try:
            build_id = 99
            prd_store.build_artifact_dir(build_id)
            slices = [
                {
                    "id": "slice-1",
                    "title": "Auth",
                    "prompt": "Implement auth",
                    "deps": [],
                    "files": ["src/auth.py"],
                    "registry_hints": ["AuthService"],
                    "acceptance_criteria": ["Login works"],
                }
            ]
            prd, registry = prd_store.generate_prd(build_id, prompt="Auth app", slices=slices)
            assert "AuthService" in prd
            assert "AuthService" in registry.get("entries", {})
            prd_store.merge_registry_entries(build_id, {"UserModel": {"type": "class", "file": "src/models.py"}})
            reg = prd_store.load_registry(build_id)
            assert reg["version"] >= 2
            assert "UserModel" in reg["entries"]
        finally:
            settings.data_dir = old


def test_looks_like_build():
    assert build_pipeline.looks_like_build("build project: create a react todo app with fastapi backend")
    assert build_pipeline.BUILD_PREFIX.match("build: something")
    assert not build_pipeline.looks_like_build("what is the weather")


def test_parse_new_registry_entries():
    text = 'Done.\nNEW_REGISTRY_ENTRIES\n{"entries": {"Foo": {"type": "class", "file": "foo.py"}}}'
    entries = prd_store.parse_new_registry_entries(text)
    assert "Foo" in entries
