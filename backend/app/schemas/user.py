from app.schemas.common import CamelModel, DatetimeISO


class UserCreate(CamelModel):
    name: str
    email: str
    password: str


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
