from datetime import datetime, timezone
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

# Converte qualquer datetime → "2026-05-28T10:00:00.000Z" (ISO 8601, milissegundos, UTC Z)
DatetimeISO = Annotated[
    datetime,
    PlainSerializer(
        lambda dt: (
            dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        )
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
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
    )


T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Envelope de recurso único: { "success": true, "message": "...", "data": {...} }"""

    success: bool = True
    message: str
    data: T


class ListResponse(BaseModel, Generic[T]):
    """Envelope de lista: { "success": true, "message": "...", "data": [...] }"""

    success: bool = True
    message: str = "Listado com sucesso"
    data: List[T]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: int
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: str
