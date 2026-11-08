# Setup — desenvolvimento local

## Pré-requisitos

- Python 3.12+
- (Opcional) Docker + Docker Compose
- (Opcional) PostgreSQL 16

## Instalação

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.local.example .env   # SQLite local
pre-commit install            # hooks ruff
```

## Rodar a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Admin: python -m app.cli create-admin
# Seed (não production): python -m app.seed
```

Com `CREATE_TABLES_ON_STARTUP=true` e SQLite, as tabelas são criadas no startup (sem Alembic).

## Testes

**Padrão — SQLite in-memory** (sem Postgres):

```bash
cd backend
pytest -q
```

**Postgres** (CI ou smoke local):

```bash
# Exija um DB vazio/descartável
export CI=true   # ou PYTEST_USE_POSTGRES=true / TEST_DATABASE_URL=...
export DATABASE_URL=postgresql+psycopg2://vitrine:vitrine@localhost:5432/vitrine_test
alembic upgrade head
alembic check
pytest -q
```

`conftest` só usa `DATABASE_URL` Postgres quando `CI` / `PYTEST_USE_POSTGRES` está setado, ou quando `TEST_DATABASE_URL` é explícito — evita apontar testes no banco do `.env` por acidente.

## Qualidade

```bash
ruff check .
ruff format --check .
mypy app
pytest -q --cov=app --cov-fail-under=85
```

Black foi removido; formatação é **ruff format**.

## Docker (dev)

```bash
cd backend
cp .env.example .env
docker compose --profile migrate run --rm migrate   # uma vez, antes das réplicas
docker compose up --build
```

Detalhes de deploy e volume de uploads: [deploy.md](./deploy.md).
