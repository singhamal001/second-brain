from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


class AuditService:
    def __init__(self, db_store: "DBStore") -> None:
        self.db_store = db_store

    @staticmethod
    def payload_hash(payload: Any) -> str:
        data = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def record(
        self,
        *,
        operation_id: str,
        action_type: str,
        source_system: str,
        target_system: str,
        table_name: str | None,
        record_identifier: str | None,
        client_code: str | None,
        payload: Any,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.db_store.log_activity(
            {
                "id": str(uuid.uuid4()),
                "operation_id": operation_id,
                "action_type": action_type,
                "source_system": source_system,
                "target_system": target_system,
                "table_name": table_name,
                "record_identifier": record_identifier,
                "client_code": client_code,
                "payload_hash": self.payload_hash(payload),
                "status": status,
                "error_message": error_message,
                "created_at": datetime.now(timezone.utc),
            }
        )


from .db_store import DBStore  # noqa: E402
