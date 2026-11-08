"""Tests for REST /api/v1/auth — Fase 3 security contracts."""

import jwt

from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.core.security import decode_access_token_claims

BASE = "/api/v1/auth"
USERS = "/api/v1/users"

ADMIN_LOGIN = {
    "email": "admin@test.local",
    "password": "admin-secret-123",
}


# ── Register removed ──────────────────────────────────────────────────────────


def test_public_register_removed(client):
    r = client.post(
        f"{BASE}/register",
        json={"name": "X", "email": "x@example.com", "password": "senha_segura_123"},
    )
    assert r.status_code == 404


def test_admin_can_create_user(client, admin_headers):
    r = client.post(
        USERS,
        json={
            "name": "Novo Operador",
            "email": "novo@example.com",
            "password": "senha_segura_123",
            "role": "operator",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["email"] == "novo@example.com"
    assert data["role"] == "operator"
    assert "passwordHash" not in data


def test_operator_cannot_create_user(client, operator_headers):
    r = client.post(
        USERS,
        json={
            "name": "Bloqueado",
            "email": "blocked@example.com",
            "password": "senha_segura_123",
        },
        headers=operator_headers,
    )
    assert r.status_code == 403


def test_create_user_short_password_returns_422(client, admin_headers):
    r = client.post(
        USERS,
        json={"name": "X", "email": "x@example.com", "password": "abc"},
        headers=admin_headers,
    )
    assert r.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_returns_token(client, admin_user):
    r = client.post(f"{BASE}/login", json=ADMIN_LOGIN)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert "accessToken" in data
    assert data["tokenType"] == "bearer"
    assert len(data["accessToken"]) > 10


def test_login_normalizes_email(client, admin_user):
    r = client.post(
        f"{BASE}/login",
        json={"email": "  Admin@Test.Local  ", "password": ADMIN_LOGIN["password"]},
    )
    assert r.status_code == 200
    assert r.json()["data"]["accessToken"]


def test_login_jwt_claims(client, admin_user):
    token = client.post(f"{BASE}/login", json=ADMIN_LOGIN).json()["data"]["accessToken"]
    claims = decode_access_token_claims(token)
    assert claims is not None
    assert claims["sub"] == admin_user.id
    assert claims["type"] == "access"
    assert "exp" in claims
    assert "iat" in claims
    assert "jti" in claims
    # Raw decode must match configured secret
    raw = jwt.decode(token, settings.jwt_secret_value, algorithms=["HS256"])
    assert raw["type"] == "access"


def test_login_wrong_password_returns_401(client, admin_user):
    r = client.post(
        f"{BASE}/login",
        json={"email": ADMIN_LOGIN["email"], "password": "senha_errada"},
    )
    assert r.status_code == 401


def test_login_nonexistent_user_returns_401(client):
    r = client.post(
        f"{BASE}/login",
        json={"email": "nao_existe@example.com", "password": "qualquercoisa"},
    )
    assert r.status_code == 401


def test_login_password_over_72_bytes_returns_422(client, admin_user):
    long_password = "á" * 40  # multi-byte chars → >72 bytes
    assert len(long_password.encode("utf-8")) > 72
    r = client.post(
        f"{BASE}/login",
        json={"email": ADMIN_LOGIN["email"], "password": long_password},
    )
    assert r.status_code == 422


def test_login_rate_limit_returns_429(client, admin_user, monkeypatch):
    monkeypatch.setattr(login_rate_limiter, "max_attempts", 3)
    login_rate_limiter.reset()
    payload = {"email": ADMIN_LOGIN["email"], "password": "wrong"}
    for _ in range(3):
        assert client.post(f"{BASE}/login", json=payload).status_code == 401
    r = client.post(f"{BASE}/login", json=payload)
    assert r.status_code == 429


# ── Me ────────────────────────────────────────────────────────────────────────


def test_me_returns_current_user(client, auth_token, admin_user):
    r = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["email"] == admin_user.email
    assert data["role"] == "admin"
    assert "passwordHash" not in data


def test_me_without_token_returns_401(client):
    r = client.get(f"{BASE}/me")
    assert r.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    r = client.get(f"{BASE}/me", headers={"Authorization": "Bearer token.invalido.xyz"})
    assert r.status_code == 401


def test_error_response_shape_is_consistent(client):
    errors = [
        client.get(f"{BASE}/me"),
        client.post(f"{BASE}/login", json={"email": "x", "password": "y"}),
    ]
    for r in errors:
        body = r.json()
        assert "status" in body
        assert "timestamp" in body
        assert "message" in body
        assert body["status"] == r.status_code
