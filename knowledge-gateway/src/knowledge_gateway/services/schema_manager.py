from __future__ import annotations

from typing import Any

from .db_store import DBStore


class SchemaManager:
    """Controls dynamic table lifecycle with non-destructive policy."""

    def __init__(self, db_store: DBStore) -> None:
        self.db_store = db_store

    def create_dynamic_table(self, table_name: str, description: str, columns: list[dict[str, Any]]) -> dict[str, Any]:
        return self.db_store.create_dynamic_table(table_name=table_name, description=description, columns=columns)

    def list_tables(self, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.db_store.list_tables(include_archived=include_archived)

    def describe_table(self, table_name: str) -> dict[str, Any]:
        return self.db_store.describe_table(table_name)

    def archive_table(self, table_name: str) -> dict[str, Any]:
        return self.db_store.archive_table(table_name)
