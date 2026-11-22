"""imageUrl: relative by default (same-origin proxy), absolute only with PUBLIC_BASE_URL."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.product import build_public_image_url
from tests.conftest import MIN_PNG, product_payload, upload_image


@pytest.fixture
def public_base_url(monkeypatch):
    def _set(value: str) -> None:
        monkeypatch.setattr(get_settings(), "PUBLIC_BASE_URL", value)

    return _set


def test_empty_base_returns_root_relative_path(public_base_url):
    public_base_url("")
    assert build_public_image_url("uploads/products/a.png") == "/uploads/products/a.png"


def test_base_url_builds_absolute_url(public_base_url):
    public_base_url("http://192.168.0.50")
    assert (
        build_public_image_url("uploads/products/a.png")
        == "http://192.168.0.50/uploads/products/a.png"
    )


def test_external_url_is_returned_untouched(public_base_url):
    public_base_url("")
    assert (
        build_public_image_url("https://cdn.example.com/x.png") == "https://cdn.example.com/x.png"
    )


def test_missing_image_is_null(public_base_url):
    public_base_url("")
    assert build_public_image_url(None) is None


def test_settings_default_public_base_url_is_empty(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert Settings(_env_file=None).PUBLIC_BASE_URL == ""


def test_settings_strip_trailing_slash(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", " http://vitrine.lan/ ")
    assert Settings(_env_file=None).PUBLIC_BASE_URL == "http://vitrine.lan"


def test_settings_reject_base_without_scheme(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "vitrine.lan")
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)
    assert "PUBLIC_BASE_URL" in str(exc.value)


def test_production_accepts_empty_public_base_url(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "http://192.168.0.50")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine")
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    assert Settings(_env_file=None).PUBLIC_BASE_URL == ""


def test_upload_returns_relative_image_url(
    client, created_product, admin_headers, tmp_storage, public_base_url
):
    public_base_url("")
    r = upload_image(client, created_product["id"], MIN_PNG, admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["imageUrl"].startswith("/uploads/products/")


def test_public_catalog_returns_relative_image_url(client, admin_headers, public_base_url):
    public_base_url("")
    payload = product_payload(sku="IMG-REL-1", imageUrl="uploads/products/existing.png")
    created = client.post("/api/v1/products", json=payload, headers=admin_headers)
    assert created.status_code == 201

    listed = client.get("/api/v1/products").json()["data"]
    assert listed[0]["imageUrl"] == "/uploads/products/existing.png"
