# Contributing — TM-LFCCC-BACK

## Fluxo

1. Branch a partir de `develop` / `main`
2. `cd backend && pip install -e ".[dev]" && pre-commit install`
3. Mudanças mínimas; schemas Pydantic para I/O; authz no servidor
4. `ruff check . && ruff format . && mypy app && pytest -q`
5. PR com resumo + plano de teste

## Estilo

- Formatação/lint: **Ruff** (não Black)
- Tipagem: `mypy app` deve passar
- Testes: SQLite por padrão; Postgres via `DATABASE_URL` + `CI`/`TEST_DATABASE_URL` (ver [docs/setup.md](docs/setup.md))
- Sem secrets em commits (`.env` está no `.gitignore`)

## Migrations

```bash
cd backend
alembic revision --autogenerate -m "descricao"
alembic upgrade head
alembic check
```

Em deploy: migrate one-shot, depois scale da API ([docs/deploy.md](docs/deploy.md)).

## Contrato API

Após mudanças de schema/rotas:

```bash
python scripts/export-openapi.py
npx openapi-typescript openapi.json -o api-contract.d.ts
```

Ver [docs/api-contract.md](docs/api-contract.md).
