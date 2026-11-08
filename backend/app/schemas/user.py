from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, Field, field_validator

from app.core.enums import UserRole
from app.core.security import assert_password_byte_limit
from app.schemas.common import CamelModel, DatetimeISO


def _normalize_email(v: str) -> str:
    """Lowercase + strip, then validate format (EmailStr-equivalent, no DNS).

    email-validator rejects special-use TLDs like `.local`; we allow those after a
    basic shape check so seed/CLI addresses (admin@vitrine.local) keep working.
    """
    normalized = v.strip().lower()
    try:
        validate_email(normalized, check_deliverability=False)
        return normalized
    except EmailNotValidError as exc:
        if "@" in normalized:
            local, _, domain = normalized.partition("@")
            if local and domain.endswith(".local") and "." in domain:
                return normalized
        raise ValueError(str(exc)) from exc


# Annotated email field — same role as pydantic EmailStr, with normalize + no DNS.
NormalizedEmail = Annotated[str, AfterValidator(_normalize_email)]


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("A senha deve ter no mínimo 8 caracteres")
    try:
        assert_password_byte_limit(v)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return v


class UserCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=200)
    role: UserRole = UserRole.operator

    @field_validator("password")
    @classmethod
    def password_constraints(cls, v: str) -> str:
        return _validate_password(v)


class UserResponse(CamelModel):
    id: str
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: DatetimeISO


class LoginRequest(CamelModel):
    # EmailStr-equivalent (format + normalize); special-use domains allowed for local/dev.
    email: NormalizedEmail = Field(examples=["admin@vitrine.local"])
    password: str = Field(examples=["senha-segura-exemplo"])

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, v: str) -> str:
        try:
            assert_password_byte_limit(v)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return v


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
