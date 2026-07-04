import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import InsufficientStockError, NotFoundError
from app.models.sale import Sale
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.schemas.sale import SaleInput


class SaleService:
    def __init__(self, db: Session) -> None:
        self._sale_repo = SaleRepository(db)
        self._product_repo = ProductRepository(db)
        self._db = db

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Sale]:
        return self._sale_repo.get_all(skip=skip, limit=limit)

    def get_by_id(self, sale_id: str) -> Sale:
        sale = self._sale_repo.get_by_id(sale_id)
        if sale is None:
            raise NotFoundError(f"Venda com id '{sale_id}' não encontrada.")
        return sale

    def create(self, data: SaleInput) -> Sale:
        # 1. Verifica se o produto existe
        product = self._product_repo.get_by_id(data.product_id)
        if product is None:
            raise NotFoundError(f"Produto com id '{data.product_id}' não encontrado.")

        # 2. Verifica se há estoque suficiente
        if product.quantity < data.quantity:
            raise InsufficientStockError(
                f"Estoque insuficiente. Disponível: {product.quantity}, "
                f"solicitado: {data.quantity}."
            )

        # 3. Recalcula o total no servidor — nunca confiar no valor enviado pelo cliente
        calculated_total = round(
            data.unit_price * data.quantity * (1 - data.discount / 100), 2
        )

        now = datetime.now(timezone.utc)

        # 4. Grava snapshot do nome/SKU a partir do banco — não usar dados do cliente
        # 5. Cria a venda e decrementa o estoque atomicamente (um único commit no final)
        sale = Sale(
            id=str(uuid.uuid4()),
            product_id=data.product_id,
            product_name=product.name,
            product_sku=product.sku,
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

        # Decrementa o estoque — flush para que ambas as alterações fiquem na mesma transação
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
