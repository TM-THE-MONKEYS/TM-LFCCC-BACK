import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.donation import Donation
from app.repositories.donation_repository import DonationRepository
from app.schemas.donation import DonationInput


class DonationService:
    def __init__(self, db: Session) -> None:
        self._repo = DonationRepository(db)
        self._db = db

    def list_all(self) -> List[Donation]:
        return self._repo.get_all()

    def create(self, data: DonationInput) -> Donation:
        donation = Donation(
            id=str(uuid.uuid4()),
            direction=data.direction.value,
            donor_name=data.donor_name,
            recipient_name=data.recipient_name,
            description=data.description,
            category=data.category.value,
            product_type=data.product_type,
            monetary_value=data.monetary_value,
            notes=data.notes,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.create(donation)
        self._db.commit()
        self._db.refresh(donation)
        return donation

    def delete(self, donation_id: str) -> None:
        donation = self._repo.get_by_id(donation_id)
        if donation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doação com id '{donation_id}' não encontrada.",
            )
        self._repo.delete(donation)
        self._db.commit()
