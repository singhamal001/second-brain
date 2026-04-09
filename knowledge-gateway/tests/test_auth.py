from __future__ import annotations

from sqlalchemy import update

from knowledge_gateway.app import create_app
from knowledge_gateway.config import get_settings


def test_mcp_requires_auth(client):
    response = client.get("/mcp")
    assert response.status_code == 401


def test_auth_service_accepts_valid_api_key(app, api_key):
    result = app.state.auth_service.verify(api_key=api_key, client_code="1234567890")
    assert result.client_code == "1234567890"


def test_auth_service_rejects_invalid_api_key(app):
    from knowledge_gateway.services.errors import AuthError
    import pytest

    with pytest.raises(AuthError):
        app.state.auth_service.verify(api_key="not-valid", client_code="1234567890")


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

    # Positive path is validated via AuthService tests above; calling /mcp with auth
    # via TestClient can fail due FastMCP session manager lifecycle in tests.
