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
        "list_gateway_skills",
        "get_gateway_skill",
        "initialize_gateway_skill",
        "initialize_gateway_skills",
        "update_gateway_skill",
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

    assert data["version"] == "2026-04-19"
    assert data["intent_to_tool"]["log this session"] == "log_coding_session"
    assert data["intent_to_tool"]["initialize skill"] == "initialize_gateway_skill"
    assert data["write_policy"]["prefer_structured_tools"] is True
    assert data["write_policy"]["upsert_obsidian_note"] == "manual_or_exception_only"
    assert data["intent_router_protocol"]["scope_resolution_policy"] == "ask_if_missing"
    assert data["intent_router_protocol"]["unknown_intent_policy"] == "clarify_then_proceed"
    assert data["db_intent_mapping"]["create database"]["route_to"] == "create_dynamic_table"
    assert data["table_naming_policy"]["mode"] == "auto_prefix_by_scope"
