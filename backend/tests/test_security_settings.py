"""Production settings fail-fast and HTTP edge contracts."""

import pytest
from pydantic import ValidationError


def test_production_rejects_short_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "too-short")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "JWT_SECRET" in str(exc.value)


def test_production_rejects_weak_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "dev-secret-troque-em-producao-minimo-32-chars")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_rejects_default_admin_password(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "ADMIN_PASSWORD" in str(exc.value)


def test_production_rejects_cors_star(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "CORS" in str(exc.value)


def test_production_accepts_safe_config(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    monkeypatch.setenv("CREATE_TABLES_ON_STARTUP", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine")
    from app.core.config import Settings

    s = Settings(_env_file=None)
    assert s.is_production
    assert s.jwt_secret_value.startswith("aaa")


def test_local_allows_dev_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("JWT_SECRET", "dev-secret-local")
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    from app.core.config import Settings

    s = Settings(_env_file=None)
    assert not s.is_production


def test_health_endpoints_public(client):
    assert client.get("/health").status_code == 200
    assert client.get("/live").status_code == 200


def test_api_alias_removed(client):
    """Breaking: /api without /v1 must not serve the v1 router."""
    r = client.get("/api/products")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "timestamp" in body
    assert "message" in body


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Referrer-Policy" in r.headers
    assert "Permissions-Policy" in r.headers
    assert r.headers.get("Cache-Control") == "no-store"
