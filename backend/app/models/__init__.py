# Import all models so SQLAlchemy/Alembic can discover them via Base.metadata
from app.models.donation import Donation  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.sale import Sale  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["User", "Product", "Sale", "Donation"]
