import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import ProductCategory

_JsonList = JSON().with_variant(JSONB(), "postgresql")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("cost_price >= 0", name="cost_price_non_negative"),
        CheckConstraint(
            "promo_price IS NULL OR promo_price >= 0",
            name="promo_price_non_negative",
        ),
        Index("ix_products_category", "category"),
        Index("ix_products_is_active", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    category: Mapped[ProductCategory] = mapped_column(
        SAEnum(
            ProductCategory,
            name="product_category",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
        ),
        nullable=False,
    )
    sizes: Mapped[list] = mapped_column(_JsonList, nullable=False, default=list)
    colors: Mapped[list] = mapped_column(_JsonList, nullable=False, default=list)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    promo_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Fonte única de atualização: onupdate do ORM (não duplicar no service)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
