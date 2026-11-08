# Deploy e operações

## Imagem Docker

- Multi-stage (`builder` → `runtime`), usuário **non-root** (`app`, uid 10001)
- Processo: `gunicorn -k uvicorn.workers.UvicornWorker` (proxy headers / forwarded IPs)
- `HEALTHCHECK` em `GET /health`
- Secrets **somente via env** (nunca bake no image)

Build:

```bash
cd backend
docker compose build
```

## Migrations (separadas do start da API)

**Não** rode `alembic upgrade` no CMD de várias réplicas — risco de corrida.

Compose profile `migrate` (one-shot):

```bash
docker compose --profile migrate run --rm migrate
docker compose up -d api
```

Em release pipelines: job de migrate → só então scale do `api`.

## Volume de uploads

Compose monta o volume nomeado `uploads_data` em `/app/uploads` (persistente entre recreates).

Variáveis:

- `UPLOAD_DIR` — path no container (padrão `/app/uploads`)
- `PUBLIC_BASE_URL` — base usada para montar `imageUrl` nas respostas

## Servindo `/uploads` (proxy / CDN)

Em produção, **prefira não** depender do `StaticFiles` do FastAPI para tráfego de mídia:

1. Monte o mesmo volume/object storage no reverse proxy (nginx, Caddy, Traefik) ou CDN.
2. Sirva `https://cdn.exemplo.com/uploads/...` (ou path `/uploads` no proxy) com cache imutável.
3. Ajuste `PUBLIC_BASE_URL` para a origem pública das imagens (CDN ou API).

O mount `/uploads` na app continua útil em local/dev e como fallback.

## Seed

```bash
docker compose exec api python -m app.seed
```

`python -m app.seed` **aborta em `ENVIRONMENT=production`**. Use `python -m app.cli create-admin` para o primeiro admin.

## Health

`GET /health` → `{ "status": "healthy", "version": "<pyproject>", "timestamp": "..." }`  
Também: `/ready` (DB), `/live`.

## Checklist rápido produção

- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` forte (≥32, não default)
- [ ] `ADMIN_PASSWORD` não-default
- [ ] `CORS_ORIGINS` explícito (sem `*`)
- [ ] Migrate one-shot antes do scale
- [ ] Volume/CDN para uploads
- [ ] Proxy com `--forwarded-allow-ips` / headers já cobertos pelo gunicorn
