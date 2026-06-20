from fastapi import FastAPI
from fastapi.testclient import TestClient

from jarvis.routers import api


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(api.router)
    return app


def test_create_agent_from_prompt(monkeypatch):
    async def fake_create_from_prompt(prompt: str, *, workspace_dir: str | None = None, model: str | None = None):
        assert prompt == "Create a release-notes specialist"
        assert workspace_dir == "/tmp/repo"
        assert model == "composer-2.5"
        return {
            "id": 7,
            "name": "Release Notes",
            "name_key": "release-notes",
            "purpose": "Write release notes",
            "instructions": "Draft concise release notes from merged changes.",
            "trigger_phrases": ["write release notes"],
            "status": "active",
            "runtime": {
                "execution_engine": "cursor",
                "autonomy_mode": "supervised",
                "model": "composer-2.5",
                "workspace_dir": "/tmp/repo",
                "allowed_tools": ["cursor_agent.run"],
            },
            "version": 1,
            "parent_agent_id": None,
            "performance_score": 0.0,
            "learning_notes": "",
            "last_used_at": None,
            "last_improved_at": None,
            "created_at": "2026-06-20 00:00:00",
            "updated_at": "2026-06-20 00:00:00",
        }

    monkeypatch.setattr(api.agent_author, "create_from_prompt", fake_create_from_prompt)
    client = TestClient(_app())

    response = client.post(
        "/api/agents",
        json={
            "authoring_prompt": "Create a release-notes specialist",
            "runtime": {"workspace_dir": "/tmp/repo", "model": "composer-2.5"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Release Notes"
    assert body["runtime"]["workspace_dir"] == "/tmp/repo"


def test_update_archive_and_invoke_agent(monkeypatch):
    async def fake_update_agent(agent_id: int, updates: dict):
        assert agent_id == 3
        assert updates["purpose"] == "Review backend and API diffs"
        assert updates["runtime"]["allowed_tools"] == ["cursor_agent.run", "web.research"]
        return {
            "id": 3,
            "name": "Code Reviewer",
            "name_key": "code-reviewer",
            "purpose": "Review backend and API diffs",
            "instructions": "Review code and report issues first.",
            "trigger_phrases": ["review backend"],
            "status": "active",
            "runtime": {
                "execution_engine": "cursor",
                "autonomy_mode": "supervised",
                "model": None,
                "workspace_dir": None,
                "allowed_tools": ["cursor_agent.run", "web.research"],
            },
            "version": 2,
            "parent_agent_id": None,
            "performance_score": 0.0,
            "learning_notes": "",
            "last_used_at": None,
            "last_improved_at": None,
            "created_at": "2026-06-20 00:00:00",
            "updated_at": "2026-06-20 00:00:00",
        }

    async def fake_archive_agent(agent_id: int):
        assert agent_id == 3
        return {"id": 3, "status": "archived", "version": 3}

    async def fake_invoke_agent(agent_id: int, task: str, *, voice: bool = False, conversation_id: str | None = None):
        assert agent_id == 3
        assert task == "Review the latest diff"
        assert voice is False
        assert conversation_id == "sess-1"
        return {
            "ok": True,
            "reply": "Found one likely regression.",
            "engine": "agent",
            "intent": "agent",
            "agent_name": "Code Reviewer",
            "agent_version": 2,
            "allowed_tools": ["cursor_agent.run", "web.research"],
        }

    monkeypatch.setattr(api.agent_registry, "update_agent", fake_update_agent)
    monkeypatch.setattr(api.agent_registry, "archive_agent", fake_archive_agent)
    monkeypatch.setattr(api.agent_runtime, "invoke_agent", fake_invoke_agent)
    client = TestClient(_app())

    update_response = client.patch(
        "/api/agents/3",
        json={
            "purpose": "Review backend and API diffs",
            "runtime": {"allowed_tools": ["cursor_agent.run", "web.research"]},
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2

    archive_response = client.post("/api/agents/3/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"

    invoke_response = client.post(
        "/api/agents/3/invoke",
        json={"task": "Review the latest diff", "session_id": "sess-1"},
    )
    assert invoke_response.status_code == 200
    assert invoke_response.json()["agent_name"] == "Code Reviewer"
