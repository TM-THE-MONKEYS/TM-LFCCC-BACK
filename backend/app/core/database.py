from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite não suporta pool_size / max_overflow (usa StaticPool/NullPool)
_engine_kwargs: dict = {"pool_pre_ping": not _is_sqlite}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependência do FastAPI que fornece uma sessão de banco de dados.

    Definição única e canônica — re-exportada por app.dependencies
    para que todos os routers e testes referenciem o mesmo objeto de função
    (necessário para que dependency_overrides funcione corretamente).
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
