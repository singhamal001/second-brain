from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select


def _result(payload):
    if isinstance(payload, tuple):
        return payload[1]
    return payload


def test_create_project_initializes_employer_project_folder(app):
    mcp = app.state.mcp

    async def flow():
        await mcp.call_tool("create_employer", {"name": "FolderEmployer"})
        await mcp.call_tool(
            "create_project",
            {
                "employer_name": "FolderEmployer",
                "project_name": "FolderProject",
            },
        )

    asyncio.run(flow())
    expected = app.state.settings.vault_root / "Employers" / "FolderEmployer" / "FolderProject"
    assert expected.exists()
    assert expected.is_dir()


def test_log_coding_session_dual_write_and_idempotency(app):
    mcp = app.state.mcp

    async def flow():
        await mcp.call_tool("create_employer", {"name": "Benori"})
        await mcp.call_tool(
            "create_project",
            {
                "employer_name": "Benori",
                "project_name": "Project Alpha",
                "description": "alpha",
            },
        )

        first = _result(
            await mcp.call_tool(
                "log_coding_session",
                {
                    "employer_name": "Benori",
                    "project_name": "Project Alpha",
                    "session_title": "Implement gateway",
                    "idempotency_key": "sess-001",
                    "started_at": "2026-04-07T10:00:00+05:30",
                    "ended_at": "2026-04-07T11:00:00+05:30",
                    "objective": "Build core logging",
                    "summary": "Completed MVP path",
                    "next_steps": "Add tests",
                },
            )
        )

        second = _result(
            await mcp.call_tool(
                "log_coding_session",
                {
                    "employer_name": "Benori",
                    "project_name": "Project Alpha",
                    "session_title": "Implement gateway",
                    "idempotency_key": "sess-001",
                    "started_at": "2026-04-07T10:00:00+05:30",
                    "ended_at": "2026-04-07T11:00:00+05:30",
                    "objective": "Build core logging",
                    "summary": "Completed MVP path",
                    "next_steps": "Add tests",
                },
            )
        )

        return first, second

    first, second = asyncio.run(flow())

    assert first["status"] == "success"
    assert second["status"] == "success"
    assert first["data"]["id"] == second["data"]["id"]
    assert second["data"]["existing"] is True

    note_path = first["obsidian_note_path"]
    assert note_path.startswith("Employers/Benori/Project Alpha/2026-04-07-update-implement-gateway/")
    assert note_path.endswith(".md")
    full_note_path = app.state.settings.vault_root / note_path
    assert full_note_path.exists()
    assert "Implement gateway" in full_note_path.read_text(encoding="utf-8")

    sessions = app.state.db_store.tables["sessions"]
    activity_log = app.state.db_store.tables["activity_log"]
    with app.state.db_store.engine.begin() as conn:
        session_count = conn.execute(select(func.count()).select_from(sessions)).scalar_one()
        audit_count = conn.execute(
            select(func.count())
            .select_from(activity_log)
            .where(activity_log.c.action_type == "log_coding_session")
            .where(activity_log.c.status == "success")
        ).scalar_one()

    assert session_count == 1
    assert audit_count == 2


def test_project_timeline_excludes_archived_rows(app):
    mcp = app.state.mcp

    async def flow():
        await mcp.call_tool("create_employer", {"name": "EmployerX"})
        await mcp.call_tool(
            "create_project",
            {
                "employer_name": "EmployerX",
                "project_name": "Proj",
            },
        )
        await mcp.call_tool(
            "log_coding_session",
            {
                "employer_name": "EmployerX",
                "project_name": "Proj",
                "session_title": "Active session",
                "idempotency_key": "active-001",
                "started_at": "2026-04-07T10:00:00+00:00",
            },
        )
        created = _result(
            await mcp.call_tool(
                "log_coding_session",
                {
                    "employer_name": "EmployerX",
                    "project_name": "Proj",
                    "session_title": "To archive",
                    "idempotency_key": "arch-001",
                    "started_at": "2026-04-07T12:00:00+00:00",
                },
            )
        )
        return created["data"]["id"]

    archived_session_id = asyncio.run(flow())

    sessions = app.state.db_store.tables["sessions"]
    from sqlalchemy import update

    with app.state.db_store.engine.begin() as conn:
        conn.execute(update(sessions).where(sessions.c.id == archived_session_id).values(archived=True))

    timeline = asyncio.run(
        app.state.mcp.call_tool(
            "get_project_timeline",
            {
                "employer_name": "EmployerX",
                "project_name": "Proj",
                "limit": 50,
            },
        )
    )
    data = _result(timeline)
    titles = [event["title"] for event in data["events"]]

    assert "Active session" in titles
    assert "To archive" not in titles
