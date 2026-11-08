from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_serializer, field_validator, model_validator

from app.core.config import get_settings
from app.core.enums import ClothingSize, ProductCategory
from app.core.money import MoneyDecimal
from app.schemas.common import CamelModel, DatetimeISO

_ALLOWED_SIZES = {s.value for s in ClothingSize}


def build_public_image_url(stored: str | None) -> str | None:
    """Turn a relative storage path into an absolute public URL."""
    if not stored:
        return None
    if stored.startswith("http://") or stored.startswith("https://"):
        return stored
    base = get_settings().PUBLIC_BASE_URL.rstrip("/")
    path = stored if stored.startswith("/") else f"/{stored}"
    return f"{base}{path}"


class ProductInput(CamelModel):
    """Create product — quantity only allowed at creation."""

    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    category: ProductCategory
    sizes: list[str] = []
    colors: list[str] = []
    price: MoneyDecimal = Field(ge=Decimal("0"))
    promo_price: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))
    cost_price: MoneyDecimal = Field(ge=Decimal("0"))
    quantity: int = Field(default=0, ge=0)
    image_url: str | None = Field(default=None, max_length=1000)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("sizes")
    @classmethod
    def sizes_must_be_known(cls, v: list[str]) -> list[str]:
        invalid = [size for size in v if size not in _ALLOWED_SIZES]
        if invalid:
            raise ValueError(f"Tamanhos inválidos: {', '.join(invalid)}")
        return v

    @field_validator("colors")
    @classmethod
    def colors_length(cls, v: list[str]) -> list[str]:
        for color in v:
            if len(color) > 100:
                raise ValueError("Cada cor deve ter no máximo 100 caracteres")
        return v

    @model_validator(mode="after")
    def promo_not_above_price(self) -> ProductInput:
        if self.promo_price is not None and self.promo_price > self.price:
            raise ValueError("Preço promocional não pode ser maior que o preço")
        return self


class ProductPatchInput(CamelModel):
    """Partial update — quantity/stock MUST NOT be changed here."""

    sku: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    category: ProductCategory | None = None
    sizes: list[str] | None = None
    colors: list[str] | None = None
    price: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))
    promo_price: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))
    cost_price: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))
    image_url: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip().upper()

    @field_validator("sizes")
    @classmethod
    def sizes_must_be_known(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        invalid = [size for size in v if size not in _ALLOWED_SIZES]
        if invalid:
            raise ValueError(f"Tamanhos inválidos: {', '.join(invalid)}")
        return v

    @field_validator("colors")
    @classmethod
    def colors_length(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        for color in v:
            if len(color) > 100:
                raise ValueError("Cada cor deve ter no máximo 100 caracteres")
        return v

    @model_validator(mode="after")
    def promo_not_above_price(self) -> ProductPatchInput:
        if (
            self.promo_price is not None
            and self.price is not None
            and self.promo_price > self.price
        ):
            raise ValueError("Preço promocional não pode ser maior que o preço")
        return self


class ProductPublicResponse(CamelModel):
    """Catálogo público — sem costPrice."""

    id: str
    sku: str
    name: str
    description: str
    category: ProductCategory
    sizes: list[str]
    colors: list[str]
    price: MoneyDecimal
    promo_price: MoneyDecimal | None = None
    quantity: int
    image_url: str | None = None
    is_active: bool
    created_at: DatetimeISO
    updated_at: DatetimeISO

    @field_serializer("image_url")
    def serialize_image_url(self, v: str | None) -> str | None:
        return build_public_image_url(v)


class ProductResponse(ProductPublicResponse):
    """Resposta admin — inclui costPrice."""

    cost_price: MoneyDecimal


class StockPatchInput(CamelModel):
    delta: int

    @field_validator("delta")
    @classmethod
    def delta_not_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("Delta de estoque não pode ser zero")
        return v
