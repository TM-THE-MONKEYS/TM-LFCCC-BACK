"""Pacote de exceções de domínio.

Todas as exceções da aplicação estão aqui.
Os services as lançam; os handlers em exceptions/handlers.py fazem o mapeamento para HTTP.
"""

from app.exceptions.domain import (  # noqa: F401
    AppException,
    ConflictError,
    ForbiddenError,
    InsufficientStockError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableError,
)
