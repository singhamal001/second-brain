from __future__ import annotations

import pytest

from knowledge_gateway.services.errors import ConflictError, ValidationError


def test_dynamic_table_create_and_duplicate(app):
    db = app.state.db_store

    created = db.create_dynamic_table(
        table_name="work_items",
        description="Work item registry",
        columns=[
            {"name": "title", "type": "string", "nullable": False},
            {"name": "priority", "type": "int", "nullable": True},
        ],
    )

    assert created["table_name"] == "work_items"
    listed = db.list_tables()
    assert any(t["table_name"] == "work_items" for t in listed)

    with pytest.raises(ConflictError):
        db.create_dynamic_table(
            table_name="work_items",
            description="duplicate",
            columns=[{"name": "title", "type": "string", "nullable": True}],
        )


def test_reject_reserved_column_names(app):
    db = app.state.db_store
    with pytest.raises(ValidationError):
        db.create_dynamic_table(
            table_name="bad_table",
            description="bad",
            columns=[{"name": "archived", "type": "bool", "nullable": True}],
        )
