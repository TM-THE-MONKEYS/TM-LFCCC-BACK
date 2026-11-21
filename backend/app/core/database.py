import logging
from collections.abc import Callable, Generator

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings

_logger = logging.getLogger("vitrine")
_AFTER_COMMIT_KEY = "after_commit_callbacks"
_AFTER_ROLLBACK_KEY = "after_rollback_callbacks"

# Convenção de nomes para constraints/índices (Alembic + create_all)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _engine_kwargs(cfg: Settings) -> dict:
    is_sqlite = cfg.DATABASE_URL.startswith("sqlite")
    kwargs: dict = {"pool_pre_ping": not is_sqlite}
    if not is_sqlite:
        kwargs["pool_size"] = cfg.DB_POOL_SIZE
        kwargs["max_overflow"] = cfg.DB_MAX_OVERFLOW
        kwargs["pool_recycle"] = cfg.DB_POOL_RECYCLE
    return kwargs


def create_db_engine(cfg: Settings | None = None) -> Engine:
    settings = cfg or get_settings()
    return create_engine(settings.DATABASE_URL, **_engine_kwargs(settings))


# Module-level engine/session for CLI, Alembic consumers and default app wiring.
# Tests override get_db and do not rely on this engine for request isolation.
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def on_commit(session: Session, callback: Callable[[], None]) -> None:
    """Run callback once after the session's next commit; dropped if it rolls back.

    For side effects outside the DB (e.g. deleting files) that must not happen
    unless the transaction that justifies them is durable.
    """
    session.info.setdefault(_AFTER_COMMIT_KEY, []).append(callback)


def on_rollback(session: Session, callback: Callable[[], None]) -> None:
    """Run callback once if the session's current transaction rolls back."""
    session.info.setdefault(_AFTER_ROLLBACK_KEY, []).append(callback)


def _run_callbacks(callbacks: list[Callable[[], None]], phase: str) -> None:
    for callback in callbacks:
        try:
            callback()
        except Exception:
            _logger.exception("db_%s_callback_failed callback=%s", phase, callback)


@event.listens_for(Session, "after_commit")
def _after_commit(session: Session) -> None:
    session.info.pop(_AFTER_ROLLBACK_KEY, None)
    _run_callbacks(session.info.pop(_AFTER_COMMIT_KEY, []), "commit")


@event.listens_for(Session, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop(_AFTER_COMMIT_KEY, None)
    _run_callbacks(session.info.pop(_AFTER_ROLLBACK_KEY, []), "rollback")


def get_db() -> Generator[Session, None, None]:
    """Sessão por request (UoW): commit no sucesso, rollback em exceção.

    Services/repositórios apenas fazem flush — o commit fica aqui.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
