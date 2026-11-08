import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.money import quantize_money
from app.exceptions import ConflictError, InsufficientStockError, NotFoundError, UnprocessableError
from app.models.product import Product
from app.models.sale import Sale
from app.repositories.product_repository import ProductRepository
from app.repositories.sale_repository import SaleRepository
from app.schemas.sale import SaleInput


class SaleService:
    def __init__(self, db: Session) -> None:
        self._sale_repo = SaleRepository(db)
        self._product_repo = ProductRepository(db)
        self._db = db

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
        return self._sale_repo.list_filtered(
            skip=skip,
            limit=limit,
            from_dt=from_dt,
            to_dt=to_dt,
            payment_method=payment_method,
            product_id=product_id,
            include_cancelled=include_cancelled,
        )

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Sale]:
        items, _ = self.list_filtered(skip=skip, limit=limit)
        return items

    def get_by_id(self, sale_id: str) -> Sale:
        sale = self._sale_repo.get_by_id(sale_id)
        if sale is None:
            raise NotFoundError(f"Venda com id '{sale_id}' não encontrada.")
        return sale

    @staticmethod
    def _resolve_unit_price(product: Product, data: SaleInput, actor_role: str) -> Decimal:
        # unit_price_override is honored only for admin.
        if data.unit_price_override is not None and actor_role == UserRole.admin.value:
            return quantize_money(data.unit_price_override)
        if product.promo_price is not None:
            return quantize_money(product.promo_price)
        return quantize_money(product.price)

    @staticmethod
    def _validate_variant(product: Product, data: SaleInput) -> None:
        if data.size is not None:
            sizes = product.sizes or []
            if data.size not in sizes:
                raise UnprocessableError(f"Tamanho '{data.size}' não disponível para este produto.")
        if data.color is not None:
            colors = product.colors or []
            if data.color not in colors:
                raise UnprocessableError(f"Cor '{data.color}' não disponível para este produto.")

    @staticmethod
    def calculate_total(unit_price: Decimal, quantity: int, discount: Decimal) -> Decimal:
        """total = unit × qty × (1 − discount/100), quantizado ao centavo."""
        unit = quantize_money(unit_price)
        disc = quantize_money(discount)
        factor = (Decimal("100") - disc) / Decimal("100")
        return quantize_money(unit * Decimal(quantity) * factor)

    def create(self, data: SaleInput, *, actor_role: str = UserRole.operator.value) -> Sale:
        product = self._product_repo.get_by_id(data.product_id)
        if product is None:
            raise NotFoundError(f"Produto com id '{data.product_id}' não encontrado.")

        if not product.is_active:
            raise ConflictError("Produto inativo não pode ser vendido.")

        self._validate_variant(product, data)

        product_id = product.id
        available = product.quantity
        requested = data.quantity
        if available < requested:
            raise InsufficientStockError(
                f"Estoque insuficiente. Disponível: {available}, solicitado: {requested}."
            )

        unit_price = self._resolve_unit_price(product, data, actor_role)
        calculated_total = self.calculate_total(unit_price, data.quantity, data.discount)
        now = datetime.now(UTC)

        sale = Sale(
            id=str(uuid.uuid4()),
            product_id=data.product_id,
            product_name=product.name,
            product_sku=product.sku,
            quantity=data.quantity,
            unit_price=unit_price,
            discount=quantize_money(data.discount),
            total=calculated_total,
            customer_name=data.customer_name,
            payment_method=data.payment_method,
            size=data.size,
            color=data.color,
            notes=data.notes,
            cancelled_at=None,
            created_at=now,
        )
        self._sale_repo.create(sale)

        # Atomic guard against concurrent sales racing the last units
        if not self._product_repo.decrement_stock_atomic(product_id, requested):
            raise InsufficientStockError(
                f"Estoque insuficiente. Disponível: 0, solicitado: {requested}."
            )

        return sale

    def cancel(self, sale_id: str) -> Sale:
        """Cancel/refund a sale and restore stock (admin)."""
        sale = self.get_by_id(sale_id)
        if sale.cancelled_at is not None:
            raise ConflictError("Venda já cancelada.")

        sale.cancelled_at = datetime.now(UTC)
        self._sale_repo.update(sale)

        if sale.product_id and sale.quantity > 0:
            self._product_repo.increment_stock_atomic(sale.product_id, sale.quantity)

        return sale
