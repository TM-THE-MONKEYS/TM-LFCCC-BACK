"""Production polish — observability, authz gaps, settings guards."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
AUTH = "/api/v1/auth"


def test_correlation_id_roundtrip(client):
    r = client.get("/health", headers={"X-Correlation-ID": "test-corr-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Correlation-ID") == "test-corr-123"


def test_correlation_id_rejects_invalid_and_issues_uuid(client):
    r = client.get("/health", headers={"X-Correlation-ID": "bad id with spaces!!!"})
    assert r.status_code == 200
    cid = r.headers.get("X-Correlation-ID")
    assert cid
    assert " " not in cid
    assert cid != "bad id with spaces!!!"


def test_permissions_policy_and_cache_control_on_api(client):
    r = client.get("/health")
    assert r.headers.get("Permissions-Policy")
    assert "camera=()" in r.headers.get("Permissions-Policy", "")
    assert r.headers.get("Cache-Control") == "no-store"


def test_response_time_header_on_api(client):
    r = client.get("/api/v1/products")
    assert r.status_code == 200
    assert "X-Response-Time-Ms" in r.headers


def test_ready_probe_ok(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_login_rate_limit_includes_retry_after(client, admin_user, monkeypatch):
    from app.core.rate_limit import login_rate_limiter

    monkeypatch.setattr(login_rate_limiter, "max_attempts", 2)
    login_rate_limiter.reset()
    payload = {"email": "admin@test.local", "password": "wrong"}
    assert client.post(f"{AUTH}/login", json=payload).status_code == 401
    assert client.post(f"{AUTH}/login", json=payload).status_code == 401
    r = client.post(f"{AUTH}/login", json=payload)
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "60"
    body = r.json()
    assert body["status"] == 429
    assert "message" in body


def test_operator_cannot_cancel_sale(client, created_product, operator_headers, admin_headers):
    sale = client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 1, "paymentMethod": "pix"},
        headers=operator_headers,
    ).json()["data"]
    r = client.post(f"{SALES}/{sale['id']}/cancel", headers=operator_headers)
    assert r.status_code == 403
    # Admin can still cancel
    assert client.post(f"{SALES}/{sale['id']}/cancel", headers=admin_headers).status_code == 200


def test_soft_deleted_product_cannot_be_sold(client, created_product, admin_headers):
    pid = created_product["id"]
    assert client.delete(f"{PRODUCTS}/{pid}", headers=admin_headers).status_code == 204
    r = client.post(
        SALES,
        json={"productId": pid, "quantity": 1, "paymentMethod": "pix"},
        headers=admin_headers,
    )
    assert r.status_code == 409
    assert "inativo" in r.json()["message"].lower()


def test_inactive_products_visible_when_is_active_false(client, created_product, admin_headers):
    pid = created_product["id"]
    client.delete(f"{PRODUCTS}/{pid}", headers=admin_headers)
    hidden = client.get(PRODUCTS).json()["data"]
    assert all(p["id"] != pid for p in hidden)
    shown = client.get(f"{PRODUCTS}?isActive=false").json()["data"]
    assert any(p["id"] == pid for p in shown)


def test_production_rejects_create_tables_on_startup(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    monkeypatch.setenv("CREATE_TABLES_ON_STARTUP", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine")
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "CREATE_TABLES_ON_STARTUP" in str(exc.value)


def test_production_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    monkeypatch.setenv("CREATE_TABLES_ON_STARTUP", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./prod.db")
    from app.core.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "SQLite" in str(exc.value) or "DATABASE_URL" in str(exc.value)


def test_production_accepts_safe_postgres_config(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    monkeypatch.setenv("CREATE_TABLES_ON_STARTUP", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine")
    from app.core.config import Settings

    s = Settings(_env_file=None)
    assert s.is_production
