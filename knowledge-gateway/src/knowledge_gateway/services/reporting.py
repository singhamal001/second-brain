from __future__ import annotations

from datetime import datetime

from .db_store import DBStore


class ReportingService:
    def __init__(self, db_store: DBStore) -> None:
        self.db_store = db_store

    def get_project_timeline(
        self,
        employer_name: str,
        project_name: str,
        from_dt: datetime | None,
        to_dt: datetime | None,
        limit: int,
    ) -> dict:
        return self.db_store.get_project_timeline(
            employer_name=employer_name,
            project_name=project_name,
            from_dt=from_dt,
            to_dt=to_dt,
            limit=limit,
        )

    def get_project_summary(self, employer_name: str, project_name: str) -> dict:
        return self.db_store.get_project_summary(employer_name=employer_name, project_name=project_name)

    def get_open_dependencies(self, employer_name: str, project_name: str | None) -> dict:
        return self.db_store.get_open_dependencies(employer_name=employer_name, project_name=project_name)
