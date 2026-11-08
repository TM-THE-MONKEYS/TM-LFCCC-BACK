import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import DonationCategory
from app.exceptions import NotFoundError, UnprocessableError
from app.models.donation import Donation
from app.repositories.donation_repository import DonationRepository
from app.schemas.donation import DonationInput, DonationPatchInput


class DonationService:
    def __init__(self, db: Session) -> None:
        self._repo = DonationRepository(db)
        self._db = db

    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        direction: str | None = None,
        category: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> tuple[list[Donation], int]:
        return self._repo.list_filtered(
            skip=skip,
            limit=limit,
            direction=direction,
            category=category,
            from_dt=from_dt,
            to_dt=to_dt,
        )

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Donation]:
        items, _ = self.list_filtered(skip=skip, limit=limit)
        return items

    def get_by_id(self, donation_id: str) -> Donation:
        donation = self._repo.get_by_id(donation_id)
        if donation is None:
            raise NotFoundError(f"Doação com id '{donation_id}' não encontrada.")
        return donation

    def create(self, data: DonationInput) -> Donation:
        donation = Donation(
            id=str(uuid.uuid4()),
            direction=data.direction,
            donor_name=data.donor_name,
            recipient_name=data.recipient_name,
            description=data.description,
            category=data.category,
            product_type=data.product_type,
            monetary_value=data.monetary_value,
            notes=data.notes,
            created_at=datetime.now(UTC),
        )
        self._repo.create(donation)
        return donation

    def patch(self, donation_id: str, data: DonationPatchInput) -> Donation:
        donation = self.get_by_id(donation_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(donation, field, value)

        category = donation.category
        monetary = donation.monetary_value
        if category == DonationCategory.dinheiro and monetary <= 0:
            raise UnprocessableError(
                "Doação na categoria dinheiro deve ter valor monetário maior que zero"
            )

        self._repo.update(donation)
        return donation

    def delete(self, donation_id: str) -> None:
        donation = self.get_by_id(donation_id)
        self._repo.delete(donation)
