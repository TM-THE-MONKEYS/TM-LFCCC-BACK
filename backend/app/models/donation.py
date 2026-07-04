import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import DonationCategory, DonationDirection


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    direction: Mapped[str] = mapped_column(
        SAEnum(
            DonationDirection,
            name="donation_direction",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DonationDirection.recebida.value,
    )
    donor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum(
            DonationCategory,
            name="donation_category",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    product_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monetary_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
