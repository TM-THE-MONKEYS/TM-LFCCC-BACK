from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        return self.db.query(Product).offset(skip).limit(limit).all()

    def get_by_id(self, product_id: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.flush()
        self.db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        self.db.delete(product)
        self.db.flush()

    def update_stock(self, product: Product, delta: int) -> Product:
        product.quantity = max(0, product.quantity + delta)
        self.db.flush()
        self.db.refresh(product)
        return product
