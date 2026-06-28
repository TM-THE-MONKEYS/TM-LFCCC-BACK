from datetime import datetime, timezone
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

# Converts any datetime → "2026-05-28T10:00:00.000Z" (ISO 8601, milliseconds, UTC Z)
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
    """Base model that accepts and serialises fields in camelCase.

    All request/response schemas must inherit from this class to satisfy
    the frontend contract (section 3.1 of the API spec).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


T = TypeVar("T")


class ListResponse(BaseModel, Generic[T]):
    """Envelope for list endpoints: { "data": [...] }"""

    data: List[T]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    status: int
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: str
