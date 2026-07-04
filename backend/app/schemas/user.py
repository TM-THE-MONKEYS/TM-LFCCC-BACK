from typing import Annotated

from pydantic import AfterValidator, field_validator
from email_validator import EmailNotValidError, validate_email

from app.schemas.common import CamelModel, DatetimeISO


def _validate_email_format(v: str) -> str:
    """Validates email format without checking DNS deliverability."""
    try:
        validate_email(v, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return v


EmailField = Annotated[str, AfterValidator(_validate_email_format)]


class UserCreate(CamelModel):
    name: str
    email: EmailField
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres")
        return v


class UserResponse(CamelModel):
    id: str
    name: str
    email: str
    is_active: bool
    created_at: DatetimeISO


class LoginRequest(CamelModel):
    email: str
    password: str


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
