from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from app.core.enums import DonationCategory, DonationDirection
from app.core.money import MoneyDecimal
from app.schemas.common import CamelModel, DatetimeISO


class DonationInput(CamelModel):
    direction: DonationDirection = DonationDirection.recebida
    donor_name: str | None = Field(default=None, max_length=255)
    recipient_name: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    category: DonationCategory
    product_type: str | None = Field(default=None, max_length=255)
    monetary_value: MoneyDecimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def dinheiro_requires_positive_value(self) -> DonationInput:
        if self.category == DonationCategory.dinheiro and self.monetary_value <= 0:
            raise ValueError("Doação na categoria dinheiro deve ter valor monetário maior que zero")
        return self


class DonationPatchInput(CamelModel):
    direction: DonationDirection | None = None
    donor_name: str | None = Field(default=None, max_length=255)
    recipient_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    category: DonationCategory | None = None
    product_type: str | None = Field(default=None, max_length=255)
    monetary_value: MoneyDecimal | None = Field(default=None, ge=Decimal("0"))
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def dinheiro_requires_positive_value(self) -> DonationPatchInput:
        if (
            self.category == DonationCategory.dinheiro
            and self.monetary_value is not None
            and self.monetary_value <= 0
        ):
            raise ValueError("Doação na categoria dinheiro deve ter valor monetário maior que zero")
        return self


class DonationResponse(CamelModel):
    id: str
    direction: DonationDirection
    donor_name: str | None = None
    recipient_name: str | None = None
    description: str
    category: DonationCategory
    product_type: str | None = None
    monetary_value: MoneyDecimal
    notes: str
    created_at: DatetimeISO
