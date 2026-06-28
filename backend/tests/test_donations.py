"""Tests for REST /api/v1/donations — verifies contracts:
- GET    /donations       → 200 { "data": [...] }
- POST   /donations       → 201 Donation
- DELETE /donations/{id}  → 204
- All fields including direction, recipientName, productType
- camelCase fields in responses
- Default direction = recebida
"""

BASE = "/api/v1/donations"


DONATION_RECEIVED = {
    "direction": "recebida",
    "donorName": "Maria Silva",
    "description": "Roupas femininas usadas em bom estado",
    "category": "roupas",
    "productType": "vestidos e blusas",
    "monetaryValue": 0.0,
    "notes": "Entregue na sede",
}

DONATION_GIVEN = {
    "direction": "doada",
    "recipientName": "Família Ferreira",
    "description": "Roupas de inverno doadas",
    "category": "roupas",
    "productType": "casacos",
    "monetaryValue": 0.0,
    "notes": "",
}

DONATION_MONETARY = {
    "direction": "recebida",
    "donorName": "João Empresário",
    "description": "Doação em dinheiro para o bazar",
    "category": "dinheiro",
    "monetaryValue": 250.00,
    "notes": "Transferência bancária",
}


# ── List ──────────────────────────────────────────────────────────────────────


def test_list_donations_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    assert "data" in r.json()
    assert isinstance(r.json()["data"], list)


# ── Create ────────────────────────────────────────────────────────────────────


def test_create_donation_received_returns_201(client):
    r = client.post(BASE, json=DONATION_RECEIVED)
    assert r.status_code == 201


def test_create_donation_response_shape_camelcase(client):
    r = client.post(BASE, json=DONATION_RECEIVED)
    data = r.json()
    assert "id" in data
    assert "direction" in data
    assert "donorName" in data       # camelCase
    assert "monetaryValue" in data   # camelCase
    assert "createdAt" in data       # camelCase
    assert data["direction"] == "recebida"
    assert data["donorName"] == "Maria Silva"


def test_create_donation_direction_doada(client):
    r = client.post(BASE, json=DONATION_GIVEN)
    assert r.status_code == 201
    data = r.json()
    assert data["direction"] == "doada"
    assert data["recipientName"] == "Família Ferreira"


def test_create_donation_monetary(client):
    r = client.post(BASE, json=DONATION_MONETARY)
    assert r.status_code == 201
    assert r.json()["monetaryValue"] == 250.00


def test_create_donation_default_direction_is_recebida(client):
    """When direction is omitted, backend defaults to 'recebida'."""
    payload = {
        "donorName": "Anônimo",
        "description": "Doação sem direção especificada",
        "category": "outros",
        "monetaryValue": 0.0,
    }
    r = client.post(BASE, json=payload)
    assert r.status_code == 201
    assert r.json()["direction"] == "recebida"


def test_create_donation_product_type_optional(client):
    """productType may be absent for non-product categories."""
    payload = {
        "direction": "recebida",
        "donorName": "Doador",
        "description": "Doação em dinheiro",
        "category": "dinheiro",
        "monetaryValue": 100.0,
    }
    r = client.post(BASE, json=payload)
    assert r.status_code == 201


def test_create_donation_invalid_category_returns_422(client):
    payload = {**DONATION_RECEIVED, "category": "categoria_invalida"}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422
    assert r.json()["status"] == 422
    assert "details" in r.json()


def test_create_donation_invalid_direction_returns_422(client):
    payload = {**DONATION_RECEIVED, "direction": "enviada"}
    r = client.post(BASE, json=payload)
    assert r.status_code == 422


# ── Delete ────────────────────────────────────────────────────────────────────


def test_delete_donation_returns_204(client):
    created = client.post(BASE, json=DONATION_RECEIVED).json()
    r = client.delete(f"{BASE}/{created['id']}")
    assert r.status_code == 204
    assert r.content == b""


def test_delete_donation_not_found_returns_404(client):
    r = client.delete(f"{BASE}/nonexistent-id-xyz")
    assert r.status_code == 404
    assert r.json()["status"] == 404


def test_list_donations_most_recent_first(client):
    client.post(BASE, json=DONATION_RECEIVED)
    client.post(BASE, json={**DONATION_RECEIVED, "donorName": "Segundo Doador"})
    donations = client.get(BASE).json()["data"]
    assert len(donations) >= 2
    assert donations[0]["createdAt"] >= donations[1]["createdAt"]
