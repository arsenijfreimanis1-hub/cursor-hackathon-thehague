import pytest

from jarvis.services import agent_learning, agent_registry
from jarvis.services.agent_types import AgentSpec


@pytest.mark.anyio
async def test_record_agent_execution_refreshes_learning_state(monkeypatch, tmp_path):
    db_path = tmp_path / "agent-learning.db"
    monkeypatch.setattr(agent_registry, "DB_PATH", db_path)
    monkeypatch.setattr(agent_learning, "DB_PATH", db_path)

    agent = await agent_registry.register_agent(
        AgentSpec(
            name="Research Scout",
            purpose="Gather quick technical research",
            instructions="Use concise grounded summaries.",
            trigger_phrases=["research this"],
            runtime={"allowed_tools": ["cursor_agent.run", "web.research"]},
        )
    )

    constrained = {
        "ok": True,
        "result": "That is outside the allowlist right now. I can summarize findings or narrow the request.",
        "run_id": "run-1",
    }
    failed = {
        "ok": False,
        "error": "workspace missing required repository context",
        "run_id": "run-2",
    }

    first = await agent_learning.record_agent_execution(agent, "Open and deploy the repo", constrained)
    second = await agent_learning.record_agent_execution(agent, "Patch the production app", failed)

    assert first["outcome"] == "constrained"
    assert second["outcome"] == "failed"

    runs = await agent_learning.list_recent_runs("Research Scout")
    assert len(runs) == 2
    assert runs[0]["outcome"] == "failed"
    assert runs[1]["outcome"] == "constrained"

    refreshed = await agent_registry.get_agent("Research Scout")
    assert refreshed is not None
    assert refreshed.performance_score < 0.6
    assert "allowlist limits" in refreshed.learning_notes
    assert refreshed.last_improved_at is not None

    block = await agent_learning.get_agent_lessons_block("Research Scout")
    assert "AGENT-SPECIFIC LEARNING" in block
    assert "allowlist" in block.lower()

    summary = await agent_learning.get_agent_summary("Research Scout")
    assert summary["ok"] is True
    assert summary["meta"]["recent_runs"] == "2"
    assert summary["meta"]["recent_failures"] == "1"
    assert float(summary["meta"]["average_score"]) < 0.6
