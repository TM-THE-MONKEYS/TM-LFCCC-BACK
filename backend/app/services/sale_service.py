import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sale import Sale
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.schemas.sale import SaleInput


class SaleService:
    def __init__(self, db: Session) -> None:
        self._sale_repo = SaleRepository(db)
        self._product_repo = ProductRepository(db)
        self._db = db

    def list_all(self) -> List[Sale]:
        return self._sale_repo.get_all()

    def create(self, data: SaleInput) -> Sale:
        # 1. Validate product exists
        product = self._product_repo.get_by_id(data.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produto com id '{data.product_id}' não encontrado.",
            )

        # 2. Validate sufficient stock
        if product.quantity < data.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Estoque insuficiente. Disponível: {product.quantity}, "
                    f"solicitado: {data.quantity}."
                ),
            )

        # 3. Recalculate total on the server — never trust client value
        calculated_total = round(
            data.unit_price * data.quantity * (1 - data.discount / 100), 2
        )

        now = datetime.now(timezone.utc)

        # 4. Create sale and decrement stock atomically (commit once at the end)
        sale = Sale(
            id=str(uuid.uuid4()),
            product_id=data.product_id,
            product_name=data.product_name,
            product_sku=data.product_sku,
            quantity=data.quantity,
            unit_price=data.unit_price,
            discount=data.discount,
            total=calculated_total,
            customer_name=data.customer_name,
            payment_method=data.payment_method.value,
            size=data.size,
            color=data.color,
            notes=data.notes,
            created_at=now,
        )
        self._sale_repo.create(sale)

        # Decrement stock — flush so both changes land in the same transaction
        product.quantity -= data.quantity
        product.updated_at = now
        self._product_repo.update(product)

        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        self._db.refresh(sale)
        return sale
