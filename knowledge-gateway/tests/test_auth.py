from __future__ import annotations

from sqlalchemy import update

from knowledge_gateway.app import create_app
from knowledge_gateway.config import get_settings


def test_mcp_requires_auth(client):
    response = client.get("/mcp")
    assert response.status_code == 401


def test_mcp_accepts_valid_api_key(client, api_key):
    response = client.get("/mcp", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code != 401


def test_mcp_rejects_invalid_key(client):
    response = client.get("/mcp", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_mcp_rejects_revoked_client(app, client, api_key):
    api_clients = app.state.db_store.tables["api_clients"]
    with app.state.db_store.engine.begin() as conn:
        conn.execute(
            update(api_clients)
            .where(api_clients.c.client_code == "1234567890")
            .values(revoked=True)
        )

    response = client.get("/mcp", headers={"Authorization": f"Bearer {api_key}"})
    assert response.status_code == 401


def test_cloudflare_header_enforced(tmp_path, monkeypatch):
    db_path = tmp_path / "cf.db"
    vault_path = tmp_path / "vault"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VAULT_ROOT", str(vault_path))
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")
    monkeypatch.setenv("REQUIRE_CLOUDFLARE_ACCESS", "true")
    monkeypatch.setenv("ALLOW_CF_BYPASS_FOR_LOCAL", "false")

    get_settings.cache_clear()
    app = create_app()
    auth = app.state.auth_service
    auth.provision_client(client_code="1234567890", raw_api_key="secret", label="cf")

    from fastapi.testclient import TestClient

    test_client = TestClient(app)

    no_cf = test_client.get("/mcp", headers={"Authorization": "Bearer secret"})
    assert no_cf.status_code == 403

    with_cf = test_client.get(
        "/mcp",
        headers={
            "Authorization": "Bearer secret",
            "Cf-Access-Jwt-Assertion": "dummy",
            "X-Client-Code": "1234567890",
        },
    )
    assert with_cf.status_code != 403
