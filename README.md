# TM-LFCCC-BACK — Vitrine API

Backend FastAPI do **Vitrine** (bazar beneficente LFCCC): produtos, vendas, doações e relatórios.

## Quick start

```bash
cd backend
cp .env.example .env          # defina JWT_SECRET e ADMIN_PASSWORD
docker compose --profile migrate run --rm migrate
docker compose up --build -d
docker compose exec api python -m app.seed   # só local/dev — bloqueado em production
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Local sem Docker (SQLite): ver [docs/setup.md](docs/setup.md).

## Docs

| Doc | Conteúdo |
|-----|----------|
| [docs/setup.md](docs/setup.md) | Dev local, testes SQLite/Postgres, pre-commit |
| [docs/deploy.md](docs/deploy.md) | Docker, migrations, uploads via proxy/CDN |
| [docs/api-contract.md](docs/api-contract.md) | OpenAPI export + `openapi-typescript` |
| [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) | Contrato HTTP para o front |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Lint, testes, PRs |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de mudanças |

## Stack

FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 (prod) / SQLite (dev/test) · JWT · Docker · pytest/ruff/mypy

## Licença

Projeto interno LFCCC.
