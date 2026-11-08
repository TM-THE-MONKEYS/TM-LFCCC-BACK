from datetime import UTC, datetime

from sqlalchemy import Select, asc, desc, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.product import Product

_SORT_MAP = {
    "name": Product.name,
    "sku": Product.sku,
    "price": Product.price,
    "quantity": Product.quantity,
    "created_at": Product.created_at,
    "updated_at": Product.updated_at,
}


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _apply_filters(
        self,
        stmt: Select,
        *,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        in_stock: bool | None = None,
    ) -> Select:
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Product.description.ilike(like),
                )
            )
        if category is not None:
            stmt = stmt.where(Product.category == category)
        if is_active is not None:
            stmt = stmt.where(Product.is_active.is_(is_active))
        if in_stock is True:
            stmt = stmt.where(Product.quantity > 0)
        elif in_stock is False:
            stmt = stmt.where(Product.quantity <= 0)
        return stmt

    def _apply_sort(self, stmt: Select, sort: str | None) -> Select:
        if not sort:
            return stmt.order_by(desc(Product.created_at))
        descending = sort.startswith("-")
        key = sort[1:] if descending else sort
        column = _SORT_MAP.get(key)
        if column is None:
            return stmt.order_by(desc(Product.created_at))
        return stmt.order_by(desc(column) if descending else asc(column))

    def list_filtered(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        q: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        in_stock: bool | None = None,
        sort: str | None = None,
    ) -> tuple[list[Product], int]:
        base = select(Product)
        base = self._apply_filters(
            base, q=q, category=category, is_active=is_active, in_stock=in_stock
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(self.db.scalar(count_stmt) or 0)
        stmt = self._apply_sort(base, sort).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all()), total

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        items, _ = self.list_filtered(skip=skip, limit=limit, is_active=True)
        return items

    def get_by_id(self, product_id: str) -> Product | None:
        return self.db.scalar(select(Product).where(Product.id == product_id))

    def get_by_sku(self, sku: str) -> Product | None:
        return self.db.scalar(select(Product).where(Product.sku == sku))

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return product

    def update(self, product: Product) -> Product:
        self.db.flush()
        return product

    def soft_delete(self, product: Product) -> Product:
        product.is_active = False
        self.db.flush()
        return product

    def delete(self, product: Product) -> None:
        """Hard delete — prefer soft_delete for API paths."""
        self.db.delete(product)
        self.db.flush()

    def decrement_stock_atomic(self, product_id: str, quantity: int) -> bool:
        """Conditionally decrement stock. Returns True if a row was updated."""
        result = self.db.execute(
            update(Product)
            .where(Product.id == product_id, Product.quantity >= quantity)
            .values(
                quantity=Product.quantity - quantity,
                updated_at=datetime.now(UTC),
            )
        )
        return bool(getattr(result, "rowcount", 0))

    def increment_stock_atomic(self, product_id: str, quantity: int) -> bool:
        """Unconditionally add stock (quantity must be positive)."""
        result = self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(
                quantity=Product.quantity + quantity,
                updated_at=datetime.now(UTC),
            )
        )
        return bool(getattr(result, "rowcount", 0))

    def update_stock(self, product_id: str, delta: int) -> Product | None:
        """Apply delta atomically. Negative deltas require sufficient stock."""
        if delta == 0:
            return self.get_by_id(product_id)
        if delta < 0:
            ok = self.decrement_stock_atomic(product_id, -delta)
        else:
            ok = self.increment_stock_atomic(product_id, delta)
        if not ok:
            return None
        self.db.flush()
        return self.get_by_id(product_id)
