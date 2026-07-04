"""Tests for REST /api/v1/auth — verifies contracts:
- POST /auth/register → 201 { "success": true, "message": "...", "data": User }
- POST /auth/login    → 200 { "success": true, "message": "...", "data": TokenResponse }
- GET  /auth/me       → 200 { "success": true, "message": "...", "data": User }
- Standard envelope on all responses
- Email format validation (format-only, no DNS check)
- Password minimum length validation (8 chars)
- No passwordHash ever exposed
"""

BASE = "/api/v1/auth"

REGISTER_PAYLOAD = {
    "name": "Usuário Teste",
    "email": "usuario@example.com",
    "password": "senha_segura_123",
}


# ── Register ──────────────────────────────────────────────────────────────────


def test_register_returns_201(client):
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 201


def test_register_standard_envelope(client):
    """Response must be wrapped in StandardResponse."""
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body


def test_register_response_shape(client):
    r = client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    data = r.json()["data"]
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


def test_register_invalid_email_returns_422(client):
    r = client.post(
        f"{BASE}/register",
        json={**REGISTER_PAYLOAD, "email": "not-an-email"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422


def test_register_short_password_returns_422(client):
    """Password shorter than 8 characters must be rejected."""
    r = client.post(
        f"{BASE}/register",
        json={**REGISTER_PAYLOAD, "password": "abc"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_returns_token(client):
    client.post(f"{BASE}/register", json=REGISTER_PAYLOAD)
    r = client.post(
        f"{BASE}/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
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
        json={"email": "nao_existe@example.com", "password": "qualquercoisa"},
    )
    assert r.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────────


def test_me_returns_current_user(client, auth_token):
    r = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
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
    """All 4xx errors must return the same error envelope shape."""
    errors = [
        client.get(f"{BASE}/me"),                                          # 401
        client.post(f"{BASE}/login", json={"email": "x", "password": "y"}),  # 401
        client.post(f"{BASE}/register", json={}),                          # 422
    ]
    for r in errors:
        body = r.json()
        assert "status" in body, f"Missing 'status' in {body}"
        assert "timestamp" in body, f"Missing 'timestamp' in {body}"
        assert "message" in body, f"Missing 'message' in {body}"

        assert "message" in body, f"Missing 'message' in {body}"
        assert "timestamp" in body, f"Missing 'timestamp' in {body}"
        assert body["status"] == r.status_code
