from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)


def build_metadata(schema: str | None = None) -> tuple[MetaData, dict[str, Table]]:
    resolved_schema = None if schema in (None, "", "public") else schema
    metadata = MetaData(schema=resolved_schema)

    api_clients = Table(
        "api_clients",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("client_code", String(10), nullable=False, index=True),
        Column("label", String(120), nullable=True),
        Column("key_hash", String(128), nullable=False, unique=True),
        Column("active", Boolean, nullable=False, default=True),
        Column("revoked", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("client_code", name="uq_api_clients_code"),
    )

    table_registry = Table(
        "table_registry",
        metadata,
        Column("table_name", String(128), primary_key=True),
        Column("description", Text, nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    activity_log = Table(
        "activity_log",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("operation_id", String(36), nullable=False, index=True),
        Column("action_type", String(120), nullable=False),
        Column("source_system", String(80), nullable=False),
        Column("target_system", String(80), nullable=False),
        Column("table_name", String(128), nullable=True),
        Column("record_identifier", String(120), nullable=True),
        Column("client_code", String(10), nullable=True),
        Column("payload_hash", String(64), nullable=False),
        Column("status", String(40), nullable=False),
        Column("error_message", Text, nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )

    employers = Table(
        "employers",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("name", String(160), nullable=False),
        Column("description", Text, nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("name", name="uq_employers_name"),
    )

    projects = Table(
        "projects",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("employer_id", String(36), ForeignKey("employers.id"), nullable=False, index=True),
        Column("name", String(160), nullable=False),
        Column("code_name", String(80), nullable=True),
        Column("description", Text, nullable=True),
        Column("status", String(50), nullable=False, default="active"),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("employer_id", "name", name="uq_projects_employer_name"),
    )

    sessions = Table(
        "sessions",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("project_id", String(36), ForeignKey("projects.id"), nullable=False, index=True),
        Column("employer_id", String(36), ForeignKey("employers.id"), nullable=False, index=True),
        Column("idempotency_key", String(120), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("ended_at", DateTime(timezone=True), nullable=True),
        Column("source", String(60), nullable=False, default="codex"),
        Column("title", String(200), nullable=False),
        Column("objective", Text, nullable=True),
        Column("summary", Text, nullable=True),
        Column("thought_process", Text, nullable=True),
        Column("methodology", Text, nullable=True),
        Column("major_changes", Text, nullable=True),
        Column("advantages", Text, nullable=True),
        Column("disadvantages", Text, nullable=True),
        Column("blockers", Text, nullable=True),
        Column("next_steps", Text, nullable=True),
        Column("learnings", Text, nullable=True),
        Column("skills_updates", Text, nullable=True),
        Column("tags_json", JSON, nullable=True),
        Column("obsidian_note_path", String(400), nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("project_id", "idempotency_key", name="uq_sessions_project_idem"),
    )

    meetings = Table(
        "meetings",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("project_id", String(36), ForeignKey("projects.id"), nullable=False, index=True),
        Column("employer_id", String(36), ForeignKey("employers.id"), nullable=False, index=True),
        Column("meeting_datetime", DateTime(timezone=True), nullable=False),
        Column("title", String(200), nullable=False),
        Column("summary", Text, nullable=True),
        Column("attendees_json", JSON, nullable=True),
        Column("decisions_json", JSON, nullable=True),
        Column("next_steps_json", JSON, nullable=True),
        Column("dependencies_json", JSON, nullable=True),
        Column("commitments_json", JSON, nullable=True),
        Column("obsidian_note_path", String(400), nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    decisions = Table(
        "decisions",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("project_id", String(36), ForeignKey("projects.id"), nullable=False, index=True),
        Column("employer_id", String(36), ForeignKey("employers.id"), nullable=False, index=True),
        Column("title", String(200), nullable=False),
        Column("context", Text, nullable=True),
        Column("chosen_option", Text, nullable=True),
        Column("rejected_options_json", JSON, nullable=True),
        Column("rationale", Text, nullable=True),
        Column("pros", Text, nullable=True),
        Column("cons", Text, nullable=True),
        Column("impact", Text, nullable=True),
        Column("status", String(50), nullable=False, default="active"),
        Column("obsidian_note_path", String(400), nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    dependencies = Table(
        "dependencies",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("project_id", String(36), ForeignKey("projects.id"), nullable=False, index=True),
        Column("employer_id", String(36), ForeignKey("employers.id"), nullable=False, index=True),
        Column("title", String(200), nullable=False),
        Column("description", Text, nullable=True),
        Column("owner_person", String(160), nullable=True),
        Column("status", String(50), nullable=False, default="open"),
        Column("due_date", DateTime(timezone=True), nullable=True),
        Column("related_meeting_id", String(36), nullable=True),
        Column("archived", Boolean, nullable=False, default=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )

    tables = {
        "api_clients": api_clients,
        "table_registry": table_registry,
        "activity_log": activity_log,
        "employers": employers,
        "projects": projects,
        "sessions": sessions,
        "meetings": meetings,
        "decisions": decisions,
        "dependencies": dependencies,
    }

    return metadata, tables
