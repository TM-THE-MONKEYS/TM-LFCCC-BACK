"""Pacote de dependências.

Re-exporta todas as dependências injetáveis para que os routers
importem sempre de um único lugar:

    from app.dependencies import get_db, get_current_user, optional_auth
"""

from app.dependencies.auth import get_current_user, get_db, optional_auth  # noqa: F401
