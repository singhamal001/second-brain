from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestAuthContext:
    client_id: str
    client_code: str
    label: str | None


current_auth_context: ContextVar[RequestAuthContext | None] = ContextVar("current_auth_context", default=None)
