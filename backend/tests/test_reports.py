"""Tests for REST /api/v1/reports — verifies aggregation contracts:
- GET /reports              → 200 ReportResponse
- Correct shape (all required fields)
- totalRevenue = sum of sale totals
- averageTicket = totalRevenue / totalSales
- totalCombined = totalRevenue + totalDonationsMonetary
- revenueByDay includes all days in window (zero days included)
- topProductsByRevenue and topProductsByUnits max 5 entries
"""

BASE = "/api/v1/reports"
PRODUCTS_BASE = "/api/v1/products"
SALES_BASE = "/api/v1/sales"
DONATIONS_BASE = "/api/v1/donations"

PRODUCT_A = {
    "sku": "RPT-001",
    "name": "Produto A",
    "description": "",
    "category": "camiseta",
    "sizes": ["M"],
    "colors": ["azul"],
    "price": 100.0,
    "costPrice": 50.0,
    "quantity": 100,
}

PRODUCT_B = {
    "sku": "RPT-002",
    "name": "Produto B",
    "description": "",
    "category": "calca",
    "sizes": ["M"],
    "colors": ["preto"],
    "price": 200.0,
    "costPrice": 80.0,
    "quantity": 100,
}


def _create_product(client, payload):
    r = client.post(PRODUCTS_BASE, json=payload)
    assert r.status_code == 201
    return r.json()["data"]


def _create_sale(client, product, qty=1, discount=0.0, method="pix"):
    r = client.post(
        SALES_BASE,
        json={
            "productId": product["id"],
            "quantity": qty,
            "unitPrice": product["price"],
            "discount": discount,
            "paymentMethod": method,
        },
    )
    assert r.status_code == 201
    return r.json()["data"]


def _create_donation(client, monetary_value=50.0, category="dinheiro"):
    r = client.post(
        DONATIONS_BASE,
        json={
            "direction": "recebida",
            "donorName": "Doador Teste",
            "description": "Doação de teste",
            "category": category,
            "monetaryValue": monetary_value,
        },
    )
    assert r.status_code == 201
    return r.json()["data"]


# ── Response shape ────────────────────────────────────────────────────────────


def test_reports_response_shape(client):
    r = client.get(BASE)
    assert r.status_code == 200
    data = r.json()
    required_keys = [
        "totalRevenue",
        "totalSales",
        "averageTicket",
        "totalDonationsMonetary",
        "totalDonationsCount",
        "totalCombined",
        "topProductsByRevenue",
        "topProductsByUnits",
        "salesByPaymentMethod",
        "revenueByDay",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_reports_empty_database(client):
    r = client.get(BASE)
    data = r.json()
    assert data["totalRevenue"] == 0
    assert data["totalSales"] == 0
    assert data["averageTicket"] == 0
    assert data["totalCombined"] == 0


# ── Aggregation correctness ───────────────────────────────────────────────────


def test_reports_total_revenue(client):
    p = _create_product(client, PRODUCT_A)
    _create_sale(client, p, qty=2)  # total = 100 * 2 = 200

    r = client.get(BASE)
    assert r.json()["totalRevenue"] == 200.0
    assert r.json()["totalSales"] == 1


def test_reports_average_ticket(client):
    p = _create_product(client, PRODUCT_A)
    _create_sale(client, p, qty=1)  # total = 100
    _create_sale(client, p, qty=3)  # total = 300

    r = client.get(BASE)
    data = r.json()
    assert data["totalRevenue"] == 400.0
    assert data["totalSales"] == 2
    assert data["averageTicket"] == 200.0  # 400 / 2


def test_reports_total_combined(client):
    p = _create_product(client, PRODUCT_A)
    _create_sale(client, p, qty=1)           # revenue = 100
    _create_donation(client, monetary_value=75.0)  # donation = 75

    r = client.get(BASE)
    data = r.json()
    assert data["totalRevenue"] == 100.0
    assert data["totalDonationsMonetary"] == 75.0
    assert data["totalCombined"] == 175.0


def test_reports_top_products_by_revenue(client):
    pa = _create_product(client, PRODUCT_A)
    pb = _create_product(client, PRODUCT_B)
    _create_sale(client, pa, qty=1)   # revenue A = 100
    _create_sale(client, pb, qty=2)   # revenue B = 400

    r = client.get(BASE)
    top = r.json()["topProductsByRevenue"]
    assert len(top) >= 1
    assert top[0]["sku"] == "RPT-002"  # B has higher revenue
    assert top[0]["revenue"] == 400.0


def test_reports_sales_by_payment_method(client):
    p = _create_product(client, PRODUCT_A)
    _create_sale(client, p, qty=1, method="pix")
    _create_sale(client, p, qty=1, method="dinheiro")

    r = client.get(BASE)
    by_method = r.json()["salesByPaymentMethod"]
    methods = {item["method"] for item in by_method}
    assert "pix" in methods
    assert "dinheiro" in methods
    # pct must sum to 100 (or very close)
    total_pct = sum(item["pct"] for item in by_method)
    assert abs(total_pct - 100.0) < 0.01


def test_reports_revenue_by_day_includes_all_days(client):
    r = client.get(f"{BASE}?days=7")
    by_day = r.json()["revenueByDay"]
    assert len(by_day) == 7
    # All entries must have the required fields
    for entry in by_day:
        assert "date" in entry
        assert "revenue" in entry
        assert "donations" in entry
        assert "count" in entry


def test_reports_filter_by_payment_method(client):
    p = _create_product(client, PRODUCT_A)
    _create_sale(client, p, qty=1, method="pix")
    _create_sale(client, p, qty=2, method="dinheiro")

    r_pix = client.get(f"{BASE}?paymentMethods=pix")
    assert r_pix.json()["totalSales"] == 1

    r_all = client.get(BASE)
    assert r_all.json()["totalSales"] == 2


def test_reports_top_products_max_5(client):
    """topProductsByRevenue and topProductsByUnits return at most 5 entries."""
    # Create 6 products and sell each once
    for i in range(6):
        p = _create_product(
            client,
            {**PRODUCT_A, "sku": f"TOP-{i:03d}", "name": f"Produto Top {i}"},
        )
        _create_sale(client, p, qty=1)

    r = client.get(BASE)
    assert len(r.json()["topProductsByRevenue"]) <= 5
    assert len(r.json()["topProductsByUnits"]) <= 5
