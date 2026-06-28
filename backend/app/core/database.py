from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite does not support pool_size / max_overflow (uses StaticPool/NullPool)
_engine_kwargs: dict = {"pool_pre_ping": not _is_sqlite}
if not _is_sqlite:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session.

    This is the single canonical definition — re-exported by app.api.deps
    so that all routers and tests reference the same function object
    (required for FastAPI dependency_overrides to work correctly).
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
