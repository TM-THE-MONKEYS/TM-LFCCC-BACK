# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) for the package
`vitrine-backend` (`backend/pyproject.toml`).

## [Unreleased]

### Added

- Request access logging middleware (`http_request` / `slow_request`) with correlation_id, duration, query **keys** only (no values/secrets)
- `Permissions-Policy` + `Cache-Control: no-store` on API responses (uploads excluded from no-store)
- Auth login OpenAPI summaries + `429` docs; `Retry-After: 60` on rate limit
- Shared `parse_iso_dt` and `OPENAPI_ERRORS` helpers for consistent API docs
- Production settings reject `CREATE_TABLES_ON_STARTUP=true` and SQLite `DATABASE_URL`
- Tests: cancel authz (operator 403), soft-delete cannot sell, `isActive=false` listing, correlation ID, readiness

### Changed

- `/ready` executes `SELECT 1` (not connect-only); Docker HEALTHCHECK uses `/ready`
- Auth/Users routers: OpenAPI response maps aligned with other resources
- User listing count moved into `UserRepository.count()`

### Added (earlier)

- FASE 6 ops: multi-stage Dockerfile (non-root, HEALTHCHECK, gunicorn + UvicornWorker)
- Compose profile `migrate` (Alembic one-shot) + named volume `uploads_data`
- CI: ruff check/format, mypy, pytest+cov fail-under, Postgres job (alembic upgrade/check + pytest), pip-audit
- pre-commit (ruff)
- `/health` includes package `version` from `importlib.metadata`
- `scripts/export-openapi.py` + docs for `openapi-typescript`
- CONTRIBUTING / CHANGELOG / docs (setup, deploy, api-contract)

### Changed

- Seed blocked in production; sales seed uses `SaleService`
- Root README slimmed; detail moved under `docs/`
- Removed obsolete Compose `version:` key and Black leftovers

### Security

- Secrets only via env; production seed disabled
