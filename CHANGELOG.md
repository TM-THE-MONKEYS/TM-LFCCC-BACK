# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) for the package
`vitrine-backend` (`backend/pyproject.toml`).

## [Unreleased]

### Added

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
