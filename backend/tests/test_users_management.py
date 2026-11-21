"""User administration: PATCH /users/{id}, admin password reset, own password change."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import create_access_token, hash_password
from app.models.user import User

BASE = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
MISSING_ID = "00000000-0000-0000-0000-000000000099"


def _make_user(
    db: Session, *, email: str, role: UserRole, password: str = "senha-inicial-1"
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        name=email.split("@")[0],
        email=email,
        password_hash=hash_password(password),
        role=role.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    return user


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _login(client, email: str, password: str):
    return client.post(LOGIN, json={"email": email, "password": password})


# ── PATCH /users/{id} ────────────────────────────────────────────────────────


def test_admin_updates_name_and_role(client, admin_headers, operator_user):
    r = client.patch(
        f"{BASE}/{operator_user.id}",
        json={"name": "Caixa 2", "role": "admin"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Caixa 2"
    assert data["role"] == "admin"
    assert data["isActive"] is True
    assert "passwordHash" not in data and "password_hash" not in data


def test_patch_ignores_null_fields(client, admin_headers, operator_user):
    r = client.patch(f"{BASE}/{operator_user.id}", json={"name": None}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["name"] == operator_user.name


def test_patch_requires_admin(client, operator_headers, admin_user):
    r = client.patch(f"{BASE}/{admin_user.id}", json={"name": "x"}, headers=operator_headers)
    assert r.status_code == 403


def test_patch_requires_auth(client, operator_user):
    assert client.patch(f"{BASE}/{operator_user.id}", json={"name": "x"}).status_code == 401


def test_patch_unknown_user_returns_404(client, admin_headers):
    r = client.patch(f"{BASE}/{MISSING_ID}", json={"name": "x"}, headers=admin_headers)
    assert r.status_code == 404
    assert r.json()["status"] == 404


def test_patch_invalid_role_returns_422(client, admin_headers, operator_user):
    r = client.patch(f"{BASE}/{operator_user.id}", json={"role": "root"}, headers=admin_headers)
    assert r.status_code == 422


def test_admin_cannot_deactivate_self(client, admin_headers, admin_user):
    r = client.patch(f"{BASE}/{admin_user.id}", json={"isActive": False}, headers=admin_headers)
    assert r.status_code == 409
    assert "própria" in r.json()["message"]


def test_admin_cannot_demote_self(client, admin_headers, admin_user):
    r = client.patch(f"{BASE}/{admin_user.id}", json={"role": "operator"}, headers=admin_headers)
    assert r.status_code == 409


def test_admin_can_rename_self(client, admin_headers, admin_user):
    r = client.patch(f"{BASE}/{admin_user.id}", json={"name": "Coordenação"}, headers=admin_headers)
    assert r.status_code == 200


def test_admins_demoting_each_other_keep_one_admin(client, db: Session, admin_user, admin_headers):
    other = _make_user(db, email="other-admin@test.local", role=UserRole.admin)

    first = client.patch(f"{BASE}/{other.id}", json={"role": "operator"}, headers=admin_headers)
    second = client.patch(
        f"{BASE}/{admin_user.id}", json={"role": "operator"}, headers=_bearer(other)
    )

    assert first.status_code == 200
    # `other` is no longer admin, so it cannot demote anyone.
    assert second.status_code == 403


def test_last_active_admin_guard_when_target_is_other_admin(
    client, db: Session, admin_user, admin_headers, monkeypatch
):
    target = _make_user(db, email="admin2@test.local", role=UserRole.admin)
    from app.repositories.user_repository import UserRepository

    # Concurrent demotion already removed the actor from the active set.
    monkeypatch.setattr(UserRepository, "lock_active_admin_ids", lambda self: [target.id])

    r = client.patch(f"{BASE}/{target.id}", json={"isActive": False}, headers=admin_headers)
    assert r.status_code == 409
    assert "último administrador" in r.json()["message"]


def test_admin_can_deactivate_other_admin_when_another_remains(client, db: Session, admin_headers):
    target = _make_user(db, email="admin3@test.local", role=UserRole.admin)
    r = client.patch(f"{BASE}/{target.id}", json={"isActive": False}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["isActive"] is False


def test_deactivated_user_tokens_return_401_and_login_is_refused(
    client, admin_headers, operator_user, operator_headers
):
    assert client.get("/api/v1/auth/me", headers=operator_headers).status_code == 200

    r = client.patch(f"{BASE}/{operator_user.id}", json={"isActive": False}, headers=admin_headers)
    assert r.status_code == 200

    assert client.get("/api/v1/auth/me", headers=operator_headers).status_code == 401
    assert client.get("/api/v1/sales", headers=operator_headers).status_code == 401
    login = _login(client, operator_user.email, "operator-secret-123")
    assert login.status_code in (401, 403)
    assert "accessToken" not in login.text


def test_reactivated_user_can_log_in_again(client, admin_headers, operator_user):
    client.patch(f"{BASE}/{operator_user.id}", json={"isActive": False}, headers=admin_headers)
    client.patch(f"{BASE}/{operator_user.id}", json={"isActive": True}, headers=admin_headers)
    assert _login(client, operator_user.email, "operator-secret-123").status_code == 200


# ── POST /users/{id}/password (admin reset) ──────────────────────────────────


def test_admin_resets_other_user_password(client, admin_headers, operator_user):
    r = client.post(
        f"{BASE}/{operator_user.id}/password",
        json={"newPassword": "nova-senha-caixa-1"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["id"] == operator_user.id
    assert _login(client, operator_user.email, "operator-secret-123").status_code == 401
    assert _login(client, operator_user.email, "nova-senha-caixa-1").status_code == 200


def test_admin_reset_rejects_short_password(client, admin_headers, operator_user):
    r = client.post(
        f"{BASE}/{operator_user.id}/password",
        json={"newPassword": "curta"},
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert r.json()["details"][0]["field"] == "newPassword"


def test_admin_reset_rejects_password_over_72_bytes(client, admin_headers, operator_user):
    r = client.post(
        f"{BASE}/{operator_user.id}/password",
        json={"newPassword": "é" * 40},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_admin_reset_own_password_is_refused(client, admin_headers, admin_user):
    r = client.post(
        f"{BASE}/{admin_user.id}/password",
        json={"newPassword": "outra-senha-admin-1"},
        headers=admin_headers,
    )
    assert r.status_code == 409
    assert "/users/me/password" in r.json()["message"]


def test_operator_cannot_reset_password(client, operator_headers, admin_user):
    r = client.post(
        f"{BASE}/{admin_user.id}/password",
        json={"newPassword": "tentativa-de-ataque"},
        headers=operator_headers,
    )
    assert r.status_code == 403


def test_reset_unknown_user_returns_404(client, admin_headers):
    r = client.post(
        f"{BASE}/{MISSING_ID}/password",
        json={"newPassword": "qualquer-senha-1"},
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_password_values_never_logged(client, admin_headers, operator_user, caplog):
    secret = "senha-que-nao-pode-vazar-1"
    with caplog.at_level(logging.DEBUG):
        client.post(
            f"{BASE}/{operator_user.id}/password",
            json={"newPassword": secret},
            headers=admin_headers,
        )
    assert secret not in caplog.text
    assert "user_password_reset" in caplog.text


# ── POST /users/me/password ──────────────────────────────────────────────────


def test_user_changes_own_password(client, operator_user, operator_headers):
    r = client.post(
        f"{BASE}/me/password",
        json={"currentPassword": "operator-secret-123", "newPassword": "minha-nova-senha-1"},
        headers=operator_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["email"] == operator_user.email
    assert _login(client, operator_user.email, "minha-nova-senha-1").status_code == 200
    assert _login(client, operator_user.email, "operator-secret-123").status_code == 401


def test_change_own_password_wrong_current_returns_422(client, operator_headers):
    r = client.post(
        f"{BASE}/me/password",
        json={"currentPassword": "errada", "newPassword": "minha-nova-senha-1"},
        headers=operator_headers,
    )
    assert r.status_code == 422
    assert "atual" in r.json()["message"].lower()


def test_change_own_password_same_as_current_returns_422(client, operator_headers):
    r = client.post(
        f"{BASE}/me/password",
        json={"currentPassword": "operator-secret-123", "newPassword": "operator-secret-123"},
        headers=operator_headers,
    )
    assert r.status_code == 422


def test_change_own_password_short_new_returns_422(client, operator_headers):
    r = client.post(
        f"{BASE}/me/password",
        json={"currentPassword": "operator-secret-123", "newPassword": "123"},
        headers=operator_headers,
    )
    assert r.status_code == 422


def test_change_own_password_requires_auth(client):
    r = client.post(
        f"{BASE}/me/password",
        json={"currentPassword": "a", "newPassword": "minha-nova-senha-1"},
    )
    assert r.status_code == 401


def test_change_own_password_rate_limited(client, operator_headers):
    payload = {"currentPassword": "errada", "newPassword": "minha-nova-senha-1"}
    for _ in range(5):
        r = client.post(f"{BASE}/me/password", json=payload, headers=operator_headers)
        assert r.status_code == 422

    blocked = client.post(f"{BASE}/me/password", json=payload, headers=operator_headers)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert blocked.json()["status"] == 429
