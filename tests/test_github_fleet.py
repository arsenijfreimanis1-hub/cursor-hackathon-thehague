import asyncio
from pathlib import Path

import pytest

from jarvis.services import compute_fleet, github_sync


def test_github_slug():
    assert github_sync._slug("My Cool App!!") == "my-cool-app"


def test_hub_repo_url(monkeypatch):
    monkeypatch.setattr(github_sync.settings, "github_owner", "willy")
    monkeypatch.setattr(github_sync.settings, "william_hub_repo", "william-hub")
    assert github_sync.hub_repo_url() == "https://github.com/willy/william-hub.git"


def test_configured_requires_token_and_owner(monkeypatch):
    monkeypatch.setattr(github_sync.settings, "github_token", "")
    monkeypatch.setattr(github_sync.settings, "github_owner", "")
    assert github_sync.configured() is False

    monkeypatch.setattr(github_sync.settings, "github_token", "ghp_" + "x" * 36)
    monkeypatch.setattr(github_sync.settings, "github_owner", "willy")
    assert github_sync.configured() is True


def test_compute_fleet_cloud_workers_minimum():
    assert compute_fleet.cloud_worker_count() >= 3


def test_local_workers_minimum(monkeypatch):
    monkeypatch.setattr(compute_fleet.settings, "build_parallel", 1)
    assert compute_fleet.local_worker_count() >= 3


def test_resolve_runtime_defaults_local(monkeypatch):
    monkeypatch.setattr(compute_fleet.settings, "cursor_runtime", "local")
    assert compute_fleet.resolve_runtime() == "local"
    assert compute_fleet.effective_parallel() >= 3


def test_resolve_runtime_auto_fallback(monkeypatch):
    monkeypatch.setattr(github_sync, "configured", lambda: True)
    monkeypatch.setattr(compute_fleet.settings, "cursor_runtime", "auto")
    assert compute_fleet.resolve_runtime() == "local"


def test_export_build_manifest(tmp_path, monkeypatch):
    from jarvis.services import prd_store

    monkeypatch.setattr(github_sync.settings, "data_dir", tmp_path)
    build_id = 42
    prd_store.build_artifact_dir(build_id)
    prd_store.save_slices(build_id, [{"id": "slice-1", "title": "t"}])

    async def _run():
        return await github_sync.export_build_manifest(build_id, github_repo_url="https://github.com/w/william-project-42")

    result = asyncio.run(_run())
    assert result["ok"] is True
    manifest = (github_sync.hub_state_path() / "state" / "builds" / "42" / "manifest.json").read_text()
    assert "github.com" in manifest
