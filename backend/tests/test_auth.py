"""Tests for REST /api/v1/auth — verifies contracts:
- POST /auth/register → 201 User (no passwordHash exposed)
- POST /auth/login    → 200 { access_token, token_type }
- GET  /auth/me       → 200 User (requires Bearer token)
- Protected write routes require token when AUTH_REQUIRED=true
- Error shape on invalid credentials
"""

BASE = "/api/v1/auth"

REGISTER_PAYLOAD = {
    "name": "Usuário Teste",
    "email": "usuario@vitrine.local",
    "password": "senha_segura_123",
}


# ── Register ──────────────────────────────────────────────────────────────────


def test_register_returns_201(client):
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201


def test_register_response_shape(client):
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    data = r.json()
    assert "id" in data
    assert "name" in data
    assert "email" in data
    assert "isActive" in data      # camelCase
    assert "createdAt" in data     # camelCase
    assert "passwordHash" not in data   # must NEVER be exposed
    assert "password_hash" not in data  # neither snake_case


def test_register_duplicate_email_returns_409(client):
    client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 409
    body = r.json()
    assert body["status"] == 409
    assert "timestamp" in body


def test_register_missing_fields_returns_422(client):
    r = client.post(f"{BASE}/register", json={"email": "incomplete@example.com"})
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "details" in body


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_returns_token(client):
    client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    r = client.post(
        f"{BASE}/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "accessToken" in data
    assert data["tokenType"] == "bearer"
    assert isinstance(data["accessToken"], str)
    assert len(data["accessToken"]) > 10


def test_login_wrong_password_returns_401(client):
    client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    r = client.post(
        f"{BASE}/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "senha_errada"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["status"] == 401
    assert "timestamp" in body


def test_login_nonexistent_user_returns_401(client):
    r = client.post(
        f"{BASE}/login",
        json={"email": "nao_existe@vitrine.local", "password": "qualquercoisa"},
    )
    assert r.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────────


def test_me_returns_current_user(client, auth_token):
    r = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "email" in data
    assert "isActive" in data
    assert "passwordHash" not in data


def test_me_without_token_returns_401(client):
    r = client.get(f"{BASE}/me")
    assert r.status_code == 401
    body = r.json()
    assert body["status"] == 401
    assert "timestamp" in body


def test_me_with_invalid_token_returns_401(client):
    r = client.get(f"{BASE}/me", headers={"Authorization": "Bearer token.invalido.xyz"})
    assert r.status_code == 401


# ── Error format consistency ──────────────────────────────────────────────────


def test_error_response_shape_is_consistent(client):
    """All 4xx errors must return the same shape."""
    errors = [
        client.get(f"{BASE}/me"),                                          # 401
        client.post(f"{BASE}/login", json={"email": "x", "password": "y"}),  # 401
        client.post(f"{BASE}/register", json={}),                          # 422
    ]
    for r in errors:
        body = r.json()
        assert "status" in body, f"Missing 'status' in {body}"
        assert "message" in body, f"Missing 'message' in {body}"
        assert "timestamp" in body, f"Missing 'timestamp' in {body}"
        assert body["status"] == r.status_code
