# Vitrine Backend

Backend FastAPI para o sistema **Vitrine** — gestão de bazar/loja beneficente (LFCCC).

> **Contrato TypeScript**: o arquivo `api-contract.d.ts` na raiz do projeto contém todos os tipos de request/response prontos para copiar no frontend.

---

## Stack

| Camada     | Tecnologia                                   |
| ---------- | -------------------------------------------- |
| Framework  | FastAPI (Python 3.12+)                       |
| ORM        | SQLAlchemy 2.0 (síncrono, declarative typed) |
| Migrations | Alembic                                      |
| Banco      | PostgreSQL 16 (produção) / SQLite (testes)   |
| Auth       | JWT (python-jose) + bcrypt (passlib)         |
| Testes     | pytest · 75 testes · SQLite in-memory        |
| Container  | Docker + docker-compose                      |

---

## Estrutura de pastas

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, middlewares, routers, probes
│   ├── seed.py                 # seed idempotente (admin + produtos + vendas + doações)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py       # agrega todos os routers da v1
│   │       ├── auth.py
│   │       ├── products.py
│   │       ├── sales.py
│   │       ├── donations.py
│   │       └── reports.py
│   ├── core/
│   │   ├── config.py           # pydantic-settings (.env)
│   │   ├── database.py         # engine, SessionLocal, Base
│   │   ├── security.py         # hash_password, create/decode JWT
│   │   └── enums.py            # ProductCategory, PaymentMethod, DonationDirection…
│   ├── dependencies/
│   │   └── auth.py             # get_db, get_current_user, optional_auth
│   ├── exceptions/
│   │   ├── domain.py           # AppException e subclasses (HTTP-agnósticas)
│   │   └── handlers.py         # mapeia exceções de domínio → respostas HTTP
│   ├── middleware/
│   │   └── correlation.py      # injeta X-Correlation-ID em cada request/response
│   ├── models/                 # SQLAlchemy ORM (User, Product, Sale, Donation)
│   ├── repositories/           # acesso ao banco (único ponto de query por entidade)
│   ├── schemas/                # Pydantic v2 · camelCase via alias_generator
│   └── services/               # regras de negócio (transações, validações, cálculos)
├── alembic/                    # migrations PostgreSQL
├── tests/                      # 75 testes de integração (pytest)
├── api-contract.d.ts           # tipos TypeScript do contrato de API
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── requirements.txt
```

**Fluxo de uma requisição:**

```
HTTP Request
  → router        (recebe, valida schema HTTP)
  → service       (regras de negócio, lança domain exceptions)
  → repository    (acesso ao banco, sem SQL direto nas camadas acima)
  → model         (SQLAlchemy ORM)
  → DB
```

---

## Setup rápido (Docker)

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env
# Edite .env e troque JWT_SECRET e ADMIN_PASSWORD

# 2. Subir API + PostgreSQL
# As migrations são aplicadas automaticamente no startup do container
docker compose up --build

# API disponível em: http://localhost:8000
# Swagger UI:        http://localhost:8000/docs
# ReDoc:             http://localhost:8000/redoc
```

---

## Variáveis de ambiente

| Variável                   | Padrão                                                  | Descrição                                          |
| -------------------------- | ------------------------------------------------------- | -------------------------------------------------- |
| `DATABASE_URL`             | `postgresql+psycopg2://vitrine:vitrine@db:5432/vitrine` | URL de conexão ao banco                            |
| `JWT_SECRET`               | —                                                       | **Obrigatório. Troque em produção.**               |
| `JWT_EXPIRE_MINUTES`       | `60`                                                    | Expiração do token JWT                             |
| `CORS_ORIGINS`             | `http://localhost:5173,...`                             | Origens permitidas (valores separados por vírgula) |
| `AUTH_REQUIRED`            | `false`                                                 | `true` → exige Bearer token nas rotas de escrita   |
| `UPLOAD_DIR`               | `uploads`                                               | Diretório local para imagens de produtos           |
| `PUBLIC_BASE_URL`          | `http://localhost:8000`                                 | Base URL para montar `imageUrl` nas respostas      |
| `ADMIN_EMAIL`              | `admin@vitrine.local`                                   | E-mail do usuário admin criado pelo seed           |
| `ADMIN_PASSWORD`           | `changeme`                                              | **Troque em produção.**                            |
| `CREATE_TABLES_ON_STARTUP` | `true`                                                  | `true` → cria tabelas via SQLAlchemy (útil SQLite) |

---

## Desenvolvimento local (sem Docker)

```powershell
# Windows (PowerShell) — dentro da pasta backend/
cd C:\Projetos\LFCC-BACK-DEVL\backend

# Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# Instalar dependências (se ainda não instalou)
pip install -r requirements.txt

# Configurar variáveis (.env já incluído com SQLite por padrão)
# DATABASE_URL=sqlite:///./vitrine.db
# CREATE_TABLES_ON_STARTUP=true

# Rodar seed (opcional — cria admin, produtos, vendas e doações de exemplo)
python -m app.seed

# Iniciar servidor com hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> Com `CREATE_TABLES_ON_STARTUP=true` e `DATABASE_URL` apontando para SQLite, o banco `vitrine.db` é criado automaticamente na primeira execução — sem necessidade de rodar `alembic upgrade head`.

---

## Migrations (PostgreSQL)

```bash
# Criar nova migration após alterar models
alembic revision --autogenerate -m "descrição"

# Aplicar todas as migrations pendentes
alembic upgrade head

# Reverter a última migration
alembic downgrade -1
```

---

## Testes

Os testes usam SQLite in-memory — **nenhum PostgreSQL necessário**.

```bash
# Todos os testes (75 testes)
.\.venv\Scripts\python.exe -m pytest tests/ -v

# Com relatório de cobertura
.\.venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=term-missing

# Arquivo específico
.\.venv\Scripts\python.exe -m pytest tests/test_products.py -v
```

---

## Endpoints da API

Prefixo canônico: `/api/v1` | Alias retrocompatível: `/api`

### Observabilidade

| Método | Rota      | Descrição                                     | Auth |
| ------ | --------- | --------------------------------------------- | ---- |
| GET    | `/health` | App em execução                               | —    |
| GET    | `/ready`  | App pronta para tráfego (verifica conexão DB) | —    |
| GET    | `/live`   | Processo vivo                                 | —    |

### Auth (`/auth`)

| Método | Rota             | Descrição                            | Auth         |
| ------ | ---------------- | ------------------------------------ | ------------ |
| POST   | `/auth/register` | Registrar novo usuário               | —            |
| POST   | `/auth/login`    | Login → `{ accessToken, tokenType }` | —            |
| GET    | `/auth/me`       | Dados do usuário atual               | Bearer token |

### Produtos (`/products`)

| Método | Rota                   | Descrição                              | Auth       |
| ------ | ---------------------- | -------------------------------------- | ---------- |
| GET    | `/products`            | Listar (`?skip=0&limit=100`)           | —          |
| GET    | `/products/{id}`       | Buscar por ID                          | —          |
| POST   | `/products`            | Criar                                  | Opcional\* |
| PUT    | `/products/{id}`       | Atualizar                              | Opcional\* |
| DELETE | `/products/{id}`       | Remover → 204 No Content               | Opcional\* |
| PATCH  | `/products/{id}/stock` | Ajustar estoque `{ "delta": int }`     | Opcional\* |
| POST   | `/products/{id}/image` | Upload de imagem (multipart/form-data) | Opcional\* |

### Vendas (`/sales`)

| Método | Rota          | Descrição                                     | Auth       |
| ------ | ------------- | --------------------------------------------- | ---------- |
| GET    | `/sales`      | Listar mais recentes primeiro (`?skip&limit`) | —          |
| GET    | `/sales/{id}` | Buscar por ID                                 | —          |
| POST   | `/sales`      | Registrar + baixa automática de estoque       | Opcional\* |

### Doações (`/donations`)

| Método | Rota              | Descrição                                     | Auth       |
| ------ | ----------------- | --------------------------------------------- | ---------- |
| GET    | `/donations`      | Listar mais recentes primeiro (`?skip&limit`) | —          |
| GET    | `/donations/{id}` | Buscar por ID                                 | —          |
| POST   | `/donations`      | Registrar                                     | Opcional\* |
| DELETE | `/donations/{id}` | Remover → 204 No Content                      | Opcional\* |

### Relatórios (`/reports`)

| Método | Rota       | Query params                                                                   |
| ------ | ---------- | ------------------------------------------------------------------------------ |
| GET    | `/reports` | `days` (1-365, default 30), `paymentMethods` (CSV), `donationCategories` (CSV) |

\*Opcional: sempre aceita requests sem token. Quando `AUTH_REQUIRED=true`, exige Bearer token.

---

## Contrato de integração com o frontend

### Envelope de resposta

Todos os endpoints retornam um envelope, **exceto `/reports`** (que retorna o objeto diretamente).

**Recurso único** (POST, GET /{id}, PUT, PATCH):

```json
{
  "success": true,
  "message": "Produto criado com sucesso.",
  "data": { "id": "...", "name": "..." }
}
```

**Lista** (GET sem ID):

```json
{
  "success": true,
  "message": "Produtos listados com sucesso.",
  "data": [{ "id": "..." }, { "id": "..." }]
}
```

O frontend deve desembrulhar `response.data.data` para obter o payload útil.

### Formato de erro (todos os 4xx/5xx)

```json
{
  "status": 422,
  "message": "Erro de validação dos dados enviados.",
  "timestamp": "2026-07-03T10:00:00.000Z",
  "details": [
    { "field": "email", "message": "value is not a valid email address" }
  ]
}
```

> `details` aparece apenas em erros 422. Para os demais, apenas `status`, `message` e `timestamp`.

### camelCase

Todos os campos de request e response usam **camelCase**:
`promoPrice`, `costPrice`, `paymentMethod`, `isActive`, `createdAt`, `accessToken`, `monetaryValue`, etc.

### Regras de validação

| Campo      | Regra                                        |
| ---------- | -------------------------------------------- |
| `email`    | Formato válido (ex: `user@dominio.com`)      |
| `password` | Mínimo 8 caracteres                          |
| `quantity` | Inteiro ≥ 0 (produto) / > 0 (venda)          |
| `price`    | Float ≥ 0                                    |
| `discount` | Float entre 0 e 100 (percentual)             |
| `delta`    | Stock patch: 409 se resultado ficar negativo |

### Comportamentos importantes

- **`POST /sales`**: não enviar `productName`, `productSku` nem `total` — todos calculados/preenchidos pelo servidor com snapshot do produto no banco.
- **`total` da venda**: sempre calculado pelo servidor como `unitPrice × quantity × (1 − discount/100)`.
- **Upload de imagem**: `POST /products/{id}/image` via `multipart/form-data`, campo `file`. Tipos aceitos: `image/jpeg`, `image/png`, `image/webp`. Tamanho máximo: 5 MB.
- **Rastreabilidade**: toda requisição recebe um header `X-Correlation-ID` na resposta (gerado automaticamente se não enviado pelo cliente).

---

## Seed

Popula o banco com dados de exemplo (1 admin, 5 produtos, 3 vendas, 4 doações). Idempotente — seguro rodar múltiplas vezes.

```bash
# Local
python -m app.seed

# Com Docker
docker compose exec api python -m app.seed
```

---

## Qualidade de código

```bash
# Lint
ruff check .

# Verificar formatação
black --check .

# Aplicar formatação
black .
```
