from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    func,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from ..models.schema import build_metadata
from .errors import ConflictError, NotFoundError, ValidationError

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
_RESERVED_COLUMNS = {"id", "created_at", "updated_at", "archived"}
_ALLOWED_FILTER_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "like", "in"}
_TYPE_MAP = {
    "text": Text,
    "string": String(255),
    "int": Integer,
    "float": Float,
    "bool": Boolean,
    "datetime": DateTime(timezone=True),
    "json": JSON,
}


class DBStore:
    def __init__(self, database_url: str, app_schema: str = "public") -> None:
        self.database_url = database_url
        self.app_schema = app_schema
        self.engine: Engine = create_engine(database_url, future=True)
        self.metadata, self.tables = build_metadata(app_schema)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _validate_identifier(value: str, label: str) -> str:
        if not _IDENTIFIER_RE.match(value):
            raise ValidationError(f"{label} must match regex: {_IDENTIFIER_RE.pattern}")
        return value

    @property
    def _schema_arg(self) -> str | None:
        return None if self.app_schema in ("", "public") else self.app_schema

    def initialize(self) -> None:
        with self.engine.begin() as conn:
            if self._schema_arg and conn.dialect.name == "postgresql":
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema_arg}"'))
            self.metadata.create_all(conn)
        self._seed_table_registry()

    def _table_exists(self, table_name: str) -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name, schema=self._schema_arg)

    def _seed_table_registry(self) -> None:
        core = {
            "employers": "Employer registry",
            "projects": "Project registry",
            "sessions": "Coding session logs",
            "meetings": "Meeting logs",
            "decisions": "Decision register",
            "dependencies": "Open and closed dependencies",
            "activity_log": "Mutation audit log",
            "api_clients": "API clients and credentials",
            "table_registry": "Master table registry",
        }
        now = self._now()
        with self.engine.begin() as conn:
            for table_name, description in core.items():
                existing = conn.execute(
                    select(self.tables["table_registry"].c.table_name).where(
                        self.tables["table_registry"].c.table_name == table_name
                    )
                ).first()
                if existing:
                    continue
                conn.execute(
                    self.tables["table_registry"].insert().values(
                        table_name=table_name,
                        description=description,
                        archived=False,
                        created_at=now,
                        updated_at=now,
                    )
                )

    def log_activity(self, payload: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.tables["activity_log"].insert().values(**payload))

    def register_api_client(self, client_code: str, key_hash: str, label: str | None = None) -> dict[str, Any]:
        now = self._now()
        row = {
            "id": str(uuid.uuid4()),
            "client_code": client_code,
            "label": label,
            "key_hash": key_hash,
            "active": True,
            "revoked": False,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(self.tables["api_clients"].c.id).where(
                    self.tables["api_clients"].c.client_code == client_code
                )
            ).first()
            if existing:
                conn.execute(
                    update(self.tables["api_clients"])
                    .where(self.tables["api_clients"].c.client_code == client_code)
                    .values(key_hash=key_hash, label=label, active=True, revoked=False, updated_at=now)
                )
                row["id"] = existing.id
            else:
                conn.execute(self.tables["api_clients"].insert().values(**row))
        return row

    def get_api_client(self, key_hash: str, client_code: str | None = None) -> dict[str, Any] | None:
        filters = [self.tables["api_clients"].c.key_hash == key_hash]
        if client_code:
            filters.append(self.tables["api_clients"].c.client_code == client_code)
        stmt = select(self.tables["api_clients"]).where(and_(*filters))
        with self.engine.begin() as conn:
            result = conn.execute(stmt).mappings().first()
        return dict(result) if result else None

    def create_employer(self, name: str, description: str | None) -> dict[str, Any]:
        now = self._now()
        row = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "description": description,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(self.tables["employers"].insert().values(**row))
        except IntegrityError as exc:
            raise ConflictError(f"employer already exists: {name}") from exc
        return row

    def _resolve_employer(self, employer_name: str) -> dict[str, Any]:
        stmt = select(self.tables["employers"]).where(
            and_(
                self.tables["employers"].c.name == employer_name,
                self.tables["employers"].c.archived.is_(False),
            )
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            raise NotFoundError(f"employer not found: {employer_name}")
        return dict(row)

    def _resolve_project(self, employer_id: str, project_name: str) -> dict[str, Any]:
        stmt = select(self.tables["projects"]).where(
            and_(
                self.tables["projects"].c.employer_id == employer_id,
                self.tables["projects"].c.name == project_name,
                self.tables["projects"].c.archived.is_(False),
            )
        )
        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            raise NotFoundError(f"project not found: {project_name}")
        return dict(row)

    def create_project(
        self,
        employer_name: str,
        name: str,
        code_name: str | None,
        description: str | None,
        status: str,
    ) -> dict[str, Any]:
        employer = self._resolve_employer(employer_name)
        now = self._now()
        row = {
            "id": str(uuid.uuid4()),
            "employer_id": employer["id"],
            "name": name.strip(),
            "code_name": code_name,
            "description": description,
            "status": status,
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(self.tables["projects"].insert().values(**row))
        except IntegrityError as exc:
            raise ConflictError(f"project already exists: {name}") from exc
        row["employer_name"] = employer_name
        return row

    def create_dynamic_table(self, table_name: str, description: str, columns: list[dict[str, Any]]) -> dict[str, Any]:
        table_name = self._validate_identifier(table_name, "table_name")
        if table_name in self.tables:
            raise ConflictError("cannot redefine core table")
        if self._table_exists(table_name):
            raise ConflictError(f"table already exists: {table_name}")

        seen: set[str] = set()
        sql_columns = [
            Column("id", String(36), primary_key=True),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            Column("archived", Boolean, nullable=False, default=False),
        ]

        for spec in columns:
            raw_name = spec.get("name")
            if not isinstance(raw_name, str):
                raise ValidationError("column name must be provided")
            name = self._validate_identifier(raw_name, "column name")
            if name in seen or name in _RESERVED_COLUMNS:
                raise ValidationError(f"invalid or duplicate column name: {name}")
            seen.add(name)
            raw_type = str(spec.get("type", "text")).lower()
            if raw_type not in _TYPE_MAP:
                raise ValidationError(f"unsupported column type: {raw_type}")
            nullable = bool(spec.get("nullable", True))
            sql_columns.append(Column(name, _TYPE_MAP[raw_type], nullable=nullable))

        dynamic_metadata = MetaData(schema=self._schema_arg)
        dynamic_table = Table(table_name, dynamic_metadata, *sql_columns)
        now = self._now()
        with self.engine.begin() as conn:
            dynamic_metadata.create_all(conn)
            conn.execute(
                self.tables["table_registry"].insert().values(
                    table_name=table_name,
                    description=description,
                    archived=False,
                    created_at=now,
                    updated_at=now,
                )
            )
        return {
            "table_name": table_name,
            "description": description,
            "columns": ["id", "created_at", "updated_at", "archived", *list(seen)],
        }

    def list_tables(self, include_archived: bool = False) -> list[dict[str, Any]]:
        stmt = select(self.tables["table_registry"]).order_by(self.tables["table_registry"].c.table_name.asc())
        if not include_archived:
            stmt = stmt.where(self.tables["table_registry"].c.archived.is_(False))
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def _ensure_registered_table(self, table_name: str, allow_archived: bool = False) -> None:
        stmt = select(self.tables["table_registry"]).where(self.tables["table_registry"].c.table_name == table_name)
        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            raise NotFoundError(f"table not registered: {table_name}")
        if row["archived"] and not allow_archived:
            raise ValidationError(f"table is archived: {table_name}")

    def describe_table(self, table_name: str) -> dict[str, Any]:
        self._ensure_registered_table(table_name, allow_archived=True)
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name, schema=self._schema_arg)
        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": c.get("nullable", True),
                    "default": c.get("default"),
                }
                for c in columns
            ],
        }

    def archive_table(self, table_name: str) -> dict[str, Any]:
        now = self._now()
        with self.engine.begin() as conn:
            result = conn.execute(
                update(self.tables["table_registry"])
                .where(self.tables["table_registry"].c.table_name == table_name)
                .values(archived=True, updated_at=now)
            )
        if result.rowcount == 0:
            raise NotFoundError(f"table not found: {table_name}")
        return {"table_name": table_name, "archived": True}

    def _load_runtime_table(self, table_name: str) -> Table:
        self._ensure_registered_table(table_name)
        dynamic_metadata = MetaData(schema=self._schema_arg)
        return Table(table_name, dynamic_metadata, autoload_with=self.engine)

    def _apply_filters(self, table: Table, filters: list[dict[str, Any]] | None) -> Any:
        conditions = []
        if "archived" in table.c:
            conditions.append(table.c.archived.is_(False))
        for raw in filters or []:
            column_name = raw.get("column")
            op = raw.get("op", "eq")
            value = raw.get("value")
            if column_name not in table.c:
                raise ValidationError(f"unknown filter column: {column_name}")
            if op not in _ALLOWED_FILTER_OPS:
                raise ValidationError(f"unsupported filter op: {op}")
            col = table.c[column_name]
            if op == "eq":
                conditions.append(col == value)
            elif op == "neq":
                conditions.append(col != value)
            elif op == "gt":
                conditions.append(col > value)
            elif op == "gte":
                conditions.append(col >= value)
            elif op == "lt":
                conditions.append(col < value)
            elif op == "lte":
                conditions.append(col <= value)
            elif op == "like":
                conditions.append(col.like(value))
            elif op == "in":
                if not isinstance(value, list):
                    raise ValidationError("in operator value must be list")
                conditions.append(col.in_(value))
        return and_(*conditions) if conditions else None

    def insert_rows(self, table_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            raise ValidationError("rows cannot be empty")
        table = self._load_runtime_table(table_name)
        now = self._now()
        payload = []
        for row in rows:
            current = dict(row)
            if "id" in table.c and not current.get("id"):
                current["id"] = str(uuid.uuid4())
            if "created_at" in table.c and not current.get("created_at"):
                current["created_at"] = now
            if "updated_at" in table.c:
                current["updated_at"] = now
            if "archived" in table.c and "archived" not in current:
                current["archived"] = False
            payload.append(current)

        with self.engine.begin() as conn:
            conn.execute(table.insert().values(payload))
        return {"table_name": table_name, "affected_records": len(payload)}

    def update_rows(
        self,
        table_name: str,
        values: dict[str, Any],
        filters: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        table = self._load_runtime_table(table_name)
        if not filters:
            raise ValidationError("filters are required for update_rows")
        if "updated_at" in table.c:
            values = {**values, "updated_at": self._now()}
        condition = self._apply_filters(table, filters)
        stmt = update(table).values(**values)
        if condition is not None:
            stmt = stmt.where(condition)
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
        return {"table_name": table_name, "affected_records": result.rowcount}

    def archive_rows(self, table_name: str, filters: list[dict[str, Any]]) -> dict[str, Any]:
        table = self._load_runtime_table(table_name)
        if "archived" not in table.c:
            raise ValidationError("table has no archived column")
        return self.update_rows(table_name, {"archived": True}, filters)

    def query_rows(
        self,
        table_name: str,
        filters: list[dict[str, Any]] | None,
        sort: list[dict[str, str]] | None,
        limit: int,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 1000:
            raise ValidationError("limit must be between 1 and 1000")
        table = self._load_runtime_table(table_name)
        stmt = select(table)
        condition = self._apply_filters(table, filters)
        if condition is not None:
            stmt = stmt.where(condition)

        for sort_item in sort or []:
            column_name = sort_item.get("column")
            direction = str(sort_item.get("direction", "asc")).lower()
            if column_name not in table.c:
                raise ValidationError(f"unknown sort column: {column_name}")
            if direction not in {"asc", "desc"}:
                raise ValidationError("sort direction must be asc or desc")
            column = table.c[column_name]
            stmt = stmt.order_by(column.desc() if direction == "desc" else column.asc())

        stmt = stmt.limit(limit)
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return {"table_name": table_name, "rows": [dict(row) for row in rows], "count": len(rows)}

    def log_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        employer = self._resolve_employer(payload["employer_name"])
        project = self._resolve_project(employer["id"], payload["project_name"])

        now = self._now()
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(self.tables["sessions"])
                .where(self.tables["sessions"].c.project_id == project["id"])
                .where(self.tables["sessions"].c.idempotency_key == payload["idempotency_key"])
            ).mappings().first()
            if existing:
                data = dict(existing)
                data["existing"] = True
                data["project_name"] = project["name"]
                data["employer_name"] = employer["name"]
                return data

            row = {
                "id": str(uuid.uuid4()),
                "project_id": project["id"],
                "employer_id": employer["id"],
                "idempotency_key": payload["idempotency_key"],
                "started_at": payload["started_at"],
                "ended_at": payload.get("ended_at"),
                "source": payload.get("source", "codex"),
                "title": payload["title"],
                "objective": payload.get("objective"),
                "summary": payload.get("summary"),
                "thought_process": payload.get("thought_process"),
                "methodology": payload.get("methodology"),
                "major_changes": payload.get("major_changes"),
                "advantages": payload.get("advantages"),
                "disadvantages": payload.get("disadvantages"),
                "blockers": payload.get("blockers"),
                "next_steps": payload.get("next_steps"),
                "learnings": payload.get("learnings"),
                "skills_updates": payload.get("skills_updates"),
                "tags_json": payload.get("tags"),
                "obsidian_note_path": payload.get("obsidian_note_path"),
                "archived": False,
                "created_at": now,
                "updated_at": now,
            }
            conn.execute(self.tables["sessions"].insert().values(**row))

        row["existing"] = False
        row["project_name"] = project["name"]
        row["employer_name"] = employer["name"]
        return row

    def update_session_note_path(self, session_id: str, obsidian_note_path: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tables["sessions"])
                .where(self.tables["sessions"].c.id == session_id)
                .values(obsidian_note_path=obsidian_note_path, updated_at=self._now())
            )

    def log_meeting(self, payload: dict[str, Any]) -> dict[str, Any]:
        employer = self._resolve_employer(payload["employer_name"])
        project = self._resolve_project(employer["id"], payload["project_name"])
        now = self._now()
        row = {
            "id": str(uuid.uuid4()),
            "project_id": project["id"],
            "employer_id": employer["id"],
            "meeting_datetime": payload["meeting_datetime"],
            "title": payload["title"],
            "summary": payload.get("summary"),
            "attendees_json": payload.get("attendees"),
            "decisions_json": payload.get("decisions"),
            "next_steps_json": payload.get("next_steps"),
            "dependencies_json": payload.get("dependencies"),
            "commitments_json": payload.get("commitments"),
            "obsidian_note_path": payload.get("obsidian_note_path"),
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(self.tables["meetings"].insert().values(**row))
        row["project_name"] = project["name"]
        row["employer_name"] = employer["name"]
        return row

    def update_meeting_note_path(self, meeting_id: str, obsidian_note_path: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tables["meetings"])
                .where(self.tables["meetings"].c.id == meeting_id)
                .values(obsidian_note_path=obsidian_note_path, updated_at=self._now())
            )

    def log_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        employer = self._resolve_employer(payload["employer_name"])
        project = self._resolve_project(employer["id"], payload["project_name"])
        now = self._now()
        row = {
            "id": str(uuid.uuid4()),
            "project_id": project["id"],
            "employer_id": employer["id"],
            "title": payload["title"],
            "context": payload.get("context"),
            "chosen_option": payload.get("chosen_option"),
            "rejected_options_json": payload.get("rejected_options"),
            "rationale": payload.get("rationale"),
            "pros": payload.get("pros"),
            "cons": payload.get("cons"),
            "impact": payload.get("impact"),
            "status": payload.get("status", "active"),
            "obsidian_note_path": payload.get("obsidian_note_path"),
            "archived": False,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(self.tables["decisions"].insert().values(**row))
        row["project_name"] = project["name"]
        row["employer_name"] = employer["name"]
        return row

    def update_decision_note_path(self, decision_id: str, obsidian_note_path: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tables["decisions"])
                .where(self.tables["decisions"].c.id == decision_id)
                .values(obsidian_note_path=obsidian_note_path, updated_at=self._now())
            )

    def get_project_timeline(
        self,
        employer_name: str,
        project_name: str,
        from_dt: datetime | None,
        to_dt: datetime | None,
        limit: int,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 2000:
            raise ValidationError("limit must be between 1 and 2000")
        employer = self._resolve_employer(employer_name)
        project = self._resolve_project(employer["id"], project_name)

        events: list[dict[str, Any]] = []
        with self.engine.begin() as conn:
            sessions_stmt = select(self.tables["sessions"]).where(
                and_(
                    self.tables["sessions"].c.project_id == project["id"],
                    self.tables["sessions"].c.archived.is_(False),
                )
            )
            meetings_stmt = select(self.tables["meetings"]).where(
                and_(
                    self.tables["meetings"].c.project_id == project["id"],
                    self.tables["meetings"].c.archived.is_(False),
                )
            )
            decisions_stmt = select(self.tables["decisions"]).where(
                and_(
                    self.tables["decisions"].c.project_id == project["id"],
                    self.tables["decisions"].c.archived.is_(False),
                )
            )

            if from_dt:
                sessions_stmt = sessions_stmt.where(self.tables["sessions"].c.started_at >= from_dt)
                meetings_stmt = meetings_stmt.where(self.tables["meetings"].c.meeting_datetime >= from_dt)
                decisions_stmt = decisions_stmt.where(self.tables["decisions"].c.created_at >= from_dt)
            if to_dt:
                sessions_stmt = sessions_stmt.where(self.tables["sessions"].c.started_at <= to_dt)
                meetings_stmt = meetings_stmt.where(self.tables["meetings"].c.meeting_datetime <= to_dt)
                decisions_stmt = decisions_stmt.where(self.tables["decisions"].c.created_at <= to_dt)

            session_rows = conn.execute(sessions_stmt).mappings().all()
            meeting_rows = conn.execute(meetings_stmt).mappings().all()
            decision_rows = conn.execute(decisions_stmt).mappings().all()

        events.extend(
            {
                "event_type": "session",
                "event_at": row["started_at"],
                "record_id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "obsidian_note_path": row["obsidian_note_path"],
            }
            for row in session_rows
        )
        events.extend(
            {
                "event_type": "meeting",
                "event_at": row["meeting_datetime"],
                "record_id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "obsidian_note_path": row["obsidian_note_path"],
            }
            for row in meeting_rows
        )
        events.extend(
            {
                "event_type": "decision",
                "event_at": row["created_at"],
                "record_id": row["id"],
                "title": row["title"],
                "summary": row["rationale"],
                "obsidian_note_path": row["obsidian_note_path"],
            }
            for row in decision_rows
        )

        events.sort(key=lambda row: row["event_at"], reverse=True)
        return {
            "employer_name": employer_name,
            "project_name": project_name,
            "events": events[:limit],
            "count": min(len(events), limit),
        }

    def get_project_summary(self, employer_name: str, project_name: str) -> dict[str, Any]:
        employer = self._resolve_employer(employer_name)
        project = self._resolve_project(employer["id"], project_name)

        with self.engine.begin() as conn:
            sessions_count = conn.execute(
                select(func.count())
                .select_from(self.tables["sessions"])
                .where(self.tables["sessions"].c.project_id == project["id"])
                .where(self.tables["sessions"].c.archived.is_(False))
            ).scalar_one()
            meetings_count = conn.execute(
                select(func.count())
                .select_from(self.tables["meetings"])
                .where(self.tables["meetings"].c.project_id == project["id"])
                .where(self.tables["meetings"].c.archived.is_(False))
            ).scalar_one()
            decisions_count = conn.execute(
                select(func.count())
                .select_from(self.tables["decisions"])
                .where(self.tables["decisions"].c.project_id == project["id"])
                .where(self.tables["decisions"].c.archived.is_(False))
            ).scalar_one()
            open_dependencies = conn.execute(
                select(func.count())
                .select_from(self.tables["dependencies"])
                .where(self.tables["dependencies"].c.project_id == project["id"])
                .where(self.tables["dependencies"].c.archived.is_(False))
                .where(self.tables["dependencies"].c.status.not_in(["closed", "done", "resolved"]))
            ).scalar_one()

        return {
            "employer_name": employer_name,
            "project_name": project_name,
            "summary": {
                "sessions": sessions_count,
                "meetings": meetings_count,
                "decisions": decisions_count,
                "open_dependencies": open_dependencies,
            },
        }

    def get_open_dependencies(self, employer_name: str, project_name: str | None = None) -> dict[str, Any]:
        employer = self._resolve_employer(employer_name)
        stmt = select(self.tables["dependencies"]).where(
            and_(
                self.tables["dependencies"].c.employer_id == employer["id"],
                self.tables["dependencies"].c.archived.is_(False),
                self.tables["dependencies"].c.status.not_in(["closed", "done", "resolved"]),
            )
        )
        if project_name:
            project = self._resolve_project(employer["id"], project_name)
            stmt = stmt.where(self.tables["dependencies"].c.project_id == project["id"])
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return {
            "employer_name": employer_name,
            "project_name": project_name,
            "dependencies": [dict(row) for row in rows],
            "count": len(rows),
        }
