from typing import Optional

from pydantic import field_validator

from app.core.enums import PaymentMethod
from app.schemas.common import CamelModel, DatetimeISO


class SaleInput(CamelModel):
    product_id: str
    quantity: int
    unit_price: float
    discount: float = 0.0
    customer_name: Optional[str] = None
    payment_method: PaymentMethod
    size: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Preço unitário deve ser maior ou igual a zero")
        return v

    @field_validator("discount")
    @classmethod
    def discount_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("Desconto deve estar entre 0 e 100")
        return v


class SaleResponse(CamelModel):
    id: str
    product_id: Optional[str] = None
    product_name: str
    product_sku: str
    quantity: int
    unit_price: float
    discount: float
    total: float
    customer_name: Optional[str] = None
    payment_method: PaymentMethod
    size: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    created_at: DatetimeISO
