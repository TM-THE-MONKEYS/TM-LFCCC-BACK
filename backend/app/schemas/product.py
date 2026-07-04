from typing import List, Optional

from pydantic import field_validator

from app.core.enums import ProductCategory
from app.schemas.common import CamelModel, DatetimeISO


class ProductInput(CamelModel):
    sku: str
    name: str
    description: str = ""
    category: ProductCategory
    sizes: List[str] = []
    colors: List[str] = []
    price: float
    promo_price: Optional[float] = None
    cost_price: float
    quantity: int = 0
    image_url: Optional[str] = None

    @field_validator("price", "cost_price")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Valor deve ser maior ou igual a zero")
        return v

    @field_validator("promo_price")
    @classmethod
    def promo_price_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Valor deve ser maior ou igual a zero")
        return v

    @field_validator("quantity")
    @classmethod
    def quantity_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantidade deve ser maior ou igual a zero")
        return v


class ProductResponse(CamelModel):
    id: str
    sku: str
    name: str
    description: str
    category: ProductCategory
    sizes: List[str]
    colors: List[str]
    price: float
    promo_price: Optional[float] = None
    cost_price: float
    quantity: int
    image_url: Optional[str] = None
    is_active: bool
    created_at: DatetimeISO
    updated_at: DatetimeISO


class StockPatchInput(CamelModel):
    delta: int
