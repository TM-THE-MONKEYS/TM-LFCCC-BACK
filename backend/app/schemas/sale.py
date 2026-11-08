from decimal import Decimal

from pydantic import Field

from app.core.enums import PaymentMethod
from app.core.money import MoneyDecimal
from app.schemas.common import CamelModel, DatetimeISO


class SaleInput(CamelModel):
    """Client sends product, quantity and payment data — unit price comes from the product."""

    product_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(gt=0)
    discount: MoneyDecimal = Field(default=Decimal("0.00"), ge=Decimal("0"), le=Decimal("100"))
    customer_name: str | None = Field(default=None, max_length=255)
    payment_method: PaymentMethod
    size: str | None = Field(default=None, max_length=20)
    color: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    # Honored only when the authenticated user has role=admin; ignored for operator.
    unit_price_override: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))


class SaleResponse(CamelModel):
    id: str
    product_id: str | None = None
    product_name: str
    product_sku: str
    quantity: int
    unit_price: MoneyDecimal
    discount: MoneyDecimal
    total: MoneyDecimal
    customer_name: str | None = None
    payment_method: PaymentMethod
    size: str | None = None
    color: str | None = None
    notes: str | None = None
    cancelled_at: DatetimeISO | None = None
    created_at: DatetimeISO
