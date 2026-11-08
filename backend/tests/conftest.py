"""Pytest configuration and shared fixtures.

Default DB: SQLite in-memory (no PostgreSQL required).

Postgres (CI / local smoke):
  set DATABASE_URL=postgresql+psycopg2://... (and CI=true), or TEST_DATABASE_URL=...
  See docs/setup.md.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

# Force non-production settings before app import side-effects.
os.environ.setdefault("ENVIRONMENT", "test")

from app.api.deps import get_db  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.core.enums import UserRole  # noqa: E402
from app.core.rate_limit import login_rate_limiter  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


def _resolve_test_database_url() -> str:
    """SQLite by default; Postgres when explicitly opted in (CI or TEST_DATABASE_URL)."""
    explicit = os.environ.get("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("postgresql") and (
        os.environ.get("CI", "").lower() in {"1", "true", "yes"}
        or os.environ.get("PYTEST_USE_POSTGRES", "").lower() in {"1", "true", "yes"}
    ):
        return database_url
    return "sqlite://"


TEST_DATABASE_URL = _resolve_test_database_url()
IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter():
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


@pytest.fixture
def engine():
    """Fresh schema per test (avoids cross-test leaks with UoW commits)."""
    if IS_POSTGRES:
        _engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    else:
        _engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)
    _engine.dispose()


@pytest.fixture
def db(engine):
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture
def client(db: Session):
    """FastAPI TestClient with get_db overridden — mirrors production UoW."""

    def override_get_db():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _insert_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: UserRole,
    name: str,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        name=name,
        email=email.strip().lower(),
        password_hash=hash_password(password),
        role=role.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    return _insert_user(
        db,
        email="admin@test.local",
        password="admin-secret-123",
        role=UserRole.admin,
        name="Admin Test",
    )


@pytest.fixture
def operator_user(db: Session) -> User:
    return _insert_user(
        db,
        email="operator@test.local",
        password="operator-secret-123",
        role=UserRole.operator,
        name="Operator Test",
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(admin_user.id)


@pytest.fixture
def operator_token(operator_user: User) -> str:
    return create_access_token(operator_user.id)


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_headers(operator_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {operator_token}"}


# Backward-compatible alias used by older tests
@pytest.fixture
def auth_token(admin_token: str) -> str:
    return admin_token


@pytest.fixture
def auth_headers(admin_headers: dict[str, str]) -> dict[str, str]:
    return admin_headers


# ── Reusable helpers / factories ──────────────────────────────────────────────

PRODUCT_PAYLOAD = {
    "sku": "TEST-001",
    "name": "Produto de Teste",
    "description": "Descrição do produto de teste",
    "category": "camiseta",
    "sizes": ["P", "M", "G"],
    "colors": ["azul", "preto"],
    "price": 49.90,
    "costPrice": 20.00,
    "quantity": 10,
}


def product_payload(**overrides: Any) -> dict[str, Any]:
    """Build a product create payload with optional overrides."""
    data = dict(PRODUCT_PAYLOAD)
    data.update(overrides)
    return data


def sale_payload(product_id: str, **overrides: Any) -> dict[str, Any]:
    """Build a sale create payload (camelCase) for the given product."""
    data: dict[str, Any] = {
        "productId": product_id,
        "quantity": 1,
        "paymentMethod": "pix",
        "discount": 0,
    }
    data.update(overrides)
    return data


def money(value: str | float | Decimal) -> Decimal:
    return Decimal(str(value))


@pytest.fixture
def created_product(client, admin_headers):
    r = client.post("/api/v1/products", json=PRODUCT_PAYLOAD, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]
