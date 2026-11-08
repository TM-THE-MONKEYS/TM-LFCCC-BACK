# Vitrine Backend

API FastAPI do bazar beneficente LFCCC. Detalhes de setup/deploy/contrato: pasta [`docs/`](../docs/) na raiz do repo.

## Comandos úteis

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
pytest -q
ruff check . && ruff format --check . && mypy app
python -m app.cli create-admin
python -m app.seed          # bloqueado se ENVIRONMENT=production
python scripts/export-openapi.py
```

## Docker

```bash
cp .env.example .env
docker compose --profile migrate run --rm migrate
docker compose up --build
```

API sobe com **gunicorn** + `UvicornWorker`. Migrations ficam no profile `migrate` (não no CMD da API).

## Layout

```
app/          # factory, api, core, models, services, repositories, schemas
alembic/      # migrations Postgres
tests/        # pytest (SQLite default)
scripts/      # export-openapi.py
api-contract.d.ts
```

Prefixo API: `/api/v1`. Probes: `/health` (liveness-ish), `/ready` (`SELECT 1` no DB), `/live`.
Docker HEALTHCHECK usa `/ready`.

Contrato front: [FRONTEND_INTEGRATION.md](../FRONTEND_INTEGRATION.md).
