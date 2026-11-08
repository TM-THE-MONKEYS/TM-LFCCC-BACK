"""Script de seed — popula o banco com dados iniciais para desenvolvimento.

Idempotente: pode ser executado várias vezes sem criar registros duplicados.

Bloqueado em production (use `python -m app.cli create-admin`).

Uso:
    python -m app.seed
    # ou com Docker:
    docker compose exec api python -m app.seed
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.donation import Donation
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User
from app.schemas.sale import SaleInput
from app.services.sale_service import SaleService


def _now() -> datetime:
    return datetime.now(UTC)


# ── Dados iniciais ────────────────────────────────────────────────────────────

PRODUCTS: list[dict[str, Any]] = [
    {
        "sku": "CAM-001",
        "name": "Camiseta Básica Branca",
        "description": "Camiseta de algodão, corte regular, ideal para o dia a dia.",
        "category": "camiseta",
        "sizes": ["PP", "P", "M", "G", "GG"],
        "colors": ["branca"],
        "price": 25.90,
        "promo_price": None,
        "cost_price": 12.00,
        "quantity": 50,
        "image_url": None,
        "is_active": True,
    },
    {
        "sku": "CAL-001",
        "name": "Calça Jeans Masculina",
        "description": "Calça jeans de corte reto, tecido resistente e confortável.",
        "category": "calca",
        "sizes": ["38", "40", "42", "44", "46"],
        "colors": ["azul escuro", "preto"],
        "price": 89.90,
        "promo_price": 79.90,
        "cost_price": 35.00,
        "quantity": 30,
        "image_url": None,
        "is_active": True,
    },
    {
        "sku": "VES-001",
        "name": "Vestido Floral Feminino",
        "description": "Vestido leve com estampa floral, perfeito para o verão.",
        "category": "vestido",
        "sizes": ["P", "M", "G"],
        "colors": ["azul", "rosa", "verde"],
        "price": 79.90,
        "promo_price": None,
        "cost_price": 28.00,
        "quantity": 25,
        "image_url": None,
        "is_active": True,
    },
    {
        "sku": "JAQ-001",
        "name": "Jaqueta de Couro",
        "description": "Jaqueta de couro sintético, estilo clássico.",
        "category": "jaqueta",
        "sizes": ["P", "M", "G", "GG"],
        "colors": ["preta"],
        "price": 299.90,
        "promo_price": 249.90,
        "cost_price": 120.00,
        "quantity": 0,  # esgotado — para testar comportamento de estoque zero
        "image_url": None,
        "is_active": True,
    },
    {
        "sku": "SAI-001",
        "name": "Saia Midi",
        "description": "Saia midi de tecido leve, comprimento na panturrilha.",
        "category": "saia",
        "sizes": ["P", "M", "G"],
        "colors": ["bege", "preta"],
        "price": 69.90,
        "promo_price": None,
        "cost_price": 25.00,
        "quantity": 20,
        "image_url": None,
        "is_active": True,
    },
]

DONATIONS: list[dict[str, Any]] = [
    {
        "direction": "recebida",
        "donor_name": "Maria Silva",
        "recipient_name": None,
        "description": "Lote de roupas femininas em bom estado",
        "category": "roupas",
        "product_type": "vestidos e blusas",
        "monetary_value": 0.0,
        "notes": "Entregue na sede na segunda-feira",
    },
    {
        "direction": "recebida",
        "donor_name": "João Santos",
        "recipient_name": None,
        "description": "Doação em dinheiro para o bazar de junho",
        "category": "dinheiro",
        "product_type": None,
        "monetary_value": 150.00,
        "notes": "",
    },
    {
        "direction": "doada",
        "donor_name": None,
        "recipient_name": "Família Oliveira",
        "description": "Roupas de inverno para família em situação de vulnerabilidade",
        "category": "roupas",
        "product_type": "casacos e agasalhos",
        "monetary_value": 0.0,
        "notes": "Entregue diretamente à família",
    },
    {
        "direction": "doada",
        "donor_name": None,
        "recipient_name": "Abrigo Esperança",
        "description": "Cestas básicas e alimentos não perecíveis",
        "category": "alimentos",
        "product_type": None,
        "monetary_value": 0.0,
        "notes": "Parceria mensal com o abrigo",
    },
]


# ── Seed functions ─────────────────────────────────────────────────────────────


def seed_admin(db: Session) -> User | None:
    """Cria admin inicial. Prefer CLI em produção (`python -m app.cli create-admin`)."""
    cfg = get_settings()
    email = cfg.ADMIN_EMAIL.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"  [skip] Admin '{email}' já existe.")
        return existing

    password = cfg.admin_password_value
    if password == "changeme" and cfg.ENVIRONMENT != "test":
        print(
            "  [warn] ADMIN_PASSWORD ainda é o padrão 'changeme'. "
            "Troque antes de ir para produção. Prefira: python -m app.cli create-admin"
        )

    user = User(
        id=str(uuid.uuid4()),
        name="Admin",
        email=email,
        password_hash=hash_password(password),
        role=UserRole.admin.value,
        is_active=True,
        created_at=_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  [ok]   Admin criado: {email} (role=admin)")
    return user


def seed_products(db: Session) -> list[Product]:
    seeded: list[Product] = []
    for data in PRODUCTS:
        sku = str(data["sku"])
        existing = db.query(Product).filter(Product.sku == sku).first()
        if existing:
            print(f"  [skip] Produto '{sku}' já existe.")
            seeded.append(existing)
            continue

        now = _now()
        product = Product(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **data,
        )
        db.add(product)
        seeded.append(product)
        print(f"  [ok]   Produto criado: {sku} — {data['name']}")

    db.commit()
    for p in seeded:
        db.refresh(p)
    return seeded


def seed_sales(db: Session, products: list[Product]) -> None:
    """Cria vendas de exemplo via SaleService (mesmas regras da API)."""
    if db.query(Sale).count() > 0:
        print("  [skip] Vendas já existem.")
        return

    product_map = {p.sku: p for p in products}
    service = SaleService(db)

    sales_data: list[dict[str, Any]] = [
        {
            "sku": "CAM-001",
            "quantity": 2,
            "payment_method": "pix",
            "customer_name": "Ana Paula",
            "discount": Decimal("0.00"),
        },
        {
            "sku": "VES-001",
            "quantity": 1,
            "payment_method": "cartao_debito",
            "customer_name": "Beatriz Lima",
            "discount": Decimal("10.00"),
        },
        {
            "sku": "CAL-001",
            "quantity": 1,
            "payment_method": "dinheiro",
            "customer_name": None,
            "discount": Decimal("0.00"),
        },
    ]

    for data in sales_data:
        sku = str(data["sku"])
        product = product_map.get(sku)
        qty = int(data["quantity"])
        if product is None or product.quantity < qty:
            print(f"  [skip] Venda {sku} ignorada (produto ausente ou sem estoque).")
            continue

        service.create(
            SaleInput(
                product_id=product.id,
                quantity=qty,
                payment_method=data["payment_method"],
                customer_name=data["customer_name"],
                discount=data["discount"],
            ),
            actor_role=UserRole.admin.value,
        )
        print(f"  [ok]   Venda criada: {sku} × {qty}")

    db.commit()


def seed_donations(db: Session) -> None:
    if db.query(Donation).count() > 0:
        print("  [skip] Doações já existem.")
        return

    for data in DONATIONS:
        description = str(data["description"])
        donation = Donation(
            id=str(uuid.uuid4()),
            created_at=_now(),
            **data,
        )
        db.add(donation)
        print(f"  [ok]   Doação criada: {data['direction']} — {description[:40]}")

    db.commit()


def run_seed() -> None:
    if get_settings().is_production:
        raise SystemExit("Seed bloqueado em production. Use: python -m app.cli create-admin")

    db: Session = SessionLocal()
    try:
        print("\n=== Seed: Admin ===")
        seed_admin(db)

        print("\n=== Seed: Produtos ===")
        products = seed_products(db)

        print("\n=== Seed: Vendas ===")
        seed_sales(db, products)

        print("\n=== Seed: Doações ===")
        seed_donations(db)

        print("\n✓ Seed concluído com sucesso.\n")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
