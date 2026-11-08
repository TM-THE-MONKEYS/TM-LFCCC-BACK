"""Float → Numeric(12,2), check constraints e índices

Revision ID: 003
Revises: 002
Create Date: 2026-11-07 19:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── products: Float → Numeric(12,2) ───────────────────────────────────────
    op.execute(
        "ALTER TABLE products ALTER COLUMN price TYPE NUMERIC(12,2) USING ROUND(price::numeric, 2)"
    )
    op.execute(
        "ALTER TABLE products ALTER COLUMN promo_price TYPE NUMERIC(12,2) "
        "USING CASE WHEN promo_price IS NULL THEN NULL ELSE ROUND(promo_price::numeric, 2) END"
    )
    op.execute(
        "ALTER TABLE products ALTER COLUMN cost_price TYPE NUMERIC(12,2) "
        "USING ROUND(cost_price::numeric, 2)"
    )

    # ── sales ─────────────────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE sales ALTER COLUMN unit_price TYPE NUMERIC(12,2) "
        "USING ROUND(unit_price::numeric, 2)"
    )
    op.execute(
        "ALTER TABLE sales ALTER COLUMN discount TYPE NUMERIC(12,2) "
        "USING ROUND(discount::numeric, 2)"
    )
    op.execute(
        "ALTER TABLE sales ALTER COLUMN total TYPE NUMERIC(12,2) USING ROUND(total::numeric, 2)"
    )

    # ── donations ─────────────────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE donations ALTER COLUMN monetary_value TYPE NUMERIC(12,2) "
        "USING ROUND(monetary_value::numeric, 2)"
    )

    # ── Check constraints ─────────────────────────────────────────────────────
    op.create_check_constraint("ck_products_quantity_non_negative", "products", "quantity >= 0")
    op.create_check_constraint("ck_products_price_non_negative", "products", "price >= 0")
    op.create_check_constraint("ck_products_cost_price_non_negative", "products", "cost_price >= 0")
    op.create_check_constraint(
        "ck_products_promo_price_non_negative",
        "products",
        "promo_price IS NULL OR promo_price >= 0",
    )

    op.create_check_constraint("ck_sales_quantity_non_negative", "sales", "quantity >= 0")
    op.create_check_constraint("ck_sales_unit_price_non_negative", "sales", "unit_price >= 0")
    op.create_check_constraint(
        "ck_sales_discount_range", "sales", "discount >= 0 AND discount <= 100"
    )
    op.create_check_constraint("ck_sales_total_non_negative", "sales", "total >= 0")

    op.create_check_constraint(
        "ck_donations_monetary_value_non_negative",
        "donations",
        "monetary_value >= 0",
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_index("ix_sales_payment_method", "sales", ["payment_method"])
    op.create_index("ix_donations_category", "donations", ["category"])
    op.create_index("ix_donations_direction", "donations", ["direction"])


def downgrade() -> None:
    op.drop_index("ix_donations_direction", table_name="donations")
    op.drop_index("ix_donations_category", table_name="donations")
    op.drop_index("ix_sales_payment_method", table_name="sales")
    op.drop_index("ix_products_is_active", table_name="products")
    op.drop_index("ix_products_category", table_name="products")

    op.drop_constraint("ck_donations_monetary_value_non_negative", "donations", type_="check")
    op.drop_constraint("ck_sales_total_non_negative", "sales", type_="check")
    op.drop_constraint("ck_sales_discount_range", "sales", type_="check")
    op.drop_constraint("ck_sales_unit_price_non_negative", "sales", type_="check")
    op.drop_constraint("ck_sales_quantity_non_negative", "sales", type_="check")
    op.drop_constraint("ck_products_promo_price_non_negative", "products", type_="check")
    op.drop_constraint("ck_products_cost_price_non_negative", "products", type_="check")
    op.drop_constraint("ck_products_price_non_negative", "products", type_="check")
    op.drop_constraint("ck_products_quantity_non_negative", "products", type_="check")

    op.execute("ALTER TABLE donations ALTER COLUMN monetary_value TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE sales ALTER COLUMN total TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE sales ALTER COLUMN discount TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE sales ALTER COLUMN unit_price TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE products ALTER COLUMN cost_price TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE products ALTER COLUMN promo_price TYPE DOUBLE PRECISION")
    op.execute("ALTER TABLE products ALTER COLUMN price TYPE DOUBLE PRECISION")
