import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import ProductCategory


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    category: Mapped[str] = mapped_column(
        SAEnum(
            ProductCategory,
            name="product_category",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    sizes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    colors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    promo_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
