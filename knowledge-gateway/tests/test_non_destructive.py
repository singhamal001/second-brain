from __future__ import annotations


def test_archive_table_and_rows(app):
    db = app.state.db_store

    db.create_dynamic_table(
        table_name="notes_custom",
        description="Custom notes",
        columns=[{"name": "title", "type": "string", "nullable": False}],
    )

    insert_result = db.insert_rows("notes_custom", [{"title": "first"}, {"title": "second"}])
    assert insert_result["affected_records"] == 2

    archive_result = db.archive_rows("notes_custom", [{"column": "title", "op": "eq", "value": "first"}])
    assert archive_result["affected_records"] == 1

    rows = db.query_rows("notes_custom", filters=None, sort=None, limit=10)
    assert rows["count"] == 1
    assert rows["rows"][0]["title"] == "second"

    table_archive = db.archive_table("notes_custom")
    assert table_archive["archived"] is True
