from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings, resolve_upload_dir
from app.core.logging import configure_logging, logger
from app.exceptions.handlers import register_exception_handlers
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

_PACKAGE_NAME = "vitrine-backend"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _app_version() -> str:
    """Package version from installed metadata (pyproject); fallback for editable/dev)."""
    try:
        return pkg_version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return "0.0.0-dev"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — importing this module should stay light; prefer create_app()."""
    cfg = settings or get_settings()
    configure_logging()
    upload_dir = resolve_upload_dir(cfg)
    app_version = _app_version()

    @asynccontextmanager
    async def lifespan(_fastapi_app: FastAPI):
        upload_dir.mkdir(parents=True, exist_ok=True)
        if cfg.CREATE_TABLES_ON_STARTUP:
            import app.models  # noqa: F401 — register metadata
            from app.core.database import Base, engine

            Base.metadata.create_all(bind=engine)
        yield
        from app.core.database import engine

        engine.dispose()

    application = FastAPI(
        title="Vitrine API",
        version=app_version,
        description="Backend da aplicação Vitrine — bazar beneficente LFCCC",
        docs_url=None if cfg.is_production else "/docs",
        redoc_url=None if cfg.is_production else "/redoc",
        openapi_url=None if cfg.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (último adicionado = primeiro a executar no request).
    # Correlation outer → logging sees correlation_id on the ContextVar.
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(GZipMiddleware, minimum_size=500)

    if cfg.is_production:
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=cfg.allowed_hosts_list or ["localhost"],
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Correlation-ID"],
    )

    register_exception_handlers(application)

    # Ensure mount target exists even before lifespan (StaticFiles requires it)
    upload_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")
    application.include_router(api_v1_router, prefix="/api/v1")

    @application.get("/health", tags=["Observability"], operation_id="health_check")
    def health_check():
        """General health check — confirms the app is running."""
        return {"status": "healthy", "version": app_version, "timestamp": _now_iso()}

    @application.get("/ready", tags=["Observability"], operation_id="readiness_check")
    def readiness_check():
        """Readiness probe — confirms DB accepts a lightweight query."""
        from fastapi import HTTPException
        from sqlalchemy import text

        from app.core.database import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "ready", "timestamp": _now_iso()}
        except Exception:
            logger.exception("readiness_check_failed")
            raise HTTPException(status_code=503, detail="Database not reachable.")

    @application.get("/live", tags=["Observability"], operation_id="liveness_check")
    def liveness_check():
        """Liveness probe — confirms the process is alive."""
        return {"status": "alive", "timestamp": _now_iso()}

    return application


# ASGI entrypoint for uvicorn `app.main:app`
app = create_app()
