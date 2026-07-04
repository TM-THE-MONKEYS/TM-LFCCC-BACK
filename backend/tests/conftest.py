"""Pytest configuration and shared fixtures.

Uses SQLite in-memory so tests run without a running PostgreSQL.
The product model now uses JSON (not ARRAY) so SQLite is fully compatible.

Isolation strategy:
  - session-scoped engine + table creation (fast)
  - function-scoped session inside a rolled-back transaction (clean state per test)
  - TestClient with get_db dependency override
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.dependencies import get_db  # same object routers depend on — override works correctly
from app.core.database import Base
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    _engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db(engine):
    """Per-test DB session — changes are rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSession()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session):
    """FastAPI TestClient with get_db overridden to use the test session."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable helpers ──────────────────────────────────────────────────────────

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


@pytest.fixture
def created_product(client):
    r = client.post("/api/v1/products", json=PRODUCT_PAYLOAD)
    assert r.status_code == 201
    # Response is now wrapped: {"success": true, "message": "...", "data": {...}}
    return r.json()["data"]


@pytest.fixture
def auth_token(client) -> str:
    """Registers a user and returns a valid Bearer token."""
    client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "secret123"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    return r.json()["data"]["accessToken"]
