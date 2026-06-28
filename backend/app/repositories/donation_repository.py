from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.donation import Donation


class DonationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Donation]:
        return self.db.query(Donation).order_by(desc(Donation.created_at)).all()

    def get_by_id(self, donation_id: str) -> Optional[Donation]:
        return self.db.query(Donation).filter(Donation.id == donation_id).first()

    def create(self, donation: Donation) -> Donation:
        self.db.add(donation)
        self.db.flush()
        self.db.refresh(donation)
        return donation

    def delete(self, donation: Donation) -> None:
        self.db.delete(donation)
        self.db.flush()
