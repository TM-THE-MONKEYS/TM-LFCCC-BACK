from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.sale import Sale


class SaleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Sale]:
        return (
            self.db.query(Sale)
            .order_by(desc(Sale.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id(self, sale_id: str) -> Optional[Sale]:
        return self.db.query(Sale).filter(Sale.id == sale_id).first()

    def create(self, sale: Sale) -> Sale:
        self.db.add(sale)
        self.db.flush()
        self.db.refresh(sale)
        return sale
