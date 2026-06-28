# Vitrine Backend

Backend FastAPI para o sistema **Vitrine** — gestão de bazar/loja beneficente (LFCCC).

## Stack

| Camada     | Tecnologia                                   |
| ---------- | -------------------------------------------- |
| Framework  | FastAPI (Python 3.12+)                       |
| ORM        | SQLAlchemy 2.0 (síncrono, declarative typed) |
| Migrations | Alembic                                      |
| Banco      | PostgreSQL 16                                |
| Auth       | JWT (python-jose) + bcrypt (passlib)         |
| Testes     | pytest + httpx (SQLite in-memory)            |
| Container  | Docker + docker-compose                      |

---

## Estrutura (REST em camadas)

```
app/
├── main.py                  # FastAPI app, CORS, exception handlers, StaticFiles
├── core/                    # config, database, security, errors, enums
├── api/
│   ├── deps.py              # get_db, get_current_user, optional_auth
│   └── v1/
│       ├── router.py        # agrega todos os routers
│       └── routers/         # products, sales, donations, reports, auth
├── schemas/                 # Pydantic v2 (camelCase via alias_generator)
├── models/                  # SQLAlchemy ORM
├── repositories/            # acesso a dados (único ponto de query)
├── services/                # regras de negócio (transações, cálculos)
└── seed.py                  # seed idempotente
```

Fluxo de uma requisição:

```
HTTP Request → router (validação HTTP) → service (regras de negócio) → repository (dados) → model → DB
```

---

## Setup rápido (Docker)

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env

# 2. Subir API + PostgreSQL (migrations aplicadas automaticamente no startup)
docker compose up --build

# API disponível em: http://localhost:8000
# Swagger UI:        http://localhost:8000/docs
```

---

## Variáveis de ambiente

| Variável             | Padrão                                                  | Descrição                              |
| -------------------- | ------------------------------------------------------- | -------------------------------------- |
| `DATABASE_URL`       | `postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine` | URL de conexão                         |
| `JWT_SECRET`         | —                                                       | **Troque em produção**                 |
| `JWT_EXPIRE_MINUTES` | `60`                                                    | Expiração do token                     |
| `CORS_ORIGINS`       | `http://localhost:5173,...`                             | Origens permitidas (CSV)               |
| `AUTH_REQUIRED`      | `false`                                                 | `true` exige token em rotas de escrita |
| `UPLOAD_DIR`         | `uploads`                                               | Diretório de imagens                   |
| `PUBLIC_BASE_URL`    | `http://localhost:8000`                                 | Base URL para imageUrl                 |
| `ADMIN_EMAIL`        | `admin@vitrine.local`                                   | E-mail do admin do seed                |
| `ADMIN_PASSWORD`     | `changeme`                                              | **Troque em produção**                 |

---

## Desenvolvimento local (sem Docker)

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar banco local (PostgreSQL rodando em localhost:5432)
cp .env.example .env
# Edite .env com suas credenciais

# Aplicar migrations
alembic upgrade head

# Rodar seed (opcional, idempotente)
python -m app.seed

# Iniciar servidor de desenvolvimento
uvicorn app.main:app --reload --port 8000
```

---

## Migrations

```bash
# Criar nova migration após alterar models
alembic revision --autogenerate -m "descrição da mudança"

# Aplicar migrations pendentes
alembic upgrade head

# Reverter última migration
alembic downgrade -1
```

---

## Testes

```bash
# Executar todos os testes (SQLite in-memory, sem PostgreSQL necessário)
pytest

# Com cobertura
pytest --cov=app --cov-report=term-missing

# Arquivo específico
pytest tests/test_sales.py -v
```

---

## Endpoints da API

Prefixo canônico: `/api/v1` | Alias de compatibilidade: `/api`

### Produtos (`/products`)

| Método | Rota                   | Descrição                            | Auth       |
| ------ | ---------------------- | ------------------------------------ | ---------- |
| GET    | `/products`            | Listar todos                         | —          |
| GET    | `/products/{id}`       | Buscar por ID                        | —          |
| POST   | `/products`            | Criar                                | Opcional\* |
| PUT    | `/products/{id}`       | Atualizar                            | Opcional\* |
| DELETE | `/products/{id}`       | Remover                              | Opcional\* |
| PATCH  | `/products/{id}/stock` | Ajustar estoque (`{ "delta": int }`) | Opcional\* |
| POST   | `/products/{id}/image` | Upload de imagem (multipart)         | Opcional\* |

### Vendas (`/sales`)

| Método | Rota     | Descrição                               | Auth       |
| ------ | -------- | --------------------------------------- | ---------- |
| GET    | `/sales` | Listar (mais recentes primeiro)         | —          |
| POST   | `/sales` | Registrar + baixa automática de estoque | Opcional\* |

### Doações (`/donations`)

| Método | Rota              | Descrição                       | Auth       |
| ------ | ----------------- | ------------------------------- | ---------- |
| GET    | `/donations`      | Listar (mais recentes primeiro) | —          |
| POST   | `/donations`      | Registrar                       | Opcional\* |
| DELETE | `/donations/{id}` | Remover                         | Opcional\* |

### Relatórios (`/reports`)

| Método | Rota       | Query params                                                                 |
| ------ | ---------- | ---------------------------------------------------------------------------- |
| GET    | `/reports` | `days` (int, default 30), `paymentMethods` (csv), `donationCategories` (csv) |

### Auth (`/auth`)

| Método | Rota             | Descrição                              |
| ------ | ---------------- | -------------------------------------- |
| POST   | `/auth/register` | Registrar usuário                      |
| POST   | `/auth/login`    | Login → `{ access_token, token_type }` |
| GET    | `/auth/me`       | Usuário atual (Bearer token)           |

\*Opcional: sempre aceita requests sem token. Quando `AUTH_REQUIRED=true`, exige Bearer token.

---

## Contratos de integração (frontend)

### camelCase

Todos os campos de request e response usam camelCase (`promoPrice`, `costPrice`, `paymentMethod`, etc.)

### Envelope de listagem

```json
{ "data": [ ...itens... ] }
```

### Recurso único / create / update

Retorna o objeto diretamente (sem envelope).

### DELETE → 204 No Content

### Formato de erro (todos os 4xx/5xx)

```json
{
  "status": 400,
  "message": "Descrição do erro",
  "details": [{ "field": "sku", "message": "Campo obrigatório" }],
  "timestamp": "2026-06-12T10:00:00.000Z"
}
```

### Login

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

---

## Ajustes necessários no frontend

1. **`donationServiceApi.ts`** — Adicionar os campos `direction`, `recipientName` e `productType` no payload de criação de doação.

2. **`saleServiceApi.ts`** — **Remover** a chamada extra `PATCH /products/{id}/stock` após criar a venda. O backend já faz a baixa de estoque automaticamente na mesma transação do `POST /sales` (baixa dupla se mantida).

3. **`productServiceApi.ts`** — Corrigir o typo `apiConfig.enableOffallback` → `apiConfig.enableOfflineFallback`.

4. **Tela de login** — Se `AUTH_REQUIRED=true`, implementar tela de login chamando `POST /auth/login` e armazenar o token com `apiClient.setAuthToken(token)`.

---

## Seed

Popula o banco com dados de exemplo (5 produtos, 3 vendas, 4 doações, 1 admin). É seguro rodar múltiplas vezes:

```bash
python -m app.seed
# ou com Docker:
docker compose exec api python -m app.seed
```

---

## Qualidade de código

```bash
# Lint
ruff check .

# Formatação
black --check .

# Aplicar formatação
black .
```
