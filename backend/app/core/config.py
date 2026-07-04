from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Localiza o .env relativo a este arquivo (backend/.env) para que as configurações
# sejam carregadas corretamente independente de onde o uvicorn/pytest for executado.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # .../backend/
_DOTENV_PATH = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_DOTENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg2://vitrine:vitrine@localhost:5432/vitrine"
    JWT_SECRET: str = "dev-secret-troque-em-producao-minimo-32-chars"
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"
    AUTH_REQUIRED: bool = False
    UPLOAD_DIR: str = "uploads"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    ADMIN_EMAIL: str = "admin@vitrine.local"
    ADMIN_PASSWORD: str = "changeme"
    # Quando verdadeiro, cria as tabelas via SQLAlchemy ao iniciar (Base.metadata.create_all).
    # Útil para desenvolvimento local com SQLite, dispensando as migrations do Alembic.
    # Em produção, deixe como false e use `alembic upgrade head`.
    CREATE_TABLES_ON_STARTUP: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
