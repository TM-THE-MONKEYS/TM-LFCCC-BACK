"""Tests for REST /api/v1/sales — Fase 3 auth + admin override."""

import threading

import pytest
from sqlalchemy.orm import Session

from app.models.product import Product
from tests.conftest import PRODUCT_PAYLOAD

BASE = "/api/v1/sales"


def _sale_payload(product: dict, quantity: int = 1, discount: float = 0.0, **extra) -> dict:
    payload = {
        "productId": product["id"],
        "quantity": quantity,
        "discount": discount,
        "paymentMethod": "pix",
    }
    payload.update(extra)
    return payload


# --- Auth --------------------------------------------------------------------


def test_list_sales_requires_auth(client):
    assert client.get(BASE).status_code == 401


def test_create_sale_requires_auth(client, created_product):
    assert client.post(BASE, json=_sale_payload(created_product)).status_code == 401


# --- List --------------------------------------------------------------------


def test_list_sales_returns_envelope(client, admin_headers):
    r = client.get(BASE, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == 0
    assert "skip" in body["meta"] and "limit" in body["meta"]


# --- Create ------------------------------------------------------------------


def test_create_sale_returns_201(client, created_product, operator_headers):
    r = client.post(BASE, json=_sale_payload(created_product), headers=operator_headers)
    assert r.status_code == 201


def test_create_sale_standard_envelope(client, created_product, admin_headers):
    r = client.post(BASE, json=_sale_payload(created_product), headers=admin_headers)
    body = r.json()
    assert body["success"] is True
    assert "data" in body


def test_create_sale_response_shape(client, created_product, admin_headers):
    r = client.post(BASE, json=_sale_payload(created_product), headers=admin_headers)
    data = r.json()["data"]
    assert "id" in data
    assert "productId" in data
    assert "productName" in data
    assert "unitPrice" in data
    assert "createdAt" in data


def test_create_sale_snapshot_uses_db_name_and_sku(client, created_product, admin_headers):
    r = client.post(BASE, json=_sale_payload(created_product), headers=admin_headers)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["productName"] == created_product["name"]
    assert data["productSku"] == created_product["sku"]


def test_operator_unit_price_override_ignored(client, created_product, operator_headers):
    stale_override = 1.23
    r = client.post(
        BASE,
        json=_sale_payload(created_product, unitPriceOverride=stale_override),
        headers=operator_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["unitPrice"] == created_product["price"]
    assert data["unitPrice"] != stale_override


def test_admin_unit_price_override_honored(client, created_product, admin_headers):
    override = 12.34
    r = client.post(
        BASE,
        json=_sale_payload(created_product, unitPriceOverride=override),
        headers=admin_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["unitPrice"] == override
    assert data["total"] == override


def test_create_sale_prefers_promo_price(client, admin_headers):
    payload = {**PRODUCT_PAYLOAD, "sku": "PROMO-001", "price": 100.0, "promoPrice": 70.0}
    product = client.post("/api/v1/products", json=payload, headers=admin_headers).json()["data"]
    r = client.post(BASE, json=_sale_payload(product), headers=admin_headers)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["unitPrice"] == 70.0
    assert data["total"] == 70.0


def test_create_sale_inactive_product_returns_409(
    client, db: Session, created_product, admin_headers
):
    from sqlalchemy import select

    product = db.scalar(select(Product).where(Product.id == created_product["id"]))
    assert product is not None
    product.is_active = False
    db.flush()

    r = client.post(BASE, json=_sale_payload(created_product), headers=admin_headers)
    assert r.status_code == 409
    assert "inativo" in r.json()["message"].lower()


def test_create_sale_invalid_size_returns_422(client, created_product, admin_headers):
    r = client.post(BASE, json=_sale_payload(created_product, size="XXXL"), headers=admin_headers)
    assert r.status_code == 422
    assert "tamanho" in r.json()["message"].lower()


def test_create_sale_invalid_color_returns_422(client, created_product, admin_headers):
    r = client.post(
        BASE,
        json=_sale_payload(created_product, color="lilás-neon"),
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert "cor" in r.json()["message"].lower()


def test_create_sale_decrements_stock_atomically(client, created_product, admin_headers):
    initial_qty = created_product["quantity"]
    qty_to_sell = 3
    r = client.post(
        BASE, json=_sale_payload(created_product, quantity=qty_to_sell), headers=admin_headers
    )
    assert r.status_code == 201
    product = client.get(f"/api/v1/products/{created_product['id']}").json()["data"]
    assert product["quantity"] == initial_qty - qty_to_sell


def test_create_sale_insufficient_stock_returns_409(client, created_product, admin_headers):
    r = client.post(BASE, json=_sale_payload(created_product, quantity=9999), headers=admin_headers)
    assert r.status_code == 409


def test_create_sale_stock_not_decremented_on_failure(client, created_product, admin_headers):
    initial_qty = created_product["quantity"]
    client.post(BASE, json=_sale_payload(created_product, quantity=9999), headers=admin_headers)
    product = client.get(f"/api/v1/products/{created_product['id']}").json()["data"]
    assert product["quantity"] == initial_qty


def test_create_sale_server_recalculates_total(client, created_product, admin_headers):
    payload = _sale_payload(created_product, quantity=2, discount=10.0)
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 201
    expected_total = round(created_product["price"] * 2 * (1 - 10.0 / 100), 2)
    assert r.json()["data"]["total"] == expected_total


def test_sale_total_exact_cents_decimal_money(client, admin_headers):
    """3 × 19.90 com 10% desconto = 53.73 exato (sem erro de float)."""
    payload = {
        **PRODUCT_PAYLOAD,
        "sku": "MONEY-1990",
        "price": 19.90,
        "costPrice": 8.00,
        "quantity": 20,
    }
    product = client.post("/api/v1/products", json=payload, headers=admin_headers).json()["data"]
    r = client.post(
        BASE,
        json=_sale_payload(product, quantity=3, discount=10.0),
        headers=admin_headers,
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["unitPrice"] == 19.90
    assert data["total"] == 53.73


def test_mid_operation_failure_rolls_back_sale(client, created_product, admin_headers, monkeypatch):
    """Falha após flush da venda não deixa estado parcial (UoW rollback)."""
    from app.repositories.product_repository import ProductRepository

    monkeypatch.setattr(
        ProductRepository,
        "decrement_stock_atomic",
        lambda self, product_id, quantity: False,
    )
    r = client.post(BASE, json=_sale_payload(created_product, quantity=1), headers=admin_headers)
    assert r.status_code == 409

    sales = client.get(BASE, headers=admin_headers).json()["data"]
    assert sales == []
    product = client.get(f"/api/v1/products/{created_product['id']}").json()["data"]
    assert product["quantity"] == created_product["quantity"]


def test_create_sale_product_not_found_returns_404(client, admin_headers):
    payload = {
        "productId": "00000000-0000-0000-0000-000000000099",
        "quantity": 1,
        "discount": 0.0,
        "paymentMethod": "pix",
    }
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 404


def test_create_sale_invalid_payment_method_returns_422(client, created_product, admin_headers):
    payload = {**_sale_payload(created_product), "paymentMethod": "criptomoeda"}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422


def test_create_sale_zero_quantity_returns_422(client, created_product, admin_headers):
    payload = {**_sale_payload(created_product), "quantity": 0}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422


# --- Get by ID ---------------------------------------------------------------


def test_get_sale_by_id(client, created_product, admin_headers):
    created = client.post(BASE, json=_sale_payload(created_product), headers=admin_headers).json()[
        "data"
    ]
    r = client.get(f"{BASE}/{created['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["id"] == created["id"]


def test_get_sale_not_found(client, admin_headers):
    r = client.get(f"{BASE}/00000000-0000-0000-0000-000000000099", headers=admin_headers)
    assert r.status_code == 404


def test_get_sale_invalid_uuid_returns_422(client, admin_headers):
    r = client.get(f"{BASE}/nonexistent-id", headers=admin_headers)
    assert r.status_code == 422


# --- Pagination --------------------------------------------------------------


def test_list_sales_pagination(client, created_product, admin_headers):
    for _ in range(3):
        client.post(BASE, json=_sale_payload(created_product, quantity=1), headers=admin_headers)
    all_sales = client.get(BASE, headers=admin_headers).json()["data"]
    page = client.get(f"{BASE}?skip=1&limit=1", headers=admin_headers).json()["data"]
    assert len(page) == 1
    assert page[0]["id"] == all_sales[1]["id"]


def test_list_sales_most_recent_first(client, created_product, admin_headers):
    client.post(BASE, json=_sale_payload(created_product, quantity=1), headers=admin_headers)
    client.post(BASE, json=_sale_payload(created_product, quantity=1), headers=admin_headers)
    sales = client.get(BASE, headers=admin_headers).json()["data"]
    assert len(sales) >= 2
    assert sales[0]["createdAt"] >= sales[1]["createdAt"]


# --- Concurrency (Postgres only) ---------------------------------------------


@pytest.mark.postgres
def test_concurrent_sale_last_unit_one_201_one_409(engine):
    """Two sessions racing the last unit: one 201, one 409 (Postgres only)."""
    if engine.dialect.name == "sqlite":
        pytest.skip("Concurrency race requires PostgreSQL; skipped on SQLite")

    from sqlalchemy.orm import sessionmaker

    from app.core.enums import ProductCategory
    from app.exceptions import InsufficientStockError
    from app.models.sale import Sale
    from app.schemas.sale import SaleInput
    from app.services.sale_service import SaleService

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    setup = SessionLocal()
    try:
        product = Product(
            id="race-product-id",
            sku="RACE-001",
            name="Race Product",
            description="",
            category=ProductCategory.camiseta.value,
            sizes=["M"],
            colors=["azul"],
            price=10.0,
            promo_price=None,
            cost_price=5.0,
            quantity=1,
            is_active=True,
        )
        setup.add(product)
        setup.commit()
    finally:
        setup.close()

    results: list[int | str] = []
    lock = threading.Lock()

    def attempt_sale() -> None:
        session = SessionLocal()
        try:
            service = SaleService(session)
            service.create(
                SaleInput(
                    product_id="race-product-id",
                    quantity=1,
                    payment_method="pix",
                )
            )
            session.commit()
            with lock:
                results.append(201)
        except InsufficientStockError:
            session.rollback()
            with lock:
                results.append(409)
        except Exception as exc:
            session.rollback()
            with lock:
                results.append(str(exc))
        finally:
            session.close()

    t1 = threading.Thread(target=attempt_sale)
    t2 = threading.Thread(target=attempt_sale)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results) == [201, 409]

    from sqlalchemy import func, select

    verify = SessionLocal()
    try:
        remaining = verify.scalar(select(Product.quantity).where(Product.id == "race-product-id"))
        sale_count = verify.scalar(
            select(func.count()).select_from(Sale).where(Sale.product_id == "race-product-id")
        )
        assert remaining == 0
        assert sale_count == 1
    finally:
        verify.close()
