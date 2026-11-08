"""Tests for REST /api/v1/products — Fase 3 auth + public catalog."""

from tests.conftest import PRODUCT_PAYLOAD

BASE = "/api/v1/products"


# ── Public list / get ─────────────────────────────────────────────────────────


def test_list_products_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == 0
    assert body["meta"]["skip"] == 0
    assert body["meta"]["limit"] == 100


def test_list_products_empty(client):
    r = client.get(BASE)
    assert r.json()["data"] == []


def test_public_catalog_has_no_cost_price(client, created_product):
    listed = client.get(BASE).json()["data"]
    assert listed
    assert "costPrice" not in listed[0]
    detail = client.get(f"{BASE}/{created_product['id']}").json()["data"]
    assert "costPrice" not in detail
    assert detail["sku"] == created_product["sku"]


# ── Create (admin) ────────────────────────────────────────────────────────────


def test_create_product_requires_auth(client):
    r = client.post(BASE, json=PRODUCT_PAYLOAD)
    assert r.status_code == 401


def test_create_product_operator_forbidden(client, operator_headers):
    r = client.post(BASE, json=PRODUCT_PAYLOAD, headers=operator_headers)
    assert r.status_code == 403


def test_create_product_returns_201(client, admin_headers):
    r = client.post(BASE, json=PRODUCT_PAYLOAD, headers=admin_headers)
    assert r.status_code == 201


def test_create_product_standard_envelope(client, admin_headers):
    r = client.post(BASE, json=PRODUCT_PAYLOAD, headers=admin_headers)
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body


def test_create_product_response_shape(client, admin_headers):
    r = client.post(BASE, json=PRODUCT_PAYLOAD, headers=admin_headers)
    data = r.json()["data"]
    assert "id" in data
    assert "sku" in data
    assert "createdAt" in data
    assert "updatedAt" in data
    assert "isActive" in data
    assert "costPrice" in data  # admin write response keeps cost
    assert data["sku"] == PRODUCT_PAYLOAD["sku"]
    assert data["isActive"] is True


def test_create_product_duplicate_sku_returns_409(client, admin_headers):
    client.post(BASE, json=PRODUCT_PAYLOAD, headers=admin_headers)
    r = client.post(BASE, json=PRODUCT_PAYLOAD, headers=admin_headers)
    assert r.status_code == 409
    body = r.json()
    assert body["status"] == 409
    assert "timestamp" in body


def test_create_product_invalid_category_returns_422(client, admin_headers):
    payload = {**PRODUCT_PAYLOAD, "sku": "ERR-001", "category": "categoria_invalida"}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422
    assert "details" in r.json()


def test_create_product_negative_price_returns_422(client, admin_headers):
    payload = {**PRODUCT_PAYLOAD, "sku": "ERR-002", "price": -10}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422


# ── Read by ID ────────────────────────────────────────────────────────────────


def test_get_product_by_id(client, created_product):
    r = client.get(f"{BASE}/{created_product['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["id"] == created_product["id"]
    assert "costPrice" not in body["data"]


def test_get_product_not_found(client):
    r = client.get(f"{BASE}/00000000-0000-0000-0000-000000000099")
    assert r.status_code == 404


def test_get_product_invalid_uuid_returns_422(client):
    r = client.get(f"{BASE}/nonexistent-id-xyz")
    assert r.status_code == 422


# ── Update (PATCH partial) ────────────────────────────────────────────────────


def test_update_product(client, created_product, admin_headers):
    r = client.patch(
        f"{BASE}/{created_product['id']}",
        json={"name": "Nome Atualizado", "price": 59.90},
        headers=admin_headers,
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Nome Atualizado"
    assert data["price"] == 59.90


def test_update_product_duplicate_sku(client, created_product, admin_headers):
    second = client.post(
        BASE, json={**PRODUCT_PAYLOAD, "sku": "TEST-002"}, headers=admin_headers
    ).json()["data"]
    r = client.patch(
        f"{BASE}/{second['id']}",
        json={"sku": PRODUCT_PAYLOAD["sku"]},
        headers=admin_headers,
    )
    assert r.status_code == 409


# ── Soft delete ───────────────────────────────────────────────────────────────


def test_delete_product_returns_204(client, created_product, admin_headers):
    r = client.delete(f"{BASE}/{created_product['id']}", headers=admin_headers)
    assert r.status_code == 204
    assert r.content == b""


def test_delete_product_then_get_returns_404(client, created_product, admin_headers):
    client.delete(f"{BASE}/{created_product['id']}", headers=admin_headers)
    r = client.get(f"{BASE}/{created_product['id']}")
    assert r.status_code == 404


# ── Stock patch ───────────────────────────────────────────────────────────────


def test_patch_stock_decrements(client, created_product, operator_headers):
    initial_qty = created_product["quantity"]
    r = client.patch(
        f"{BASE}/{created_product['id']}/stock",
        json={"delta": -3},
        headers=operator_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["quantity"] == initial_qty - 3


def test_patch_stock_insufficient_stock_returns_409(client, created_product, admin_headers):
    r = client.patch(
        f"{BASE}/{created_product['id']}/stock",
        json={"delta": -9999},
        headers=admin_headers,
    )
    assert r.status_code == 409


def test_patch_stock_increments(client, created_product, admin_headers):
    initial_qty = created_product["quantity"]
    r = client.patch(
        f"{BASE}/{created_product['id']}/stock",
        json={"delta": 5},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["quantity"] == initial_qty + 5


def test_patch_stock_requires_auth(client, created_product):
    r = client.patch(f"{BASE}/{created_product['id']}/stock", json={"delta": 1})
    assert r.status_code == 401


# ── Pagination ────────────────────────────────────────────────────────────────


def test_list_products_pagination(client, admin_headers):
    skus = ["PAG-001", "PAG-002", "PAG-003"]
    for sku in skus:
        client.post(BASE, json={**PRODUCT_PAYLOAD, "sku": sku}, headers=admin_headers)
    all_products = client.get(BASE).json()["data"]
    page = client.get(f"{BASE}?skip=1&limit=1").json()["data"]
    assert len(page) == 1
    assert page[0]["id"] == all_products[1]["id"]


def test_list_products_limit_enforced(client, admin_headers):
    for i in range(5):
        client.post(BASE, json={**PRODUCT_PAYLOAD, "sku": f"LIM-{i:03d}"}, headers=admin_headers)
    page = client.get(f"{BASE}?limit=2").json()["data"]
    assert len(page) == 2


# ── Image upload ──────────────────────────────────────────────────────────────

# Valid 1×1 PNG that Pillow can load and re-encode
_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
    b"\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_upload_product_image_success(
    client, created_product, admin_headers, tmp_path, monkeypatch
):
    from app.services.product_service import ProductService
    from app.storage.local import LocalStorage

    storage = LocalStorage(base_dir=tmp_path)

    original_init = ProductService.__init__

    def _init(self, db, storage_arg=None):
        original_init(self, db, storage=storage)

    monkeypatch.setattr(ProductService, "__init__", _init)

    r = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("pixel.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["imageUrl"] is not None
    assert "/uploads/products/" in body["data"]["imageUrl"]


def test_upload_fake_png_text_renamed_returns_422(
    client, created_product, admin_headers, tmp_path, monkeypatch
):
    from app.services.product_service import ProductService
    from app.storage.local import LocalStorage

    storage = LocalStorage(base_dir=tmp_path)
    original_init = ProductService.__init__

    def _init(self, db, storage_arg=None):
        original_init(self, db, storage=storage)

    monkeypatch.setattr(ProductService, "__init__", _init)

    r = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("fake.png", b"this is not a png file at all", "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_upload_product_image_invalid_type_returns_422(client, created_product, admin_headers):
    r = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("notes.txt", b"not-an-image", "text/plain")},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_upload_product_image_too_large_returns_422(
    client, created_product, admin_headers, monkeypatch
):
    from app.services import product_service

    monkeypatch.setattr(product_service, "_MAX_IMAGE_BYTES", 10)
    r = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("big.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert "grande" in r.json()["message"].lower() or "tamanho" in r.json()["message"].lower()


def test_upload_replace_deletes_old_image(
    client, created_product, admin_headers, tmp_path, monkeypatch
):
    from app.services.product_service import ProductService
    from app.storage.local import LocalStorage

    storage = LocalStorage(base_dir=tmp_path)
    original_init = ProductService.__init__

    def _init(self, db, storage_arg=None):
        original_init(self, db, storage=storage)

    monkeypatch.setattr(ProductService, "__init__", _init)

    r1 = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("pixel.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r1.status_code == 200
    first_url = r1.json()["data"]["imageUrl"]
    # Relative path stored under tmp_path/products
    first_files = list((tmp_path / "products").glob("*"))
    assert len(first_files) == 1
    old_name = first_files[0].name

    r2 = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("pixel2.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r2.status_code == 200
    second_url = r2.json()["data"]["imageUrl"]
    assert second_url != first_url
    remaining = list((tmp_path / "products").glob("*"))
    assert len(remaining) == 1
    assert remaining[0].name != old_name


def test_upload_product_image_product_not_found_returns_404(client, admin_headers):
    r = client.post(
        f"{BASE}/00000000-0000-0000-0000-000000000099/image",
        files={"file": ("pixel.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_upload_product_image_invalid_uuid_returns_422(client, admin_headers):
    r = client.post(
        f"{BASE}/nonexistent-id/image",
        files={"file": ("pixel.png", _MIN_PNG, "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_upload_requires_admin(client, created_product, operator_headers):
    r = client.post(
        f"{BASE}/{created_product['id']}/image",
        files={"file": ("pixel.png", _MIN_PNG, "image/png")},
        headers=operator_headers,
    )
    assert r.status_code == 403
