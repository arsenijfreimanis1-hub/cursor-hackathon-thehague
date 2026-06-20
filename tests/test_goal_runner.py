"""Tests for jarvis.services.goal_runner safety caps and approval flow."""

import pytest

from jarvis.services.goal_runner import (
    MAX_ITERATIONS,
    MAX_WALL_SECONDS,
    _needs_approval,
    _wall_elapsed_seconds,
)


def test_needs_approval_sensitive_keywords():
    assert _needs_approval("please deploy to production") is True
    assert _needs_approval("delete old backups") is True
    assert _needs_approval("open Spotify and play music") is False


def test_wall_elapsed_seconds_without_start():
    assert _wall_elapsed_seconds({}) == 0.0


def test_wall_elapsed_seconds_with_start():
    goal = {"started_at": "2020-01-01 00:00:00"}
    assert _wall_elapsed_seconds(goal) > MAX_WALL_SECONDS


def test_iteration_cap_constant():
    assert MAX_ITERATIONS == 10


def test_wall_cap_constant():
    assert MAX_WALL_SECONDS == 30 * 60


@pytest.mark.asyncio
async def test_approve_goal_not_found():
    from jarvis.services import goal_runner

    result = await goal_runner.approve_goal(999999999)
    assert result["ok"] is False
    assert "not found" in result["error"]
