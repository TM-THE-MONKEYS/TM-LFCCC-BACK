from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Localiza o .env relativo a este arquivo (backend/.env) para que as configurações
# sejam carregadas corretamente independente de onde o uvicorn/pytest for executado.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend/
_DOTENV_PATH = _BACKEND_DIR / ".env"

_WEAK_JWT_SECRETS = frozenset(
    {
        "dev-secret-troque-em-producao-minimo-32-chars",
        "troque-este-segredo-em-producao",
        "troque-este-segredo-por-um-valor-seguro-em-producao",
        "dev-secret-local",
        "changeme",
        "secret",
        "jwt-secret",
    }
)
_DEFAULT_ADMIN_PASSWORD = "changeme"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_DOTENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Literal["local", "test", "production"] = "local"
    DATABASE_URL: str = "postgresql+psycopg2://vitrine:vitrine@localhost:5432/vitrine"
    JWT_SECRET: SecretStr = SecretStr("dev-secret-troque-em-producao-minimo-32-chars")
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"
    APP_TIMEZONE: str = "America/Sao_Paulo"
    UPLOAD_DIR: str = "uploads"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    ADMIN_EMAIL: str = "admin@vitrine.local"
    ADMIN_PASSWORD: SecretStr = SecretStr(_DEFAULT_ADMIN_PASSWORD)
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    # Quando verdadeiro, cria as tabelas via SQLAlchemy ao iniciar (Base.metadata.create_all).
    # Útil para desenvolvimento local com SQLite, dispensando as migrations do Alembic.
    # Em produção, deixe como false e use `alembic upgrade head`.
    CREATE_TABLES_ON_STARTUP: bool = False

    # Pool SQLAlchemy (ignorado para SQLite)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def jwt_secret_value(self) -> str:
        return self.JWT_SECRET.get_secret_value()

    @property
    def admin_password_value(self) -> str:
        return self.ADMIN_PASSWORD.get_secret_value()

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_environment(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            return self

        errors: list[str] = []
        secret = self.JWT_SECRET.get_secret_value()
        if len(secret) < 32:
            errors.append("JWT_SECRET deve ter no mínimo 32 caracteres em produção.")
        if secret in _WEAK_JWT_SECRETS or secret.lower().startswith("dev-secret"):
            errors.append("JWT_SECRET é um valor conhecido/fraco — defina um segredo forte.")

        if self.ADMIN_PASSWORD.get_secret_value() == _DEFAULT_ADMIN_PASSWORD:
            errors.append("ADMIN_PASSWORD não pode ser o valor padrão 'changeme' em produção.")

        origins = self.cors_origins_list
        if not origins or "*" in origins:
            errors.append("CORS_ORIGINS não pode ser '*' ou vazio em produção.")

        if errors:
            raise ValueError("Configuração insegura para produção:\n- " + "\n- ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings factory — call get_settings.cache_clear() after env changes in tests."""
    return Settings()


def resolve_upload_dir(cfg: Settings | None = None) -> Path:
    """Absolute path for local uploads (single helper used by app factory + storage)."""
    settings = cfg or get_settings()
    configured = Path(settings.UPLOAD_DIR)
    return configured if configured.is_absolute() else _BACKEND_DIR / configured


# Backward-compatible module alias (resolved via cache on first access pattern).
settings = get_settings()
