"""FASE 6 ops: health version metadata + seed guards."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.seed import run_seed, seed_products, seed_sales


def test_health_includes_package_version(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "version" in body
    assert isinstance(body["version"], str)
    assert body["version"]  # non-empty
    assert "timestamp" in body


def test_seed_blocked_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 32 + "-producao-segura")
    monkeypatch.setenv("ADMIN_PASSWORD", "senha-forte-producao-123")
    monkeypatch.setenv("CORS_ORIGINS", "https://vitrine.example.com")
    get_settings.cache_clear()
    assert Settings(_env_file=None).is_production
    get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit, match="production"):
            run_seed()
    finally:
        # Restore cache before monkeypatch teardown so later tests see test settings.
        monkeypatch.setenv("ENVIRONMENT", "test")
        get_settings.cache_clear()


def test_seed_sales_via_sale_service(db):
    """Sales seed goes through SaleService (stock decrement + totals)."""
    products = seed_products(db)
    assert products
    before_qty = {p.sku: p.quantity for p in products}
    seed_sales(db, products)
    db.expire_all()
    from app.models.sale import Sale

    assert db.query(Sale).count() == 3
    cam = next(p for p in products if p.sku == "CAM-001")
    db.refresh(cam)
    assert cam.quantity == before_qty["CAM-001"] - 2
