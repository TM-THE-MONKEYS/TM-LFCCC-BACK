"""Tests for REST /api/v1/reports — StandardResponse envelope (Fase 5)."""

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


def _create_product(client, payload, headers):
    r = client.post(PRODUCTS_BASE, json=payload, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


def _create_sale(client, product, headers, qty=1, discount=0.0, method="pix"):
    r = client.post(
        SALES_BASE,
        json={
            "productId": product["id"],
            "quantity": qty,
            "discount": discount,
            "paymentMethod": method,
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["data"]


def _create_donation(
    client, headers, monetary_value=50.0, category="dinheiro", direction="recebida"
):
    payload = {
        "direction": direction,
        "description": "Doação de teste",
        "category": category,
        "monetaryValue": monetary_value,
    }
    if direction == "recebida":
        payload["donorName"] = "Doador Teste"
    else:
        payload["recipientName"] = "Beneficiário Teste"
    r = client.post(DONATIONS_BASE, json=payload, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


def _data(r):
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    return body["data"]


def test_reports_requires_auth(client):
    assert client.get(BASE).status_code == 401


def test_reports_operator_forbidden(client, operator_headers):
    assert client.get(BASE, headers=operator_headers).status_code == 403


def test_reports_response_shape(client, admin_headers):
    r = client.get(BASE, headers=admin_headers)
    assert r.status_code == 200
    data = _data(r)
    required_keys = [
        "totalRevenue",
        "totalSales",
        "averageTicket",
        "totalDonationsMonetary",
        "totalDonationsCount",
        "totalDonationsOutgoingMonetary",
        "totalDonationsOutgoingCount",
        "totalCombined",
        "topProductsByRevenue",
        "topProductsByUnits",
        "salesByPaymentMethod",
        "revenueByDay",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"


def test_reports_empty_database(client, admin_headers):
    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert data["totalRevenue"] == 0
    assert data["totalSales"] == 0
    assert data["averageTicket"] == 0
    assert data["totalCombined"] == 0


def test_reports_total_revenue(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=2)

    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert data["totalRevenue"] == 200.0
    assert data["totalSales"] == 1


def test_reports_average_ticket(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1)
    _create_sale(client, p, admin_headers, qty=3)

    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert data["totalRevenue"] == 400.0
    assert data["totalSales"] == 2
    assert data["averageTicket"] == 200.0


def test_reports_total_combined(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1)
    _create_donation(client, admin_headers, monetary_value=75.0)

    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert data["totalRevenue"] == 100.0
    assert data["totalDonationsMonetary"] == 75.0
    assert data["totalCombined"] == 175.0


def test_reports_doada_not_in_monetary_revenue(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1)
    _create_donation(client, admin_headers, monetary_value=50.0, direction="recebida")
    _create_donation(client, admin_headers, monetary_value=200.0, direction="doada")

    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert data["totalDonationsMonetary"] == 50.0
    assert data["totalDonationsOutgoingMonetary"] == 200.0
    assert data["totalCombined"] == 150.0


def test_reports_daily_sum_equals_total_revenue(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1)
    _create_sale(client, p, admin_headers, qty=2)

    r = client.get(f"{BASE}?days=7", headers=admin_headers)
    data = _data(r)
    daily_sum = round(sum(day["revenue"] for day in data["revenueByDay"]), 2)
    assert daily_sum == data["totalRevenue"]
    assert data["totalRevenue"] == 300.0


def test_reports_top_products_by_revenue(client, admin_headers):
    pa = _create_product(client, PRODUCT_A, admin_headers)
    pb = _create_product(client, PRODUCT_B, admin_headers)
    _create_sale(client, pa, admin_headers, qty=1)
    _create_sale(client, pb, admin_headers, qty=2)

    r = client.get(BASE, headers=admin_headers)
    top = _data(r)["topProductsByRevenue"]
    assert top[0]["sku"] == "RPT-002"
    assert top[0]["revenue"] == 400.0


def test_reports_sales_by_payment_method(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1, method="pix")
    _create_sale(client, p, admin_headers, qty=1, method="dinheiro")

    r = client.get(BASE, headers=admin_headers)
    by_method = _data(r)["salesByPaymentMethod"]
    methods = {item["method"] for item in by_method}
    assert "pix" in methods
    assert "dinheiro" in methods
    total_pct = sum(item["pct"] for item in by_method)
    assert abs(total_pct - 100.0) < 0.01


def test_reports_revenue_by_day_includes_all_days(client, admin_headers):
    r = client.get(f"{BASE}?days=7", headers=admin_headers)
    by_day = _data(r)["revenueByDay"]
    assert len(by_day) == 7


def test_reports_days_window_length(client, admin_headers):
    for days in (1, 14, 30):
        r = client.get(f"{BASE}?days={days}", headers=admin_headers)
        assert r.status_code == 200
        assert len(_data(r)["revenueByDay"]) == days


def test_reports_filter_by_payment_method(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    _create_sale(client, p, admin_headers, qty=1, method="pix")
    _create_sale(client, p, admin_headers, qty=2, method="dinheiro")

    r_pix = client.get(f"{BASE}?paymentMethods=pix", headers=admin_headers)
    assert _data(r_pix)["totalSales"] == 1

    r_all = client.get(BASE, headers=admin_headers)
    assert _data(r_all)["totalSales"] == 2


def test_reports_invalid_payment_method_returns_422(client, admin_headers):
    r = client.get(f"{BASE}?paymentMethods=pix,bitcoin", headers=admin_headers)
    assert r.status_code == 422


def test_reports_invalid_donation_category_returns_422(client, admin_headers):
    r = client.get(f"{BASE}?donationCategories=roupas,xyz", headers=admin_headers)
    assert r.status_code == 422


def test_reports_top_products_max_5(client, admin_headers):
    for i in range(6):
        p = _create_product(
            client,
            {**PRODUCT_A, "sku": f"TOP-{i:03d}", "name": f"Produto Top {i}"},
            admin_headers,
        )
        _create_sale(client, p, admin_headers, qty=1)

    r = client.get(BASE, headers=admin_headers)
    data = _data(r)
    assert len(data["topProductsByRevenue"]) <= 5
    assert len(data["topProductsByUnits"]) <= 5


def test_reports_excludes_cancelled_sales(client, admin_headers):
    p = _create_product(client, PRODUCT_A, admin_headers)
    sale = _create_sale(client, p, admin_headers, qty=1)
    assert (
        client.post(f"{SALES_BASE}/{sale['id']}/cancel", headers=admin_headers).status_code == 200
    )
    data = _data(client.get(BASE, headers=admin_headers))
    assert data["totalSales"] == 0
    assert data["totalRevenue"] == 0
