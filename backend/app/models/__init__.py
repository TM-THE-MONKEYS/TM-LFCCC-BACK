# Importa todos os models para que o SQLAlchemy/Alembic os descubra via Base.metadata
from app.models.donation import Donation  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.sale import Sale  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["User", "Product", "Sale", "Donation"]
