from __future__ import annotations

import asyncio

import pytest


def _result(payload):
    if isinstance(payload, tuple):
        return payload[1]
    return payload


def test_list_gateway_skills_returns_split_skill_suite(app):
    payload = asyncio.run(app.state.mcp.call_tool("list_gateway_skills", {}))
    data = _result(payload)

    names = {s["skill_name"] for s in data["skills"]}
    assert "knowledge-gateway-logging" in names
    assert "knowledge-gateway-router" in names
    assert "knowledge-gateway-schema-intake" in names
    assert data["count"] == 3


def test_get_gateway_skill_rejects_unknown_name(app):
    with pytest.raises(Exception):
        asyncio.run(app.state.mcp.call_tool("get_gateway_skill", {"skill_name": "unknown-skill"}))


def test_initialize_gateway_skills_creates_all_canonical_paths(app):
    payload = asyncio.run(app.state.mcp.call_tool("initialize_gateway_skills", {}))
    data = _result(payload)

    assert data["status"] == "success"
    assert data["data"]["initialized_count"] == 3

    vault = app.state.settings.vault_root
    assert (vault / "System" / "Skills" / "knowledge-gateway-logging" / "SKILL.md").exists()
    assert (vault / "System" / "Skills" / "knowledge-gateway-router" / "SKILL.md").exists()
    assert (vault / "System" / "Skills" / "knowledge-gateway-schema-intake" / "SKILL.md").exists()


def test_update_gateway_skill_writes_and_get_reads_back(app):
    asyncio.run(
        app.state.mcp.call_tool(
            "initialize_gateway_skill",
            {"skill_name": "knowledge-gateway-router", "force": True},
        )
    )

    updated = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "update_gateway_skill",
                {
                    "skill_name": "knowledge-gateway-router",
                    "content": "# Skill: knowledge-gateway-router\n\n## Purpose\nCustom router behavior.",
                    "mode": "overwrite",
                    "reason": "test update",
                },
            )
        )
    )
    assert updated["status"] == "success"

    current = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "get_gateway_skill",
                {"skill_name": "knowledge-gateway-router"},
            )
        )
    )
    assert current["source"] == "vault"
    assert "Custom router behavior." in current["content"]


def test_logging_wrappers_match_generic_behavior(app):
    generic = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "get_gateway_skill",
                {"skill_name": "knowledge-gateway-logging"},
            )
        )
    )
    wrapper = _result(asyncio.run(app.state.mcp.call_tool("get_logging_skill", {})))
    assert wrapper["skill_name"] == generic["skill_name"]
    assert wrapper["version"] == generic["version"]
    assert wrapper["path"] == generic["path"]

    init_wrapper = _result(asyncio.run(app.state.mcp.call_tool("initialize_logging_skill", {"force": True})))
    init_generic = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "initialize_gateway_skill",
                {"skill_name": "knowledge-gateway-logging", "force": True},
            )
        )
    )
    assert init_wrapper["status"] == "success"
    assert init_generic["status"] == "success"
    assert init_wrapper["data"]["path"] == init_generic["data"]["path"]


def test_router_playbook_contracts_for_db_intent_and_naming(app):
    data = _result(asyncio.run(app.state.mcp.call_tool("get_usage_playbook", {})))

    create_db_route = data["db_intent_mapping"]["create database"]["route_to"]
    assert create_db_route == "create_dynamic_table"

    assert data["intent_router_protocol"]["unknown_intent_policy"] == "clarify_then_proceed"
    assert data["intent_router_protocol"]["write_on_ambiguous_intent"] is False

    naming = data["table_naming_policy"]
    assert naming["global_template"] == "global_<name>"
    assert naming["employer_template"] == "<employer_slug>_<name>"
    assert naming["project_template"] == "<employer_slug>_<project_slug>_<name>"

