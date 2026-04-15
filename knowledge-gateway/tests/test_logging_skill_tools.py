from __future__ import annotations

import asyncio


def _result(payload):
    if isinstance(payload, tuple):
        return payload[1]
    return payload


def test_get_logging_skill_defaults_when_not_initialized(app):
    payload = asyncio.run(app.state.mcp.call_tool("get_logging_skill", {}))
    data = _result(payload)

    assert data["skill_name"] == "knowledge-gateway-logging"
    assert data["version"] == "2026-04-16"
    assert data["source"] == "default"
    assert data["path"] == "System/Skills/knowledge-gateway-logging/SKILL.md"
    assert "Golden Rule" in data["content"]


def test_initialize_logging_skill_creates_canonical_note(app):
    payload = asyncio.run(app.state.mcp.call_tool("initialize_logging_skill", {}))
    data = _result(payload)

    assert data["status"] == "success"
    assert data["data"]["initialized"] is True

    note_path = app.state.settings.vault_root / "System" / "Skills" / "knowledge-gateway-logging" / "SKILL.md"
    assert note_path.exists()
    assert "Skill: knowledge-gateway-logging" in note_path.read_text(encoding="utf-8")

    current = _result(asyncio.run(app.state.mcp.call_tool("get_logging_skill", {})))
    assert current["source"] == "vault"


def test_update_logging_skill_overwrite_and_append(app):
    asyncio.run(app.state.mcp.call_tool("initialize_logging_skill", {}))

    overwrite = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "update_logging_skill",
                {
                    "content": "# Skill: knowledge-gateway-logging\n\n## Purpose\nCustom behavior.",
                    "mode": "overwrite",
                    "reason": "customize for device-agnostic policy",
                },
            )
        )
    )
    assert overwrite["status"] == "success"

    after_overwrite = _result(asyncio.run(app.state.mcp.call_tool("get_logging_skill", {})))
    assert "Custom behavior." in after_overwrite["content"]
    assert after_overwrite["source"] == "vault"

    append = _result(
        asyncio.run(
            app.state.mcp.call_tool(
                "update_logging_skill",
                {
                    "content": "## Retrieval Reminder\nAlways use project timeline first.",
                    "mode": "append",
                },
            )
        )
    )
    assert append["status"] == "success"

    after_append = _result(asyncio.run(app.state.mcp.call_tool("get_logging_skill", {})))
    assert "Custom behavior." in after_append["content"]
    assert "Always use project timeline first." in after_append["content"]

