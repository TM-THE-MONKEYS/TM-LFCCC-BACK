from datetime import datetime

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.models.sale import Sale


class SaleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _apply_filters(
        self,
        stmt: Select,
        *,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        payment_method: str | None = None,
        product_id: str | None = None,
        include_cancelled: bool = False,
    ) -> Select:
        if not include_cancelled:
            stmt = stmt.where(Sale.cancelled_at.is_(None))
        if from_dt is not None:
            stmt = stmt.where(Sale.created_at >= from_dt)
        if to_dt is not None:
            stmt = stmt.where(Sale.created_at <= to_dt)
        if payment_method is not None:
            stmt = stmt.where(Sale.payment_method == payment_method)
        if product_id is not None:
            stmt = stmt.where(Sale.product_id == product_id)
        return stmt

    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        payment_method: str | None = None,
        product_id: str | None = None,
        include_cancelled: bool = False,
    ) -> tuple[list[Sale], int]:
        base = select(Sale)
        base = self._apply_filters(
            base,
            from_dt=from_dt,
            to_dt=to_dt,
            payment_method=payment_method,
            product_id=product_id,
            include_cancelled=include_cancelled,
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.scalar(count_stmt) or 0)
        stmt = base.order_by(desc(Sale.created_at)).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Sale]:
        items, _ = self.list_filtered(skip=skip, limit=limit)
        return items

    def get_by_id(self, sale_id: str) -> Sale | None:
        return self.db.scalar(select(Sale).where(Sale.id == sale_id))

    def create(self, sale: Sale) -> Sale:
        self.db.add(sale)
        self.db.flush()
        return sale

    def update(self, sale: Sale) -> Sale:
        self.db.flush()
        return sale
