import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import DonationCategory, DonationDirection


class Donation(Base):
    __tablename__ = "donations"
    __table_args__ = (
        CheckConstraint("monetary_value >= 0", name="monetary_value_non_negative"),
        Index("ix_donations_category", "category"),
        Index("ix_donations_direction", "direction"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    direction: Mapped[DonationDirection] = mapped_column(
        SAEnum(
            DonationDirection,
            name="donation_direction",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
        ),
        nullable=False,
        default=DonationDirection.recebida,
    )
    donor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[DonationCategory] = mapped_column(
        SAEnum(
            DonationCategory,
            name="donation_category",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
        ),
        nullable=False,
    )
    product_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monetary_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
