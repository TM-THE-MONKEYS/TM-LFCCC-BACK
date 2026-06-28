from typing import List

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.sale import Sale


class SaleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Sale]:
        return self.db.query(Sale).order_by(desc(Sale.created_at)).all()

    def create(self, sale: Sale) -> Sale:
        self.db.add(sale)
        self.db.flush()
        self.db.refresh(sale)
        return sale
