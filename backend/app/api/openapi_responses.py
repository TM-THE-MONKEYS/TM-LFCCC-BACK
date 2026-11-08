"""Shared OpenAPI response descriptions for consistent docs across routers."""

from __future__ import annotations

from typing import Any

OPENAPI_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Não autenticado"},
    403: {"description": "Sem permissão"},
    404: {"description": "Não encontrado"},
    409: {"description": "Conflito"},
    422: {"description": "Validação inválida"},
    429: {"description": "Rate limit excedido"},
}
