import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.core.config import settings, _BACKEND_DIR
from app.exceptions.handlers import register_exception_handlers
from app.middleware.correlation import CorrelationIdMiddleware

# Localiza o diretório de uploads relativo à pasta backend/ para funcionar
# independente de onde o uvicorn for executado.
_UPLOAD_DIR = (
    Path(settings.UPLOAD_DIR)
    if Path(settings.UPLOAD_DIR).is_absolute()
    else _BACKEND_DIR / settings.UPLOAD_DIR
)
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Inicialização ─────────────────────────────────────────────────────────
    # CREATE_TABLES_ON_STARTUP=true → cria as tabelas via SQLAlchemy
    # (útil para dev local com SQLite, dispensando as migrations do Alembic)
    if settings.CREATE_TABLES_ON_STARTUP:
        from app.core.database import Base, engine
        import app.models  # garante que todos os models estejam registrados no Base.metadata  # noqa: F401
        Base.metadata.create_all(bind=engine)

    yield
    # ── Encerramento (nenhum recurso para liberar) ───────────────────────────


app = FastAPI(
    title="Vitrine API",
    version="1.0.0",
    description="Backend da aplicação Vitrine — bazar beneficente LFCCC",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Handlers de exceção (registrar antes dos routers) ──────────────────────────
register_exception_handlers(app)

# ── Arquivos estáticos (imagens dos produtos) ─────────────────────────────────
app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_DIR)), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
# Prefixo canônico: /api/v1
app.include_router(api_v1_router, prefix="/api/v1")

# Alias /api → /api/v1 (retrocompatível com frontend usando VITE_API_BASE_URL=.../api)
app.include_router(api_v1_router, prefix="/api", include_in_schema=False)


# ── Observabilidade ─────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@app.get("/health", tags=["Observability"])
def health_check():
    """General health check — confirms the app is running."""
    return {"status": "healthy", "timestamp": _now_iso()}


@app.get("/ready", tags=["Observability"])
def readiness_check():
    """Readiness probe — confirms the app is ready to serve traffic."""
    from app.core.database import engine
    try:
        with engine.connect():
            pass
        return {"status": "ready", "timestamp": _now_iso()}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not reachable.")


@app.get("/live", tags=["Observability"])
def liveness_check():
    """Liveness probe — confirms the process is alive."""
    return {"status": "alive", "timestamp": _now_iso()}
