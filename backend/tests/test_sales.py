"""Tests for REST /api/v1/sales — verifies contracts:
- GET  /sales       → 200 { "data": [...] }
- POST /sales       → 201 Sale
- Atomic stock decrement on sale creation
- 409 on insufficient stock
- Server-side total recalculation (client value ignored)
- camelCase fields in responses
"""

BASE = "/api/v1/sales"


def _sale_payload(product: dict, quantity: int = 1, discount: float = 0.0) -> dict:
    return {
        "productId": product["id"],
        "productName": product["name"],
        "productSku": product["sku"],
        "quantity": quantity,
        "unitPrice": product["price"],
        "discount": discount,
        "paymentMethod": "pix",
    }


# ── List ──────────────────────────────────────────────────────────────────────


def test_list_sales_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    assert "data" in r.json()
    assert isinstance(r.json()["data"], list)


# ── Create ────────────────────────────────────────────────────────────────────


def test_create_sale_returns_201(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product))
    assert r.status_code == 201


def test_create_sale_response_shape(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product))
    data = r.json()
    assert "id" in data
    assert "productId" in data
    assert "productName" in data
    assert "productSku" in data
    assert "unitPrice" in data
    assert "paymentMethod" in data
    assert "createdAt" in data


def test_create_sale_decrements_stock_atomically(client, created_product):
    initial_qty = created_product["quantity"]
    qty_to_sell = 3
    r = client.post(BASE, json=_sale_payload(created_product, quantity=qty_to_sell))
    assert r.status_code == 201

    # Stock must be decremented in the same transaction
    product = client.get(f"/api/v1/products/{created_product['id']}").json()
    assert product["quantity"] == initial_qty - qty_to_sell


def test_create_sale_insufficient_stock_returns_409(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product, quantity=9999))
    assert r.status_code == 409
    body = r.json()
    assert body["status"] == 409
    assert "message" in body
    assert "timestamp" in body


def test_create_sale_stock_not_decremented_on_failure(client, created_product):
    """Stock must remain unchanged when sale fails due to insufficient stock."""
    initial_qty = created_product["quantity"]
    client.post(BASE, json=_sale_payload(created_product, quantity=9999))
    product = client.get(f"/api/v1/products/{created_product['id']}").json()
    assert product["quantity"] == initial_qty


def test_create_sale_server_recalculates_total(client, created_product):
    """Backend must ignore client-provided total and recalculate it."""
    payload = {
        **_sale_payload(created_product, quantity=2, discount=10.0),
        "total": 9999.99,  # wrong — server must override
    }
    r = client.post(BASE, json=payload)
    assert r.status_code == 201
    # total = price * qty * (1 - discount/100)
    expected_total = round(created_product["price"] * 2 * (1 - 10.0 / 100), 2)
    assert r.json()["total"] == expected_total


def test_create_sale_product_not_found_returns_404(client):
    payload = {
        "productId": "nonexistent-id",
        "productName": "Ghost",
        "productSku": "GHO-000",
        "quantity": 1,
        "unitPrice": 10.0,
        "discount": 0.0,
        "paymentMethod": "pix",
    }
    r = client.post(BASE, json=payload)
    assert r.status_code == 404


def test_create_sale_invalid_payment_method_returns_422(client, created_product):
    payload = {**_sale_payload(created_product), "paymentMethod": "criptomoeda"}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422


def test_create_sale_zero_quantity_returns_422(client, created_product):
    payload = {**_sale_payload(created_product), "quantity": 0}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422


def test_list_sales_most_recent_first(client, created_product):
    # Create two sales
    client.post(BASE, json=_sale_payload(created_product, quantity=1))
    client.post(BASE, json=_sale_payload(created_product, quantity=1))
    sales = client.get(BASE).json()["data"]
    assert len(sales) >= 2
    # createdAt desc — first item must be >= second
    assert sales[0]["createdAt"] >= sales[1]["createdAt"]
