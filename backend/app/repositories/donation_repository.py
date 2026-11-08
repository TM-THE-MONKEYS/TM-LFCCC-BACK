from datetime import datetime

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.models.donation import Donation


class DonationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _apply_filters(
        self,
        stmt: Select,
        *,
        direction: str | None = None,
        category: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> Select:
        if direction is not None:
            stmt = stmt.where(Donation.direction == direction)
        if category is not None:
            stmt = stmt.where(Donation.category == category)
        if from_dt is not None:
            stmt = stmt.where(Donation.created_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(Donation.created_at <= to_dt)
        return stmt

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
        base = select(Donation)
        base = self._apply_filters(
            base,
            direction=direction,
            category=category,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.scalar(count_stmt) or 0)
        stmt = base.order_by(desc(Donation.created_at)).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Donation]:
        items, _ = self.list_filtered(skip=skip, limit=limit)
        return items

    def get_by_id(self, donation_id: str) -> Donation | None:
        return self.db.scalar(select(Donation).where(Donation.id == donation_id))

    def create(self, donation: Donation) -> Donation:
        self.db.add(donation)
        self.db.flush()
        return donation

    def update(self, donation: Donation) -> Donation:
        self.db.flush()
        return donation

    def delete(self, donation: Donation) -> None:
        self.db.delete(donation)
        self.db.flush()
