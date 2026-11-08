"""Tests for REST /api/v1/donations — admin-only after Fase 3."""

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


def test_list_donations_requires_auth(client):
    assert client.get(BASE).status_code == 401


def test_list_donations_operator_forbidden(client, operator_headers):
    assert client.get(BASE, headers=operator_headers).status_code == 403


def test_create_donation_requires_auth(client):
    assert client.post(BASE, json=DONATION_RECEIVED).status_code == 401


def test_list_donations_returns_envelope(client, admin_headers):
    r = client.get(BASE, headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == 0
    assert "skip" in body["meta"] and "limit" in body["meta"]


def test_create_donation_received_returns_201(client, admin_headers):
    r = client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers)
    assert r.status_code == 201


def test_create_donation_standard_envelope(client, admin_headers):
    r = client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers)
    body = r.json()
    assert body["success"] is True
    assert "data" in body


def test_create_donation_response_shape_camelcase(client, admin_headers):
    r = client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers)
    data = r.json()["data"]
    assert data["direction"] == "recebida"
    assert data["donorName"] == "Maria Silva"
    assert "createdAt" in data


def test_create_donation_direction_doada(client, admin_headers):
    r = client.post(BASE, json=DONATION_GIVEN, headers=admin_headers)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["direction"] == "doada"
    assert data["recipientName"] == "Família Ferreira"


def test_create_donation_monetary(client, admin_headers):
    r = client.post(BASE, json=DONATION_MONETARY, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["data"]["monetaryValue"] == 250.00


def test_create_donation_default_direction_is_recebida(client, admin_headers):
    payload = {
        "donorName": "Anônimo",
        "description": "Doação sem direção especificada",
        "category": "outros",
        "monetaryValue": 0.0,
    }
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["data"]["direction"] == "recebida"


def test_create_donation_product_type_optional(client, admin_headers):
    payload = {
        "direction": "recebida",
        "donorName": "Doador",
        "description": "Doação em dinheiro",
        "category": "dinheiro",
        "monetaryValue": 100.0,
    }
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 201


def test_create_donation_invalid_category_returns_422(client, admin_headers):
    payload = {**DONATION_RECEIVED, "category": "categoria_invalida"}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422


def test_create_donation_invalid_direction_returns_422(client, admin_headers):
    payload = {**DONATION_RECEIVED, "direction": "enviada"}
    r = client.post(BASE, json=payload, headers=admin_headers)
    assert r.status_code == 422


def test_delete_donation_returns_204(client, admin_headers):
    created = client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers).json()["data"]
    r = client.delete(f"{BASE}/{created['id']}", headers=admin_headers)
    assert r.status_code == 204


def test_delete_donation_not_found_returns_404(client, admin_headers):
    r = client.delete(f"{BASE}/00000000-0000-0000-0000-000000000099", headers=admin_headers)
    assert r.status_code == 404


def test_delete_donation_invalid_uuid_returns_422(client, admin_headers):
    r = client.delete(f"{BASE}/nonexistent-id-xyz", headers=admin_headers)
    assert r.status_code == 422


def test_list_donations_most_recent_first(client, admin_headers):
    client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers)
    client.post(
        BASE, json={**DONATION_RECEIVED, "donorName": "Segundo Doador"}, headers=admin_headers
    )
    donations = client.get(BASE, headers=admin_headers).json()["data"]
    assert len(donations) >= 2
    assert donations[0]["createdAt"] >= donations[1]["createdAt"]


def test_get_donation_by_id(client, admin_headers):
    created = client.post(BASE, json=DONATION_RECEIVED, headers=admin_headers).json()["data"]
    r = client.get(f"{BASE}/{created['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["donorName"] == DONATION_RECEIVED["donorName"]


def test_get_donation_not_found(client, admin_headers):
    r = client.get(f"{BASE}/00000000-0000-0000-0000-000000000099", headers=admin_headers)
    assert r.status_code == 404


def test_list_donations_pagination(client, admin_headers):
    for i in range(3):
        client.post(
            BASE, json={**DONATION_RECEIVED, "donorName": f"Doador {i}"}, headers=admin_headers
        )
    all_items = client.get(BASE, headers=admin_headers).json()["data"]
    page = client.get(f"{BASE}?skip=1&limit=1", headers=admin_headers).json()["data"]
    assert len(page) == 1
    assert page[0]["id"] == all_items[1]["id"]
