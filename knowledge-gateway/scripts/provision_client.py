from __future__ import annotations

import argparse
import secrets

from knowledge_gateway.config import get_settings
from knowledge_gateway.services.auth import AuthService
from knowledge_gateway.services.db_store import DBStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision or rotate an API client")
    parser.add_argument("--client-code", required=True, help="10 digit client code")
    parser.add_argument("--label", default=None)
    parser.add_argument("--api-key", default=None, help="Optional pre-generated API key")
    args = parser.parse_args()

    settings = get_settings()
    db = DBStore(settings.database_url, app_schema=settings.app_schema)
    db.initialize()
    auth = AuthService(db_store=db, api_key_pepper=settings.api_key_pepper)

    raw_key = args.api_key or secrets.token_urlsafe(32)
    record = auth.provision_client(client_code=args.client_code, raw_api_key=raw_key, label=args.label)

    print("Client provisioned")
    print(f"client_code={record['client_code']}")
    print(f"client_id={record['id']}")
    print(f"api_key={raw_key}")


if __name__ == "__main__":
    main()
