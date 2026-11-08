"""Fase 5 contract tests — pagination meta, filters, PATCH, soft-delete, cancel, envelopes."""

from __future__ import annotations

from tests.conftest import PRODUCT_PAYLOAD

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
DONATIONS = "/api/v1/donations"
REPORTS = "/api/v1/reports"

MISSING_UUID = "00000000-0000-0000-0000-000000000099"
INVALID_UUID = "not-a-uuid"


def test_list_products_includes_meta(client, created_product):
    r = client.get(PRODUCTS)
    assert r.status_code == 200
    body = r.json()
    assert "meta" in body
    assert body["meta"]["total"] >= 1
    assert body["meta"]["skip"] == 0
    assert body["meta"]["limit"] == 100


def test_list_sales_includes_meta(client, created_product, admin_headers):
    client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 1, "paymentMethod": "pix"},
        headers=admin_headers,
    )
    body = client.get(SALES, headers=admin_headers).json()
    assert body["meta"]["total"] >= 1
    assert "skip" in body["meta"] and "limit" in body["meta"]


def test_list_donations_includes_meta(client, admin_headers):
    client.post(
        DONATIONS,
        json={
            "direction": "recebida",
            "donorName": "A",
            "description": "x",
            "category": "roupas",
        },
        headers=admin_headers,
    )
    body = client.get(DONATIONS, headers=admin_headers).json()
    assert body["meta"]["total"] >= 1


def test_products_filter_q_and_category(client, admin_headers):
    client.post(PRODUCTS, json={**PRODUCT_PAYLOAD, "sku": "FLT-CAM"}, headers=admin_headers)
    client.post(
        PRODUCTS,
        json={**PRODUCT_PAYLOAD, "sku": "FLT-CAL", "category": "calca", "name": "Calça X"},
        headers=admin_headers,
    )
    by_q = client.get(f"{PRODUCTS}?q=Calça").json()["data"]
    assert any(p["sku"] == "FLT-CAL" for p in by_q)
    by_cat = client.get(f"{PRODUCTS}?category=camiseta").json()["data"]
    assert all(p["category"] == "camiseta" for p in by_cat)


def test_products_filter_in_stock(client, admin_headers):
    client.post(
        PRODUCTS,
        json={**PRODUCT_PAYLOAD, "sku": "ZERO-1", "quantity": 0},
        headers=admin_headers,
    )
    client.post(
        PRODUCTS,
        json={**PRODUCT_PAYLOAD, "sku": "STOCK-1", "quantity": 5},
        headers=admin_headers,
    )
    in_stock = client.get(f"{PRODUCTS}?inStock=true").json()["data"]
    assert all(p["quantity"] > 0 for p in in_stock)
    assert any(p["sku"] == "STOCK-1" for p in in_stock)


def test_patch_product_partial_does_not_change_quantity(client, created_product, admin_headers):
    initial_qty = created_product["quantity"]
    r = client.patch(
        f"{PRODUCTS}/{created_product['id']}",
        json={"name": "Nome Parcial", "price": 33.0},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Nome Parcial"
    assert data["price"] == 33.0
    assert data["quantity"] == initial_qty


def test_soft_delete_hides_from_public_catalog(client, created_product, admin_headers):
    pid = created_product["id"]
    r = client.delete(f"{PRODUCTS}/{pid}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get(f"{PRODUCTS}/{pid}").status_code == 404
    listed = client.get(PRODUCTS).json()["data"]
    assert all(p["id"] != pid for p in listed)
    manage = client.get(f"{PRODUCTS}/{pid}/manage", headers=admin_headers)
    assert manage.status_code == 200
    assert manage.json()["data"]["isActive"] is False
    assert "costPrice" in manage.json()["data"]


def test_manage_requires_admin(client, created_product, operator_headers):
    r = client.get(f"{PRODUCTS}/{created_product['id']}/manage", headers=operator_headers)
    assert r.status_code == 403


def test_operator_stock_response_has_no_cost_price(client, created_product, operator_headers):
    r = client.patch(
        f"{PRODUCTS}/{created_product['id']}/stock",
        json={"delta": 1},
        headers=operator_headers,
    )
    assert r.status_code == 200
    assert "costPrice" not in r.json()["data"]


def test_admin_stock_response_has_cost_price(client, created_product, admin_headers):
    r = client.patch(
        f"{PRODUCTS}/{created_product['id']}/stock",
        json={"delta": 1},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert "costPrice" in r.json()["data"]


def test_cancel_sale_restores_stock(client, created_product, admin_headers):
    initial = created_product["quantity"]
    sale = client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 2, "paymentMethod": "pix"},
        headers=admin_headers,
    ).json()["data"]
    mid = client.get(f"{PRODUCTS}/{created_product['id']}").json()["data"]["quantity"]
    assert mid == initial - 2
    cancel = client.post(f"{SALES}/{sale['id']}/cancel", headers=admin_headers)
    assert cancel.status_code == 200
    assert cancel.json()["data"]["cancelledAt"] is not None
    restored = client.get(f"{PRODUCTS}/{created_product['id']}").json()["data"]["quantity"]
    assert restored == initial
    # Cancelled sale excluded from default list
    listed = client.get(SALES, headers=admin_headers).json()["data"]
    assert all(s["id"] != sale["id"] for s in listed)


def test_cancel_sale_twice_returns_409(client, created_product, admin_headers):
    sale = client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 1, "paymentMethod": "pix"},
        headers=admin_headers,
    ).json()["data"]
    assert client.post(f"{SALES}/{sale['id']}/cancel", headers=admin_headers).status_code == 200
    assert client.post(f"{SALES}/{sale['id']}/cancel", headers=admin_headers).status_code == 409


def test_patch_donation(client, admin_headers):
    created = client.post(
        DONATIONS,
        json={
            "direction": "recebida",
            "donorName": "Antes",
            "description": "desc",
            "category": "roupas",
        },
        headers=admin_headers,
    ).json()["data"]
    r = client.patch(
        f"{DONATIONS}/{created['id']}",
        json={"donorName": "Depois", "notes": "ok"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["donorName"] == "Depois"
    assert r.json()["data"]["notes"] == "ok"


def test_reports_envelope(client, admin_headers):
    r = client.get(REPORTS, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "totalRevenue" in body["data"]
    assert "revenueByDay" in body["data"]


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/v1/this-route-does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "message" in body
    assert "timestamp" in body
    assert "success" not in body


def test_invalid_path_uuid_returns_422(client, admin_headers):
    assert client.get(f"{PRODUCTS}/{INVALID_UUID}").status_code == 422
    assert client.get(f"{SALES}/{INVALID_UUID}", headers=admin_headers).status_code == 422
    assert client.get(f"{DONATIONS}/{INVALID_UUID}", headers=admin_headers).status_code == 422


def test_missing_uuid_returns_404(client, admin_headers):
    assert client.get(f"{PRODUCTS}/{MISSING_UUID}").status_code == 404
    assert client.get(f"{SALES}/{MISSING_UUID}", headers=admin_headers).status_code == 404
    assert client.get(f"{DONATIONS}/{MISSING_UUID}", headers=admin_headers).status_code == 404


def test_sales_filter_payment_method(client, created_product, admin_headers):
    client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 1, "paymentMethod": "pix"},
        headers=admin_headers,
    )
    client.post(
        SALES,
        json={"productId": created_product["id"], "quantity": 1, "paymentMethod": "dinheiro"},
        headers=admin_headers,
    )
    pix = client.get(f"{SALES}?paymentMethod=pix", headers=admin_headers).json()["data"]
    assert pix and all(s["paymentMethod"] == "pix" for s in pix)


def test_donations_filter_direction(client, admin_headers):
    client.post(
        DONATIONS,
        json={
            "direction": "recebida",
            "donorName": "A",
            "description": "r",
            "category": "roupas",
        },
        headers=admin_headers,
    )
    client.post(
        DONATIONS,
        json={
            "direction": "doada",
            "recipientName": "B",
            "description": "d",
            "category": "roupas",
        },
        headers=admin_headers,
    )
    doadas = client.get(f"{DONATIONS}?direction=doada", headers=admin_headers).json()["data"]
    assert doadas and all(d["direction"] == "doada" for d in doadas)
