"""Validação de schemas (P1-7) — inválido → 422, nunca 500."""

from __future__ import annotations

import pytest

from tests.conftest import PRODUCT_PAYLOAD

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
DONATIONS = "/api/v1/donations"


@pytest.mark.parametrize(
    "patch",
    [
        {"price": -1},
        {"costPrice": -0.01},
        {"quantity": -1},
        {"promoPrice": -5},
        {"name": ""},
        {"sku": ""},
        {"promoPrice": 100.0, "price": 50.0},  # promo > price
    ],
    ids=[
        "price_negative",
        "cost_negative",
        "qty_negative",
        "promo_negative",
        "name_empty",
        "sku_empty",
        "promo_gt_price",
    ],
)
def test_product_invalid_returns_422(client, admin_headers, patch):
    payload = {**PRODUCT_PAYLOAD, "sku": "VAL-PROD", **patch}
    r = client.post(PRODUCTS, json=payload, headers=admin_headers)
    assert r.status_code == 422, r.text
    assert r.status_code != 500


def test_product_sku_normalized_uppercase(client, admin_headers):
    payload = {**PRODUCT_PAYLOAD, "sku": "  abc-99  "}
    r = client.post(PRODUCTS, json=payload, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["data"]["sku"] == "ABC-99"


@pytest.mark.parametrize(
    "patch",
    [
        {"quantity": 0},
        {"quantity": -1},
        {"discount": -1},
        {"discount": 101},
        {"unitPriceOverride": -1},
        {"paymentMethod": "criptomoeda"},
    ],
    ids=[
        "qty_zero",
        "qty_negative",
        "discount_neg",
        "discount_over",
        "override_neg",
        "payment_invalid",
    ],
)
def test_sale_invalid_returns_422(client, created_product, admin_headers, patch):
    payload = {
        "productId": created_product["id"],
        "quantity": 1,
        "discount": 0,
        "paymentMethod": "pix",
        **patch,
    }
    r = client.post(SALES, json=payload, headers=admin_headers)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    "payload",
    [
        {
            "description": "x",
            "category": "dinheiro",
            "monetaryValue": 0,
        },
        {
            "description": "x",
            "category": "dinheiro",
            "monetaryValue": -10,
        },
        {
            "description": "x",
            "category": "roupas",
            "monetaryValue": -1,
        },
        {
            "description": "",
            "category": "roupas",
            "monetaryValue": 0,
        },
    ],
    ids=["dinheiro_zero", "dinheiro_neg", "roupas_neg", "desc_empty"],
)
def test_donation_invalid_returns_422(client, admin_headers, payload):
    r = client.post(DONATIONS, json=payload, headers=admin_headers)
    assert r.status_code == 422, r.text


def test_stock_delta_zero_returns_422(client, created_product, admin_headers):
    r = client.patch(
        f"{PRODUCTS}/{created_product['id']}/stock",
        json={"delta": 0},
        headers=admin_headers,
    )
    assert r.status_code == 422, r.text
