"""Tests for MCP config loading."""

from jarvis.services import mcp_config


def test_load_mcp_servers_returns_dict():
    servers = mcp_config.load_mcp_servers()
    assert isinstance(servers, dict)


def test_mcp_server_count():
    count = mcp_config.mcp_server_count()
    assert count == len(mcp_config.load_mcp_servers())
