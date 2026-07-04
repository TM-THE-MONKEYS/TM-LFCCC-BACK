"""Initial migration — create all tables

Revision ID: 001
Revises:
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    product_category = postgresql.ENUM(
        "camiseta", "calca", "vestido", "saia", "jaqueta", "calcado", "acessorio", "outro",
        name="product_category",
    )
    payment_method = postgresql.ENUM(
        "dinheiro", "cartao_credito", "cartao_debito", "pix", "boleto",
        name="payment_method",
    )
    donation_direction = postgresql.ENUM(
        "recebida", "doada",
        name="donation_direction",
    )
    donation_category = postgresql.ENUM(
        "dinheiro", "roupas", "calcados", "acessorios", "alimentos", "outros",
        name="donation_category",
    )

    bind = op.get_bind()
    product_category.create(bind, checkfirst=True)
    payment_method.create(bind, checkfirst=True)
    donation_direction.create(bind, checkfirst=True)
    donation_category.create(bind, checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False, server_default=""),
        sa.Column(
            "category",
            sa.Enum(
                "camiseta", "calca", "vestido", "saia", "jaqueta", "calcado", "acessorio", "outro",
                name="product_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "sizes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "colors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("promo_price", sa.Float(), nullable=True),
        sa.Column("cost_price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    # ── sales ─────────────────────────────────────────────────────────────────
    op.create_table(
        "sales",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column(
            "payment_method",
            sa.Enum(
                "dinheiro", "cartao_credito", "cartao_debito", "pix", "boleto",
                name="payment_method",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("size", sa.String(20), nullable=True),
        sa.Column("color", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_sales_product_id", "sales", ["product_id"])
    op.create_index("ix_sales_created_at", "sales", ["created_at"])

    # ── donations ─────────────────────────────────────────────────────────────
    op.create_table(
        "donations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "direction",
            sa.Enum("recebida", "doada", name="donation_direction", create_type=False),
            nullable=False,
            server_default="recebida",
        ),
        sa.Column("donor_name", sa.String(255), nullable=True),
        sa.Column("recipient_name", sa.String(255), nullable=True),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "dinheiro", "roupas", "calcados", "acessorios", "alimentos", "outros",
                name="donation_category",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("product_type", sa.String(255), nullable=True),
        sa.Column("monetary_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(2000), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_donations_created_at", "donations", ["created_at"])


def downgrade() -> None:
    op.drop_table("donations")
    op.drop_table("sales")
    op.drop_table("products")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS donation_category")
    op.execute("DROP TYPE IF EXISTS donation_direction")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS product_category")
