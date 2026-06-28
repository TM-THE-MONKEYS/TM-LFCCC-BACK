"""Tests for REST /api/v1/products — verifies contracts:
- GET  /products         → 200 { "data": [...] }
- GET  /products/{id}    → 200 Product
- POST /products         → 201 Product
- PUT  /products/{id}    → 200 Product
- DELETE /products/{id}  → 204
- PATCH /products/{id}/stock → 200 Product
- camelCase fields in all responses
- Error shape { status, message, details?, timestamp }
- 409 on duplicate SKU
- 404 on not found
"""

from tests.conftest import PRODUCT_PAYLOAD

BASE = "/api/v1/products"


# ── List ──────────────────────────────────────────────────────────────────────


def test_list_products_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert isinstance(body["data"], list)


def test_list_products_empty(client):
    r = client.get(BASE)
    assert r.json()["data"] == []


# ── Create ────────────────────────────────────────────────────────────────────


def test_create_product_returns_201(client):
    r = client.post(BASE, json=PRODUCT_PAYLOAD)
    assert r.status_code == 201


def test_create_product_response_shape(client):
    r = client.post(BASE, json=PRODUCT_PAYLOAD)
    data = r.json()
    # Required camelCase fields
    assert "id" in data
    assert "sku" in data
    assert "createdAt" in data
    assert "updatedAt" in data
    assert "isActive" in data
    assert "costPrice" in data
    assert data["sku"] == PRODUCT_PAYLOAD["sku"]
    assert data["isActive"] is True


def test_create_product_duplicate_sku_returns_409(client):
    client.post(BASE, json=PRODUCT_PAYLOAD)
    r = client.post(BASE, json=PRODUCT_PAYLOAD)
    assert r.status_code == 409
    body = r.json()
    assert body["status"] == 409
    assert "message" in body
    assert "timestamp" in body


def test_create_product_invalid_category_returns_422(client):
    payload = {**PRODUCT_PAYLOAD, "sku": "ERR-001", "category": "categoria_invalida"}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body["status"] == 422
    assert "details" in body


def test_create_product_negative_price_returns_422(client):
    payload = {**PRODUCT_PAYLOAD, "sku": "ERR-002", "price": -10}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422


# ── Read by ID ────────────────────────────────────────────────────────────────


def test_get_product_by_id(client, created_product):
    r = client.get(f"{BASE}/{created_product['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created_product["id"]


def test_get_product_not_found(client):
    r = client.get(f"{BASE}/nonexistent-id-xyz")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "timestamp" in body


# ── Update ────────────────────────────────────────────────────────────────────


def test_update_product(client, created_product):
    updated = {**PRODUCT_PAYLOAD, "name": "Nome Atualizado", "price": 59.90}
    r = client.put(f"{BASE}/{created_product['id']}", json=updated)
    assert r.status_code == 200
    assert r.json()["name"] == "Nome Atualizado"
    assert r.json()["price"] == 59.90


def test_update_product_duplicate_sku(client, created_product):
    # Create a second product
    second = client.post(BASE, json={**PRODUCT_PAYLOAD, "sku": "TEST-002"}).json()
    # Try to update its SKU to the first product's SKU
    r = client.put(
        f"{BASE}/{second['id']}",
        json={**PRODUCT_PAYLOAD, "sku": PRODUCT_PAYLOAD["sku"]},
    )
    assert r.status_code == 409


# ── Delete ────────────────────────────────────────────────────────────────────


def test_delete_product_returns_204(client, created_product):
    r = client.delete(f"{BASE}/{created_product['id']}")
    assert r.status_code == 204
    assert r.content == b""


def test_delete_product_then_get_returns_404(client, created_product):
    client.delete(f"{BASE}/{created_product['id']}")
    r = client.get(f"{BASE}/{created_product['id']}")
    assert r.status_code == 404


# ── Stock patch ───────────────────────────────────────────────────────────────


def test_patch_stock_decrements(client, created_product):
    initial_qty = created_product["quantity"]
    r = client.patch(f"{BASE}/{created_product['id']}/stock", json={"delta": -3})
    assert r.status_code == 200
    assert r.json()["quantity"] == initial_qty - 3


def test_patch_stock_never_goes_below_zero(client, created_product):
    r = client.patch(f"{BASE}/{created_product['id']}/stock", json={"delta": -9999})
    assert r.status_code == 200
    assert r.json()["quantity"] == 0


def test_patch_stock_increments(client, created_product):
    initial_qty = created_product["quantity"]
    r = client.patch(f"{BASE}/{created_product['id']}/stock", json={"delta": 5})
    assert r.status_code == 200
    assert r.json()["quantity"] == initial_qty + 5
