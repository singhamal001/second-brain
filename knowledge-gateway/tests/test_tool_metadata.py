from __future__ import annotations

import asyncio


def _result(payload):
    if isinstance(payload, tuple):
        return payload[1]
    return payload


def test_key_tools_expose_non_empty_descriptions(app):
    async def flow():
        tools = await app.state.mcp.list_tools()
        return {tool.name: (tool.description or "") for tool in tools}

    descriptions = asyncio.run(flow())
    required_tools = [
        "log_coding_session",
        "log_meeting",
        "log_decision",
        "create_project",
        "upsert_obsidian_note",
        "get_logging_skill",
        "initialize_logging_skill",
        "update_logging_skill",
        "get_usage_playbook",
    ]

    for tool_name in required_tools:
        assert tool_name in descriptions
        assert descriptions[tool_name].strip() != ""


def test_get_usage_playbook_returns_intent_and_policy(app):
    payload = asyncio.run(app.state.mcp.call_tool("get_usage_playbook", {}))
    data = _result(payload)

    assert data["version"] == "2026-04-16"
    assert data["intent_to_tool"]["log this session"] == "log_coding_session"
    assert data["intent_to_tool"]["get logging skill"] == "get_logging_skill"
    assert data["write_policy"]["prefer_structured_tools"] is True
    assert data["write_policy"]["upsert_obsidian_note"] == "manual_or_exception_only"
    assert data["shared_skill"]["name"] == "knowledge-gateway-logging"
