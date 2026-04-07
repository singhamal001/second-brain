from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

from .db_store import DBStore
from .errors import AuthError


@dataclass
class AuthResult:
    client_id: str
    client_code: str
    label: str | None


class AuthService:
    def __init__(self, db_store: DBStore, api_key_pepper: str) -> None:
        self.db_store = db_store
        self.api_key_pepper = api_key_pepper

    def hash_api_key(self, api_key: str) -> str:
        return hashlib.sha256(f"{self.api_key_pepper}:{api_key}".encode("utf-8")).hexdigest()

    def verify(self, api_key: str | None, client_code: str | None) -> AuthResult:
        if not api_key:
            raise AuthError("missing bearer api key")
        key_hash = self.hash_api_key(api_key)
        client = self.db_store.get_api_client(key_hash=key_hash, client_code=client_code)
        if not client:
            raise AuthError("invalid API key")
        if not client["active"]:
            raise AuthError("client inactive")
        if client["revoked"]:
            raise AuthError("client revoked")
        if client_code and not hmac.compare_digest(str(client["client_code"]), str(client_code)):
            raise AuthError("client code mismatch")
        return AuthResult(client_id=client["id"], client_code=client["client_code"], label=client.get("label"))

    def provision_client(self, client_code: str, raw_api_key: str, label: str | None = None) -> dict[str, Any]:
        key_hash = self.hash_api_key(raw_api_key)
        return self.db_store.register_api_client(client_code=client_code, key_hash=key_hash, label=label)
