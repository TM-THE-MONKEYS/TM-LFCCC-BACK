from typing import Optional

from app.core.enums import DonationCategory, DonationDirection
from app.schemas.common import CamelModel, DatetimeISO


class DonationInput(CamelModel):
    direction: DonationDirection = DonationDirection.recebida
    donor_name: Optional[str] = None
    recipient_name: Optional[str] = None
    description: str
    category: DonationCategory
    product_type: Optional[str] = None
    monetary_value: float = 0.0
    notes: str = ""


class DonationResponse(CamelModel):
    id: str
    direction: DonationDirection
    donor_name: Optional[str] = None
    recipient_name: Optional[str] = None
    description: str
    category: DonationCategory
    product_type: Optional[str] = None
    monetary_value: float
    notes: str
    created_at: DatetimeISO
