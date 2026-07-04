"""Tests for REST /api/v1/sales â€” verifies contracts:
- GET  /sales           â†’ 200 { "success": true, "data": [...] }
- GET  /sales/{id}      â†’ 200 { "success": true, "data": Sale }
- POST /sales           â†’ 201 StandardResponse[Sale]
- Atomic stock decrement on sale creation
- 409 on insufficient stock
- Server-side total recalculation
- Server-side snapshot: productName/productSku taken from DB
- Pagination via skip/limit
"""

BASE = "/api/v1/sales"


def _sale_payload(product: dict, quantity: int = 1, discount: float = 0.0) -> dict:
    return {
        "productId": product["id"],
        "quantity": quantity,
        "unitPrice": product["price"],
        "discount": discount,
        "paymentMethod": "pix",
    }


# â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_list_sales_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body
    assert isinstance(body["data"], list)


# â”€â”€ Create â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_create_sale_returns_201(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product))
    assert r.status_code == 201


def test_create_sale_standard_envelope(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product))
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body


def test_create_sale_response_shape(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product))
    data = r.json()["data"]
    assert "id" in data
    assert "productId" in data
    assert "productName" in data
    assert "productSku" in data
    assert "unitPrice" in data
    assert "paymentMethod" in data
    assert "createdAt" in data


def test_create_sale_snapshot_uses_db_name_and_sku(client, created_product):
    """productName and productSku in the response must come from the DB."""
    r = client.post(BASE, json=_sale_payload(created_product))
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["productName"] == created_product["name"]
    assert data["productSku"] == created_product["sku"]


def test_create_sale_decrements_stock_atomically(client, created_product):
    initial_qty = created_product["quantity"]
    qty_to_sell = 3
    r = client.post(BASE, json=_sale_payload(created_product, quantity=qty_to_sell))
    assert r.status_code == 201
    product = client.get(f"/api/v1/products/{created_product['id']}").json()["data"]
    assert product["quantity"] == initial_qty - qty_to_sell


def test_create_sale_insufficient_stock_returns_409(client, created_product):
    r = client.post(BASE, json=_sale_payload(created_product, quantity=9999))
    assert r.status_code == 409
    body = r.json()
    assert body["status"] == 409
    assert "message" in body
    assert "timestamp" in body


def test_create_sale_stock_not_decremented_on_failure(client, created_product):
    """Stock must remain unchanged when sale fails."""
    initial_qty = created_product["quantity"]
    client.post(BASE, json=_sale_payload(created_product, quantity=9999))
    product = client.get(f"/api/v1/products/{created_product['id']}").json()["data"]
    assert product["quantity"] == initial_qty


def test_create_sale_server_recalculates_total(client, created_product):
    """Backend recalculates total â€” ignores any client-provided value."""
    payload = _sale_payload(created_product, quantity=2, discount=10.0)
    r = client.post(BASE, json=payload)
    assert r.status_code == 201
    expected_total = round(created_product["price"] * 2 * (1 - 10.0 / 100), 2)
    assert r.json()["data"]["total"] == expected_total


def test_create_sale_product_not_found_returns_404(client):
    payload = {
        "productId": "nonexistent-id",
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


# â”€â”€ Get by ID â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_get_sale_by_id(client, created_product):
    created = client.post(BASE, json=_sale_payload(created_product)).json()["data"]
    r = client.get(f"{BASE}/{created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert r.json()["data"]["id"] == created["id"]


def test_get_sale_not_found(client):
    r = client.get(f"{BASE}/nonexistent-id")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "timestamp" in body


# â”€â”€ Pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_list_sales_pagination(client, created_product):
    for _ in range(3):
        client.post(BASE, json=_sale_payload(created_product, quantity=1))
    all_sales = client.get(BASE).json()["data"]
    page = client.get(f"{BASE}?skip=1&limit=1").json()["data"]
    assert len(page) == 1
    assert page[0]["id"] == all_sales[1]["id"]


def test_list_sales_most_recent_first(client, created_product):
    client.post(BASE, json=_sale_payload(created_product, quantity=1))
    client.post(BASE, json=_sale_payload(created_product, quantity=1))
    sales = client.get(BASE).json()["data"]
    assert len(sales) >= 2
    assert sales[0]["createdAt"] >= sales[1]["createdAt"]

