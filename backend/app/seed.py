"""Seed script — populates the database with initial data for development.

Idempotent: running multiple times will not create duplicate records.

Usage:
    python -m app.seed
    # or with Docker:
    docker compose exec api python -m app.seed
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.donation import Donation
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Seed data ─────────────────────────────────────────────────────────────────

PRODUCTS = [
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

DONATIONS = [
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

def seed_admin(db: Session) -> User:
    existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if existing:
        print(f"  [skip] Admin '{settings.ADMIN_EMAIL}' já existe.")
        return existing

    user = User(
        id=str(uuid.uuid4()),
        name="Admin",
        email=settings.ADMIN_EMAIL,
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        is_active=True,
        created_at=_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  [ok]   Admin criado: {settings.ADMIN_EMAIL}")
    return user


def seed_products(db: Session) -> list[Product]:
    seeded: list[Product] = []
    for data in PRODUCTS:
        existing = db.query(Product).filter(Product.sku == data["sku"]).first()
        if existing:
            print(f"  [skip] Produto '{data['sku']}' já existe.")
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
        print(f"  [ok]   Produto criado: {data['sku']} — {data['name']}")

    db.commit()
    for p in seeded:
        db.refresh(p)
    return seeded


def seed_sales(db: Session, products: list[Product]) -> None:
    # Skip if sales already exist (idempotency check by count)
    if db.query(Sale).count() > 0:
        print("  [skip] Vendas já existem.")
        return

    product_map = {p.sku: p for p in products}

    sales_data = [
        {
            "sku": "CAM-001",
            "quantity": 2,
            "payment_method": "pix",
            "customer_name": "Ana Paula",
            "discount": 0.0,
        },
        {
            "sku": "VES-001",
            "quantity": 1,
            "payment_method": "cartao_debito",
            "customer_name": "Beatriz Lima",
            "discount": 10.0,
        },
        {
            "sku": "CAL-001",
            "quantity": 1,
            "payment_method": "dinheiro",
            "customer_name": None,
            "discount": 0.0,
        },
    ]

    for data in sales_data:
        product = product_map.get(data["sku"])
        if product is None or product.quantity < data["quantity"]:
            print(f"  [skip] Venda {data['sku']} ignorada (produto ausente ou sem estoque).")
            continue

        total = round(product.price * data["quantity"] * (1 - data["discount"] / 100), 2)

        sale = Sale(
            id=str(uuid.uuid4()),
            product_id=product.id,
            product_name=product.name,
            product_sku=product.sku,
            quantity=data["quantity"],
            unit_price=product.price,
            discount=data["discount"],
            total=total,
            customer_name=data["customer_name"],
            payment_method=data["payment_method"],
            created_at=_now(),
        )
        db.add(sale)
        product.quantity -= data["quantity"]
        print(f"  [ok]   Venda criada: {data['sku']} × {data['quantity']}")

    db.commit()


def seed_donations(db: Session) -> None:
    if db.query(Donation).count() > 0:
        print("  [skip] Doações já existem.")
        return

    for data in DONATIONS:
        donation = Donation(
            id=str(uuid.uuid4()),
            created_at=_now(),
            **data,
        )
        db.add(donation)
        print(f"  [ok]   Doação criada: {data['direction']} — {data['description'][:40]}")

    db.commit()


def run_seed() -> None:
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
