import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as api_v1_router
from app.core.config import settings, _BACKEND_DIR
from app.core.errors import register_exception_handlers

# Resolve upload directory relative to the backend/ folder so it works
# regardless of the working directory where uvicorn is invoked.
_UPLOAD_DIR = (
    Path(settings.UPLOAD_DIR)
    if Path(settings.UPLOAD_DIR).is_absolute()
    else _BACKEND_DIR / settings.UPLOAD_DIR
)
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    # CREATE_TABLES_ON_STARTUP=true → auto-create tables via SQLAlchemy
    # (useful for local dev with SQLite, skipping Alembic migrations)
    if settings.CREATE_TABLES_ON_STARTUP:
        from app.core.database import Base, engine
        import app.models  # ensure all models are registered on Base.metadata # noqa: F401
        Base.metadata.create_all(bind=engine)

    yield
    # ── Shutdown (nothing to clean up) ────────────────────────────────────────


app = FastAPI(
    title="Vitrine API",
    version="1.0.0",
    description="Backend da aplicação Vitrine — bazar beneficente LFCCC",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers (must be registered before routers) ────────────────────
register_exception_handlers(app)

# ── Static files (product image uploads) ─────────────────────────────────────
app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_DIR)), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
# Canonical prefix: /api/v1
app.include_router(api_v1_router, prefix="/api/v1")

# Alias: /api → /api/v1 (backward-compatible with frontend VITE_API_BASE_URL=.../api)
app.include_router(api_v1_router, prefix="/api", include_in_schema=False)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
    }
