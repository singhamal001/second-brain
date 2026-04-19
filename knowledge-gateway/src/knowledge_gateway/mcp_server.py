from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .context import current_auth_context
from .services.audit import AuditService
from .services.db_store import DBStore
from .services.errors import GatewayError, ValidationError
from .services.obsidian_store import ObsidianStore
from .services.reporting import ReportingService
from .services.schema_manager import SchemaManager
from .skills_catalog import (
    LOGGING_SKILL_NAME,
    ROUTER_SKILL_NAME,
    SCHEMA_INTAKE_SKILL_NAME,
    get_skill_spec,
    list_skill_specs,
)


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


_IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{6,128}$")
_SOURCE_RE = re.compile(r"^[a-z0-9._-]{2,40}$")


def _clean_required_text(value: str, label: str, *, max_len: int = 200) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{label} cannot be empty")
    if len(cleaned) > max_len:
        raise ValidationError(f"{label} exceeds max length {max_len}")
    return cleaned


def _clean_optional_text(value: str | None, label: str, *, max_len: int = 8000) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string or null")
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_len:
        raise ValidationError(f"{label} exceeds max length {max_len}")
    return cleaned


def _clean_idempotency_key(value: str) -> str:
    key = _clean_required_text(value, "idempotency_key", max_len=128)
    if not _IDEMPOTENCY_KEY_RE.match(key):
        raise ValidationError(
            "idempotency_key must match ^[A-Za-z0-9._:-]{6,128}$ (example: codex-machineA-20260411-001)"
        )
    return key


def _clean_source(value: str) -> str:
    source = _clean_required_text(value, "source", max_len=40).lower()
    if not _SOURCE_RE.match(source):
        raise ValidationError("source must match ^[a-z0-9._-]{2,40}$")
    return source


def _clean_tags(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return None
    if not isinstance(tags, list):
        raise ValidationError("tags must be an array of strings")
    normalized: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(tags):
        if not isinstance(item, str):
            raise ValidationError(f"tags[{idx}] must be a string")
        tag = item.strip().lower()
        if not tag:
            continue
        if len(tag) > 48:
            raise ValidationError("each tag must be <= 48 chars")
        if tag not in seen:
            normalized.append(tag)
            seen.add(tag)
    if len(normalized) > 20:
        raise ValidationError("tags cannot exceed 20 items")
    return normalized or None


def _clean_skill_content(value: str, *, max_len: int = 200_000) -> str:
    if not isinstance(value, str):
        raise ValidationError("content must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError("content cannot be empty")
    if len(cleaned) > max_len:
        raise ValidationError(f"content exceeds max length {max_len}")
    return cleaned + "\n"


def _skill_snapshot(skill_name: str, content: str, source: str) -> dict[str, Any]:
    spec = get_skill_spec(skill_name)
    if spec is None:
        raise ValidationError(f"unknown skill_name: {skill_name}")
    return {
        "skill_name": spec.name,
        "version": spec.version,
        "path": spec.canonical_path,
        "source": source,
        "checksum_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


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

    @mcp.tool(
        description=(
            "Create a top-level employer/client record. Use this before creating projects if the employer "
            "does not already exist."
        )
    )
    def create_employer(name: str, description: str | None = None) -> dict[str, Any]:
        name = _clean_required_text(name, "name", max_len=160)
        description = _clean_optional_text(description, "description", max_len=1200)
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

    @mcp.tool(
        description=(
            "Create a project under an existing employer and initialize canonical Obsidian folder structure: "
            "Employers/<Employer>/<Project>/."
        )
    )
    def create_project(
        employer_name: str,
        project_name: str,
        code_name: str | None = None,
        description: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        employer_name = _clean_required_text(employer_name, "employer_name", max_len=160)
        project_name = _clean_required_text(project_name, "project_name", max_len=180)
        code_name = _clean_optional_text(code_name, "code_name", max_len=120)
        description = _clean_optional_text(description, "description", max_len=2000)
        status = _clean_required_text(status, "status", max_len=40).lower()
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

    @mcp.tool(
        description=(
            "Log a coding session in structured form and dual-write to Obsidian markdown. Prefer this for "
            "session updates instead of free-form note writes. Reuse idempotency_key for retries."
        )
    )
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
        employer_name = _clean_required_text(employer_name, "employer_name", max_len=160)
        project_name = _clean_required_text(project_name, "project_name", max_len=180)
        session_title = _clean_required_text(session_title, "session_title", max_len=220)
        idempotency_key = _clean_idempotency_key(idempotency_key)
        source = _clean_source(source)
        objective = _clean_optional_text(objective, "objective")
        summary = _clean_optional_text(summary, "summary")
        thought_process = _clean_optional_text(thought_process, "thought_process")
        methodology = _clean_optional_text(methodology, "methodology")
        major_changes = _clean_optional_text(major_changes, "major_changes")
        advantages = _clean_optional_text(advantages, "advantages")
        disadvantages = _clean_optional_text(disadvantages, "disadvantages")
        blockers = _clean_optional_text(blockers, "blockers")
        next_steps = _clean_optional_text(next_steps, "next_steps")
        learnings = _clean_optional_text(learnings, "learnings")
        skills_updates = _clean_optional_text(skills_updates, "skills_updates")
        tags = _clean_tags(tags)

        parsed_started_at = _parse_datetime(started_at)
        parsed_ended_at = _parse_datetime(ended_at)
        if parsed_started_at is None:
            raise ValidationError("started_at is required and must be ISO-8601")
        if parsed_ended_at and parsed_ended_at < parsed_started_at:
            raise ValidationError("ended_at cannot be earlier than started_at")

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
                    "started_at": parsed_started_at,
                    "ended_at": parsed_ended_at,
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

    @mcp.tool(
        description=(
            "Log a meeting as structured data and generate/update canonical Obsidian meeting note under the "
            "project update folder."
        )
    )
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
        employer_name = _clean_required_text(employer_name, "employer_name", max_len=160)
        project_name = _clean_required_text(project_name, "project_name", max_len=180)
        meeting_title = _clean_required_text(meeting_title, "meeting_title", max_len=220)
        summary = _clean_optional_text(summary, "summary")
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

    @mcp.tool(
        description=(
            "Log an architectural or product decision with rationale/pros/cons and generate a canonical "
            "decision note in Obsidian."
        )
    )
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
        employer_name = _clean_required_text(employer_name, "employer_name", max_len=160)
        project_name = _clean_required_text(project_name, "project_name", max_len=180)
        title = _clean_required_text(title, "title", max_len=220)
        context = _clean_optional_text(context, "context")
        chosen_option = _clean_optional_text(chosen_option, "chosen_option", max_len=1000)
        rationale = _clean_optional_text(rationale, "rationale")
        pros = _clean_optional_text(pros, "pros")
        cons = _clean_optional_text(cons, "cons")
        impact = _clean_optional_text(impact, "impact")
        status = _clean_required_text(status, "status", max_len=40).lower()
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

    @mcp.tool(
        description=(
            "Create a new dynamic table with standard non-destructive columns: id, created_at, updated_at, archived. "
            "Use this instead of raw SQL DDL."
        )
    )
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

    @mcp.tool(description="List registered tables from table_registry. Archived tables are hidden by default.")
    def list_tables(include_archived: bool = False) -> dict[str, Any]:
        return {"tables": schema_manager.list_tables(include_archived=include_archived)}

    @mcp.tool(description="Describe a table's columns/types using gateway-safe introspection.")
    def describe_table(table_name: str) -> dict[str, Any]:
        return schema_manager.describe_table(table_name)

    @mcp.tool(description="Archive a table in registry metadata. Physical DROP TABLE is not supported.")
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

    @mcp.tool(description="Insert rows into a registered table. Gateway will auto-populate standard metadata columns.")
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

    @mcp.tool(description="Update rows by constrained filters. Full-table updates are blocked without filters.")
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

    @mcp.tool(description="Archive rows (soft delete) by setting archived=true using constrained filters.")
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

    @mcp.tool(
        description=(
            "Query rows from a registered table using constrained filters/sort/limit. By default archived rows are "
            "excluded by policy."
        )
    )
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

    @mcp.tool(description="Get cross-entity timeline (sessions, meetings, decisions) for a project.")
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

    @mcp.tool(description="Get project-level summary counts for sessions, meetings, decisions, and open dependencies.")
    def get_project_summary(employer_name: str, project_name: str) -> dict[str, Any]:
        return reporting_service.get_project_summary(employer_name=employer_name, project_name=project_name)

    @mcp.tool(description="List open dependencies for an employer, optionally constrained to a project.")
    def get_open_dependencies(employer_name: str, project_name: str | None = None) -> dict[str, Any]:
        return reporting_service.get_open_dependencies(employer_name=employer_name, project_name=project_name)

    @mcp.tool(description="Read an Obsidian note by relative path within VAULT_ROOT.")
    def get_obsidian_note(path: str) -> dict[str, Any]:
        return obsidian_store.get_note(path)

    @mcp.tool(
        description=(
            "Advanced/manual note write. Prefer structured logging tools (log_coding_session/log_meeting/log_decision) "
            "for canonical formatting and paths."
        )
    )
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

    def _resolve_skill(skill_name: str):
        normalized = _clean_required_text(skill_name, "skill_name", max_len=120).strip().lower()
        spec = get_skill_spec(normalized)
        if spec is None:
            raise ValidationError(f"unknown skill_name: {normalized}")
        return spec

    def _active_skill_snapshot(skill_name: str) -> dict[str, Any]:
        spec = _resolve_skill(skill_name)
        note = obsidian_store.get_note(spec.canonical_path)
        if note["exists"]:
            return _skill_snapshot(spec.name, note["content"], source="vault")
        return _skill_snapshot(spec.name, spec.default_content, source="default")

    def _initialize_skill(
        *,
        skill_name: str,
        force: bool,
    ) -> tuple[dict[str, Any], int, str]:
        spec = _resolve_skill(skill_name)
        existing = obsidian_store.get_note(spec.canonical_path)
        if existing["exists"] and not force:
            data = {
                "initialized": False,
                "path": spec.canonical_path,
                "reason": "already_exists",
                **_skill_snapshot(spec.name, existing["content"], source="vault"),
            }
            return data, 0, spec.canonical_path

        path = obsidian_store.upsert_note(spec.canonical_path, spec.default_content, mode="overwrite")
        current = obsidian_store.get_note(spec.canonical_path)
        data = {
            "initialized": True,
            "path": path,
            "reason": "forced_overwrite" if force and existing["exists"] else "created",
            **_skill_snapshot(spec.name, current["content"], source="vault"),
        }
        return data, 1, path

    def _initialize_skill_mutation(
        *,
        skill_name: str,
        force: bool,
        action_type: str,
    ) -> dict[str, Any]:
        payload = {"skill_name": skill_name, "force": force}

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            data, affected, path = _initialize_skill(skill_name=skill_name, force=force)
            return data, affected, path, skill_name

        return execute_mutation(
            action_type=action_type,
            target_system="obsidian",
            table_name=None,
            payload=payload,
            executor=_exec,
        )

    def _update_skill_mutation(
        *,
        skill_name: str,
        content: str,
        mode: Literal["overwrite", "append"],
        reason: str | None,
        action_type: str,
    ) -> dict[str, Any]:
        spec = _resolve_skill(skill_name)
        normalized_reason = _clean_optional_text(reason, "reason", max_len=500)
        normalized_content = _clean_skill_content(content)
        payload = {
            "skill_name": spec.name,
            "path": spec.canonical_path,
            "mode": mode,
            "reason": normalized_reason,
            "content_len": len(normalized_content),
        }

        def _exec() -> tuple[dict[str, Any], int, str, str]:
            path = obsidian_store.upsert_note(spec.canonical_path, normalized_content, mode=mode)
            current = obsidian_store.get_note(spec.canonical_path)
            data = {
                "path": path,
                "mode": mode,
                "reason": normalized_reason,
                **_skill_snapshot(spec.name, current["content"], source="vault"),
            }
            return data, 1, path, spec.name

        return execute_mutation(
            action_type=action_type,
            target_system="obsidian",
            table_name=None,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool(
        description=(
            "List canonical gateway skill definitions managed by the MCP server. Use this to discover "
            "available skill names, versions, and canonical Obsidian paths."
        )
    )
    def list_gateway_skills() -> dict[str, Any]:
        skills: list[dict[str, Any]] = []
        for spec in list_skill_specs():
            active = _active_skill_snapshot(spec.name)
            skills.append(
                {
                    "skill_name": spec.name,
                    "version": spec.version,
                    "path": spec.canonical_path,
                    "active_source": active["source"],
                    "active_checksum_sha256": active["checksum_sha256"],
                }
            )
        return {"skills": skills, "count": len(skills)}

    @mcp.tool(
        description=(
            "Fetch one canonical gateway skill by name. Returns active content from Obsidian if present, "
            "otherwise returns the server default content."
        )
    )
    def get_gateway_skill(skill_name: str) -> dict[str, Any]:
        return _active_skill_snapshot(skill_name)

    @mcp.tool(
        description=(
            "Initialize a gateway skill in Obsidian at its canonical path. Set force=true to overwrite existing "
            "vault content with server default content."
        )
    )
    def initialize_gateway_skill(skill_name: str, force: bool = False) -> dict[str, Any]:
        return _initialize_skill_mutation(
            skill_name=skill_name,
            force=force,
            action_type="initialize_gateway_skill",
        )

    @mcp.tool(
        description=(
            "Initialize all gateway skills in canonical Obsidian paths. Set force=true to overwrite existing "
            "vault content with server defaults."
        )
    )
    def initialize_gateway_skills(force: bool = False) -> dict[str, Any]:
        payload = {"force": force, "skill_names": [spec.name for spec in list_skill_specs()]}

        def _exec() -> tuple[dict[str, Any], int, None, str]:
            results: list[dict[str, Any]] = []
            affected_total = 0
            for spec in list_skill_specs():
                data, affected, _ = _initialize_skill(skill_name=spec.name, force=force)
                results.append(data)
                affected_total += affected
            return (
                {
                    "force": force,
                    "initialized_count": affected_total,
                    "skipped_count": len(results) - affected_total,
                    "skills": results,
                },
                affected_total,
                None,
                "all_gateway_skills",
            )

        return execute_mutation(
            action_type="initialize_gateway_skills",
            target_system="obsidian",
            table_name=None,
            payload=payload,
            executor=_exec,
        )

    @mcp.tool(
        description=(
            "Update one gateway skill at its canonical Obsidian path. Use this to evolve centralized, "
            "cross-device behavior for all connected coding agents."
        )
    )
    def update_gateway_skill(
        skill_name: str,
        content: str,
        mode: Literal["overwrite", "append"] = "overwrite",
        reason: str | None = None,
    ) -> dict[str, Any]:
        return _update_skill_mutation(
            skill_name=skill_name,
            content=content,
            mode=mode,
            reason=reason,
            action_type="update_gateway_skill",
        )

    @mcp.tool(
        description=(
            "Backward-compatible wrapper for get_gateway_skill('knowledge-gateway-logging')."
        )
    )
    def get_logging_skill() -> dict[str, Any]:
        return get_gateway_skill(LOGGING_SKILL_NAME)

    @mcp.tool(
        description=(
            "Backward-compatible wrapper for initialize_gateway_skill on the logging skill."
        )
    )
    def initialize_logging_skill(force: bool = False) -> dict[str, Any]:
        return _initialize_skill_mutation(
            skill_name=LOGGING_SKILL_NAME,
            force=force,
            action_type="initialize_logging_skill",
        )

    @mcp.tool(
        description=(
            "Backward-compatible wrapper for update_gateway_skill on the logging skill."
        )
    )
    def update_logging_skill(
        content: str,
        mode: Literal["overwrite", "append"] = "overwrite",
        reason: str | None = None,
    ) -> dict[str, Any]:
        return _update_skill_mutation(
            skill_name=LOGGING_SKILL_NAME,
            content=content,
            mode=mode,
            reason=reason,
            action_type="update_logging_skill",
        )

    @mcp.tool(description="Get non-destructive safety policy enforced by the gateway.")
    def get_gateway_policy() -> dict[str, Any]:
        return {
            "destructive_operations": "disabled",
            "row_deletion_policy": "archive_only",
            "table_deletion_policy": "archive_only",
            "drop_table_supported": False,
            "delete_rows_supported": False,
        }

    @mcp.tool(
        description=(
            "Get canonical agent usage rules for this gateway: intent-to-tool mapping, required fields, idempotency "
            "format, and when to avoid free-form note writes."
        )
    )
    def get_usage_playbook() -> dict[str, Any]:
        return {
            "version": "2026-04-19",
            "intent_to_tool": {
                "log this session": "log_coding_session",
                "log meeting": "log_meeting",
                "log decision": "log_decision",
                "read note": "get_obsidian_note",
                "custom note write": "upsert_obsidian_note",
                "list skills": "list_gateway_skills",
                "get skill": "get_gateway_skill",
                "initialize skill": "initialize_gateway_skill",
                "initialize skills": "initialize_gateway_skills",
                "update skill": "update_gateway_skill",
                "get logging skill": "get_logging_skill",
                "initialize logging skill": "initialize_logging_skill",
                "update logging skill": "update_logging_skill",
            },
            "intent_router_protocol": {
                "session_bootstrap": "call get_usage_playbook once per session and cache by version",
                "scope_resolution_model": [
                    "global",
                    "employer_all_projects",
                    "single_project",
                    "multi_employer_or_multi_project",
                ],
                "scope_resolution_policy": "ask_if_missing",
                "clarification_batch_policy": "ask_one_consolidated_question",
                "unknown_intent_policy": "clarify_then_proceed",
                "write_on_ambiguous_intent": False,
                "tool_discovery_policy": "avoid_redundant_discovery_when_playbook_cached",
            },
            "db_intent_mapping": {
                "create database": {
                    "route_to": "create_dynamic_table",
                    "required_clarifications_if_missing": [
                        "scope",
                        "table_purpose",
                        "columns_with_types",
                    ],
                }
            },
            "table_naming_policy": {
                "mode": "auto_prefix_by_scope",
                "global_template": "global_<name>",
                "employer_template": "<employer_slug>_<name>",
                "project_template": "<employer_slug>_<project_slug>_<name>",
            },
            "session_logging_standard": {
                "required_fields": [
                    "employer_name",
                    "project_name",
                    "session_title",
                    "idempotency_key",
                    "started_at",
                ],
                "idempotency_key_regex": "^[A-Za-z0-9._:-]{6,128}$",
                "recommended_idempotency_key": "<agent>-<machine>-<utcstamp>-<seq>",
                "notes": [
                    "Use log_coding_session for normal session updates.",
                    "Reuse the same idempotency_key for retries/replays.",
                    "Use ISO-8601 timestamps (timezone-aware preferred).",
                ],
            },
            "write_policy": {
                "prefer_structured_tools": True,
                "upsert_obsidian_note": "manual_or_exception_only",
                "non_destructive": True,
                "row_delete_mode": "archive_only",
                "table_delete_mode": "archive_only",
            },
            "skill_suite": {
                "source_of_truth": "mcp_hosted_vault_skills",
                "names": [
                    LOGGING_SKILL_NAME,
                    ROUTER_SKILL_NAME,
                    SCHEMA_INTAKE_SKILL_NAME,
                ],
                "management_tools": [
                    "list_gateway_skills",
                    "get_gateway_skill",
                    "initialize_gateway_skill",
                    "initialize_gateway_skills",
                    "update_gateway_skill",
                ],
                "backward_compatible_wrappers": [
                    "get_logging_skill",
                    "initialize_logging_skill",
                    "update_logging_skill",
                ],
            },
        }

    return mcp
