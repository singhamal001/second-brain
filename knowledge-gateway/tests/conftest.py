from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from knowledge_gateway.app import create_app
from knowledge_gateway.config import get_settings


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "kg.db"
    vault_path = tmp_path / "vault"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("VAULT_ROOT", str(vault_path))
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")
    monkeypatch.setenv("REQUIRE_CLOUDFLARE_ACCESS", "false")
    monkeypatch.setenv("ALLOW_CF_BYPASS_FOR_LOCAL", "true")

    get_settings.cache_clear()
    app = create_app()
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def api_key(app):
    key = "test-secret-key"
    app.state.auth_service.provision_client(client_code="1234567890", raw_api_key=key, label="test")
    return key
