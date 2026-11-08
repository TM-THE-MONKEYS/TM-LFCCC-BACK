from datetime import UTC, datetime
from typing import Annotated, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

# Converte qualquer datetime → "2026-05-28T10:00:00.000Z" (ISO 8601, milissegundos, UTC Z)
DatetimeISO = Annotated[
    datetime,
    PlainSerializer(
        lambda dt: (
            (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        ),
        return_type=str,
    ),
]


class CamelModel(BaseModel):
    """Modelo base que aceita e serializa campos em camelCase.

    Todos os schemas de request/response devem herdar desta classe
    para manter o contrato com o frontend.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


T = TypeVar("T")


class PaginationMeta(CamelModel):
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)


class StandardResponse[T](BaseModel):
    """Envelope de recurso único: { "success": true, "message": "...", "data": {...} }"""

    success: bool = True
    message: str
    data: T


class ListResponse[T](BaseModel):
    """Envelope de lista com meta de paginação."""

    success: bool = True
    message: str = "Listado com sucesso"
    data: list[T]
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: int
    message: str
    details: list[ErrorDetail] | None = None
    timestamp: str
