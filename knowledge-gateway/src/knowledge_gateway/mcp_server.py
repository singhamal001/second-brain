from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .context import current_auth_context
from .services.audit import AuditService
from .services.db_store import DBStore
from .services.errors import GatewayError
from .services.obsidian_store import ObsidianStore
from .services.reporting import ReportingService
from .services.schema_manager import SchemaManager


class ColumnSpec(BaseModel):
    name: str
    type: Literal["text", "string", "int", "float", "bool", "datetime", "json"] = "text"
    nullable: bool = True


class RowFilter(BaseModel):
    column: str
    op: Literal["eq", "neq", "gt", "gte", "lt", "lte", "like", "in"] = "eq"
    value: Any


class SortSpec(BaseModel):
    column: str
    direction: Literal["asc", "desc"] = "asc"


class MutationEnvelope(BaseModel):
    status: Literal["success", "error"]
    operation_id: str
    affected_records: int
    obsidian_note_path: str | None = None
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_mcp_server(
    *,
    name: str,
    version: str,
    db_store: DBStore,
    obsidian_store: ObsidianStore,
    schema_manager: SchemaManager,
    reporting_service: ReportingService,
    audit_service: AuditService,
) -> FastMCP:
    # Bind FastMCP to 0.0.0.0 so the SDK does not auto-enable localhost-only
    # Host header protection, which breaks reverse-proxy/tunnel hostnames.
    mcp = FastMCP(name=name, host="0.0.0.0")
    mcp.version = version

    def current_client_code() -> str | None:
        ctx = current_auth_context.get()
        return ctx.client_code if ctx else None

    def mutation_success(
        operation_id: str,
        affected_records: int,
        data: dict[str, Any],
        obsidian_note_path: str | None = None,
    ) -> dict[str, Any]:
        return MutationEnvelope(
            status="success",
            operation_id=operation_id,
            affected_records=affected_records,
            obsidian_note_path=obsidian_note_path,
            timestamp=_now(),
            data=data,
        ).model_dump(mode="json")

    def mutation_error(operation_id: str, message: str) -> dict[str, Any]:
        return MutationEnvelope(
            status="error",
            operation_id=operation_id,
            affected_records=0,
            timestamp=_now(),
            data={"error": message},
        ).model_dump(mode="json")

    def execute_mutation(
        *,
        action_type: str,
        target_system: str,
        table_name: str | None,
        payload: dict[str, Any],
        executor: callable,
    ) -> dict[str, Any]:
        operation_id = str(uuid.uuid4())
        code = current_client_code()
        try:
            data, affected, note_path, record_id = executor()
            audit_service.record(
                operation_id=operation_id,
                action_type=action_type,
                source_system="mcp",
                target_system=target_system,
                table_name=table_name,
                record_identifier=record_id,
                client_code=code,
                payload=payload,
                status="success",
            )
            return mutation_success(operation_id, affected, data, note_path)
        except (GatewayError, ValueError) as exc:
            audit_service.record(
                operation_id=operation_id,
                action_type=action_type,
                source_system="mcp",
                target_system=target_system,
                table_name=table_name,
                record_identifier=None,
                client_code=code,
                payload=payload,
                status="error",
                error_message=str(exc),
            )
            return mutation_error(operation_id, str(exc))

    def render_session_note(row: dict[str, Any]) -> str:
        started = row["started_at"].astimezone(timezone.utc).isoformat()
        ended = row["ended_at"].astimezone(timezone.utc).isoformat() if row.get("ended_at") else ""
        tags = ", ".join(row.get("tags_json") or [])
        return (
            f"# Session: {row['title']}\n\n"
            f"- Employer: {row['employer_name']}\n"
            f"- Project: {row['project_name']}\n"
            f"- Started: {started}\n"
            f"- Ended: {ended}\n"
            f"- Source: {row.get('source', 'codex')}\n"
            f"- Idempotency Key: {row['idempotency_key']}\n"
            f"- Tags: {tags}\n\n"
            f"## Objective\n{row.get('objective') or ''}\n\n"
            f"## Summary\n{row.get('summary') or ''}\n\n"
            f"## Thought Process\n{row.get('thought_process') or ''}\n\n"
            f"## Methodology\n{row.get('methodology') or ''}\n\n"
            f"## Major Changes\n{row.get('major_changes') or ''}\n\n"
            f"## Advantages\n{row.get('advantages') or ''}\n\n"
            f"## Disadvantages\n{row.get('disadvantages') or ''}\n\n"
            f"## Blockers\n{row.get('blockers') or ''}\n\n"
            f"## Next Steps\n{row.get('next_steps') or ''}\n\n"
            f"## Learnings\n{row.get('learnings') or ''}\n\n"
            f"## Skills Updates\n{row.get('skills_updates') or ''}\n"
        )

    def render_meeting_note(row: dict[str, Any]) -> str:
        return (
            f"# Meeting: {row['title']}\n\n"
            f"- Employer: {row['employer_name']}\n"
            f"- Project: {row['project_name']}\n"
            f"- DateTime: {row['meeting_datetime'].astimezone(timezone.utc).isoformat()}\n\n"
            f"## Summary\n{row.get('summary') or ''}\n\n"
            f"## Attendees\n{row.get('attendees_json') or []}\n\n"
            f"## Decisions\n{row.get('decisions_json') or []}\n\n"
            f"## Commitments\n{row.get('commitments_json') or []}\n\n"
            f"## Dependencies\n{row.get('dependencies_json') or []}\n\n"
            f"## Next Steps\n{row.get('next_steps_json') or []}\n"
        )

    def render_decision_note(row: dict[str, Any]) -> str:
        return (
            f"# Decision: {row['title']}\n\n"
            f"- Employer: {row['employer_name']}\n"
            f"- Project: {row['project_name']}\n"
            f"- Status: {row.get('status', 'active')}\n\n"
            f"## Context\n{row.get('context') or ''}\n\n"
            f"## Chosen Option\n{row.get('chosen_option') or ''}\n\n"
            f"## Rejected Options\n{row.get('rejected_options_json') or []}\n\n"
            f"## Rationale\n{row.get('rationale') or ''}\n\n"
            f"## Pros\n{row.get('pros') or ''}\n\n"
            f"## Cons\n{row.get('cons') or ''}\n\n"
            f"## Impact\n{row.get('impact') or ''}\n"
        )

    @mcp.tool()
    def create_employer(name: str, description: str | None = None) -> dict[str, Any]:
        payload = {"name": name, "description": description}

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            row = db_store.create_employer(name=name, description=description)
            return row, 1, None, row["id"]

        return execute_mutation(
            action_type="create_employer",
            target_system="postgres",
            table_name="employers",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def create_project(
        employer_name: str,
        project_name: str,
        code_name: str | None = None,
        description: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        payload = {
            "employer_name": employer_name,
            "project_name": project_name,
            "code_name": code_name,
            "description": description,
            "status": status,
        }

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            row = db_store.create_project(
                employer_name=employer_name,
                name=project_name,
                code_name=code_name,
                description=description,
                status=status,
            )
            obsidian_store.ensure_project_structure(employer_name, project_name)
            return row, 1, None, row["id"]

        return execute_mutation(
            action_type="create_project",
            target_system="postgres",
            table_name="projects",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def log_coding_session(
        employer_name: str,
        project_name: str,
        session_title: str,
        idempotency_key: str,
        started_at: str,
        ended_at: str | None = None,
        objective: str | None = None,
        summary: str | None = None,
        thought_process: str | None = None,
        methodology: str | None = None,
        major_changes: str | None = None,
        advantages: str | None = None,
        disadvantages: str | None = None,
        blockers: str | None = None,
        next_steps: str | None = None,
        learnings: str | None = None,
        skills_updates: str | None = None,
        tags: list[str] | None = None,
        source: str = "codex",
    ) -> dict[str, Any]:
        payload = {
            "employer_name": employer_name,
            "project_name": project_name,
            "title": session_title,
            "idempotency_key": idempotency_key,
            "started_at": started_at,
            "ended_at": ended_at,
            "objective": objective,
            "summary": summary,
            "thought_process": thought_process,
            "methodology": methodology,
            "major_changes": major_changes,
            "advantages": advantages,
            "disadvantages": disadvantages,
            "blockers": blockers,
            "next_steps": next_steps,
            "learnings": learnings,
            "skills_updates": skills_updates,
            "tags": tags,
            "source": source,
        }

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            row = db_store.log_session(
                {
                    **payload,
                    "started_at": _parse_datetime(started_at),
                    "ended_at": _parse_datetime(ended_at),
                }
            )
            note_path = row.get("obsidian_note_path")
            if not note_path:
                note_path = ObsidianStore.canonical_session_path(
                    employer=row["employer_name"],
                    project=row["project_name"],
                    session_id=row["id"],
                    started_at=row["started_at"],
                    feature_name=row["title"],
                )
                obsidian_store.upsert_note(note_path, render_session_note(row), mode="overwrite")
                db_store.update_session_note_path(row["id"], note_path)
                row["obsidian_note_path"] = note_path
            return row, 1, note_path, row["id"]

        return execute_mutation(
            action_type="log_coding_session",
            target_system="postgres+obsidian",
            table_name="sessions",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def log_meeting(
        employer_name: str,
        project_name: str,
        meeting_title: str,
        meeting_datetime: str,
        summary: str | None = None,
        attendees: list[str] | None = None,
        decisions: list[str] | None = None,
        dependencies: list[str] | None = None,
        commitments: list[str] | None = None,
        next_steps: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "employer_name": employer_name,
            "project_name": project_name,
            "title": meeting_title,
            "meeting_datetime": meeting_datetime,
            "summary": summary,
            "attendees": attendees,
            "decisions": decisions,
            "dependencies": dependencies,
            "commitments": commitments,
            "next_steps": next_steps,
        }

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            row = db_store.log_meeting({**payload, "meeting_datetime": _parse_datetime(meeting_datetime)})
            note_path = ObsidianStore.canonical_meeting_path(
                employer=row["employer_name"],
                project=row["project_name"],
                meeting_id=row["id"],
                meeting_dt=row["meeting_datetime"],
                feature_name=row["title"],
            )
            obsidian_store.upsert_note(note_path, render_meeting_note(row), mode="overwrite")
            db_store.update_meeting_note_path(row["id"], note_path)
            row["obsidian_note_path"] = note_path
            return row, 1, note_path, row["id"]

        return execute_mutation(
            action_type="log_meeting",
            target_system="postgres+obsidian",
            table_name="meetings",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def log_decision(
        employer_name: str,
        project_name: str,
        title: str,
        context: str | None = None,
        chosen_option: str | None = None,
        rejected_options: list[str] | None = None,
        rationale: str | None = None,
        pros: str | None = None,
        cons: str | None = None,
        impact: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        payload = {
            "employer_name": employer_name,
            "project_name": project_name,
            "title": title,
            "context": context,
            "chosen_option": chosen_option,
            "rejected_options": rejected_options,
            "rationale": rationale,
            "pros": pros,
            "cons": cons,
            "impact": impact,
            "status": status,
        }

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            row = db_store.log_decision(payload)
            note_path = ObsidianStore.canonical_decision_path(
                employer=row["employer_name"],
                project=row["project_name"],
                decision_id=row["id"],
                created_at=row["created_at"],
                feature_name=row["title"],
            )
            obsidian_store.upsert_note(note_path, render_decision_note(row), mode="overwrite")
            db_store.update_decision_note_path(row["id"], note_path)
            row["obsidian_note_path"] = note_path
            return row, 1, note_path, row["id"]

        return execute_mutation(
            action_type="log_decision",
            target_system="postgres+obsidian",
            table_name="decisions",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def create_dynamic_table(table_name: str, description: str, columns: list[ColumnSpec]) -> dict[str, Any]:
        payload = {
            "table_name": table_name,
            "description": description,
            "columns": [c.model_dump() for c in columns],
        }

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            data = schema_manager.create_dynamic_table(
                table_name=table_name,
                description=description,
                columns=[c.model_dump() for c in columns],
            )
            return data, 1, None, table_name

        return execute_mutation(
            action_type="create_dynamic_table",
            target_system="postgres",
            table_name="table_registry",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def list_tables(include_archived: bool = False) -> dict[str, Any]:
        return {"tables": schema_manager.list_tables(include_archived=include_archived)}

    @mcp.tool()
    def describe_table(table_name: str) -> dict[str, Any]:
        return schema_manager.describe_table(table_name)

    @mcp.tool()
    def archive_table(table_name: str) -> dict[str, Any]:
        payload = {"table_name": table_name}

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            data = schema_manager.archive_table(table_name)
            return data, 1, None, table_name

        return execute_mutation(
            action_type="archive_table",
            target_system="postgres",
            table_name="table_registry",
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def insert_rows(table_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"table_name": table_name, "rows": rows}

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            data = db_store.insert_rows(table_name=table_name, rows=rows)
            return data, data["affected_records"], None, table_name

        return execute_mutation(
            action_type="insert_rows",
            target_system="postgres",
            table_name=table_name,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def update_rows(table_name: str, values: dict[str, Any], filters: list[RowFilter]) -> dict[str, Any]:
        payload = {
            "table_name": table_name,
            "values": values,
            "filters": [f.model_dump() for f in filters],
        }

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            data = db_store.update_rows(
                table_name=table_name,
                values=values,
                filters=[f.model_dump() for f in filters],
            )
            return data, data["affected_records"], None, table_name

        return execute_mutation(
            action_type="update_rows",
            target_system="postgres",
            table_name=table_name,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def archive_rows(table_name: str, filters: list[RowFilter]) -> dict[str, Any]:
        payload = {"table_name": table_name, "filters": [f.model_dump() for f in filters]}

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            data = db_store.archive_rows(table_name=table_name, filters=[f.model_dump() for f in filters])
            return data, data["affected_records"], None, table_name

        return execute_mutation(
            action_type="archive_rows",
            target_system="postgres",
            table_name=table_name,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def query_rows(
        table_name: str,
        filters: list[RowFilter] | None = None,
        sort: list[SortSpec] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return db_store.query_rows(
            table_name=table_name,
            filters=[f.model_dump() for f in (filters or [])],
            sort=[s.model_dump() for s in (sort or [])],
            limit=limit,
        )

    @mcp.tool()
    def get_project_timeline(
        employer_name: str,
        project_name: str,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return reporting_service.get_project_timeline(
            employer_name=employer_name,
            project_name=project_name,
            from_dt=_parse_datetime(from_datetime),
            to_dt=_parse_datetime(to_datetime),
            limit=limit,
        )

    @mcp.tool()
    def get_project_summary(employer_name: str, project_name: str) -> dict[str, Any]:
        return reporting_service.get_project_summary(employer_name=employer_name, project_name=project_name)

    @mcp.tool()
    def get_open_dependencies(employer_name: str, project_name: str | None = None) -> dict[str, Any]:
        return reporting_service.get_open_dependencies(employer_name=employer_name, project_name=project_name)

    @mcp.tool()
    def get_obsidian_note(path: str) -> dict[str, Any]:
        return obsidian_store.get_note(path)

    @mcp.tool()
    def upsert_obsidian_note(path: str, content: str, mode: Literal["overwrite", "append"] = "overwrite") -> dict[str, Any]:
        payload = {"path": path, "mode": mode, "content_len": len(content)}

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            note_path = obsidian_store.upsert_note(path, content, mode=mode)
            return {"path": note_path, "mode": mode}, 1, note_path, note_path

        return execute_mutation(
            action_type="upsert_obsidian_note",
            target_system="obsidian",
            table_name=None,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool()
    def get_gateway_policy() -> dict[str, Any]:
        return {
            "destructive_operations": "disabled",
            "row_deletion_policy": "archive_only",
            "table_deletion_policy": "archive_only",
            "drop_table_supported": False,
            "delete_rows_supported": False,
        }

    return mcp
