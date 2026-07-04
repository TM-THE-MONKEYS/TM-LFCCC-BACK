"""Tests for REST /api/v1/donations â€” verifies contracts:
- GET    /donations       â†’ 200 { "success": true, "data": [...] }
- GET    /donations/{id}  â†’ 200 StandardResponse[Donation]
- POST   /donations       â†’ 201 StandardResponse[Donation]
- DELETE /donations/{id}  â†’ 204
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
    "recipientName": "FamÃ­lia Ferreira",
    "description": "Roupas de inverno doadas",
    "category": "roupas",
    "productType": "casacos",
    "monetaryValue": 0.0,
    "notes": "",
}

DONATION_MONETARY = {
    "direction": "recebida",
    "donorName": "JoÃ£o EmpresÃ¡rio",
    "description": "DoaÃ§Ã£o em dinheiro para o bazar",
    "category": "dinheiro",
    "monetaryValue": 250.00,
    "notes": "TransferÃªncia bancÃ¡ria",
}


# â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_list_donations_returns_envelope(client):
    r = client.get(BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body
    assert isinstance(body["data"], list)


# â”€â”€ Create â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_create_donation_received_returns_201(client):
    r = client.post(BASE, json=DONATION_RECEIVED)
    assert r.status_code == 201


def test_create_donation_standard_envelope(client):
    r = client.post(BASE, json=DONATION_RECEIVED)
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "data" in body


def test_create_donation_response_shape_camelcase(client):
    r = client.post(BASE, json=DONATION_RECEIVED)
    data = r.json()["data"]
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
    data = r.json()["data"]
    assert data["direction"] == "doada"
    assert data["recipientName"] == "FamÃ­lia Ferreira"


def test_create_donation_monetary(client):
    r = client.post(BASE, json=DONATION_MONETARY)
    assert r.status_code == 201
    assert r.json()["data"]["monetaryValue"] == 250.00


def test_create_donation_default_direction_is_recebida(client):
    """When direction is omitted, backend defaults to 'recebida'."""
    payload = {
        "donorName": "AnÃ´nimo",
        "description": "DoaÃ§Ã£o sem direÃ§Ã£o especificada",
        "category": "outros",
        "monetaryValue": 0.0,
    }
    r = client.post(BASE, json=payload)
    assert r.status_code == 201
    assert r.json()["data"]["direction"] == "recebida"


def test_create_donation_product_type_optional(client):
    """productType may be absent for non-product categories."""
    payload = {
        "direction": "recebida",
        "donorName": "Doador",
        "description": "DoaÃ§Ã£o em dinheiro",
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


# â”€â”€ Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_delete_donation_returns_204(client):
    created = client.post(BASE, json=DONATION_RECEIVED).json()["data"]
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


# â”€â”€ Get by ID â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_get_donation_by_id(client):
    created = client.post(BASE, json=DONATION_RECEIVED).json()["data"]
    r = client.get(f"{BASE}/{created['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["id"] == created["id"]
    assert body["data"]["donorName"] == DONATION_RECEIVED["donorName"]


def test_get_donation_not_found(client):
    r = client.get(f"{BASE}/nonexistent-id-xyz")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "timestamp" in body


# â”€â”€ Pagination â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def test_list_donations_pagination(client):
    """skip/limit parameters must slice the result set."""
    for i in range(3):
        client.post(BASE, json={**DONATION_RECEIVED, "donorName": f"Doador {i}"})
    all_items = client.get(BASE).json()["data"]
    page = client.get(f"{BASE}?skip=1&limit=1").json()["data"]
    assert len(page) == 1
    assert page[0]["id"] == all_items[1]["id"]

