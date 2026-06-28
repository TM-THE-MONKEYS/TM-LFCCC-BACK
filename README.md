# LFCC-BACK-DEVL

Backend **Vitrine** — API REST para gestão de bazar/loja beneficente (LFCCC).

## Visão geral

Sistema de gestão de produtos, vendas, doações e relatórios para bazares beneficentes. Arquitetura em camadas (router → service → repository) com contrato JSON em **camelCase** para integração com frontend.

| Domínio | Funcionalidades |
|---------|-----------------|
| **Produtos** | CRUD, ajuste de estoque, upload de imagens |
| **Vendas** | Registro com decremento automático de estoque e cálculo server-side do total |
| **Doações** | Controle de doações recebidas/doadas (roupas, dinheiro, alimentos, etc.) |
| **Relatórios** | Receita, ticket médio, top produtos, breakdown por pagamento, gráfico diário |
| **Auth** | JWT (login/registro), auth opcional ou obrigatória nas rotas de escrita |

## Stack

| Camada | Tecnologia |
|--------|------------|
| Framework | FastAPI (Python 3.12+) |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Banco | PostgreSQL 16 (prod) / SQLite (dev/testes) |
| Auth | PyJWT + bcrypt |
| Testes | pytest + TestClient |
| Container | Docker + docker-compose |

## Estrutura do repositório

```
LFCC-BACK-DEVL/
├── backend/                  # Aplicação FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/             # config, database, security, errors
│   │   ├── api/v1/routers/   # auth, products, sales, donations, reports
│   │   ├── schemas/          # Pydantic v2 (camelCase)
│   │   ├── models/           # SQLAlchemy ORM
│   │   ├── repositories/
│   │   └── services/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── docker-compose.yml
├── FRONTEND_INTEGRATION.md   # Contrato completo da API para o frontend
└── README.md
```

## Início rápido (Docker)

```bash
cd backend
cp .env.example .env   # edite JWT_SECRET e credenciais
docker compose up --build -d
docker compose exec api python -m app.seed
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Desenvolvimento local (SQLite)

```bash
cd backend
cp .env.local.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
python -m app.seed
pytest
```

## API

**Prefixo:** `/api/v1` (alias `/api` também disponível)

Principais endpoints:

| Recurso | Rotas |
|---------|-------|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Produtos | CRUD + `PATCH /products/{id}/stock` + `POST /products/{id}/image` |
| Vendas | `GET /sales`, `POST /sales` |
| Doações | `GET /donations`, `POST /donations`, `DELETE /donations/{id}` |
| Relatórios | `GET /reports?days=30&paymentMethods=...` |

Consulte [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) para o contrato completo.

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | URL de conexão PostgreSQL/SQLite |
| `JWT_SECRET` | Chave de assinatura JWT (**obrigatório trocar em produção**) |
| `JWT_EXPIRE_MINUTES` | TTL do token (padrão: 60) |
| `CORS_ORIGINS` | Origens permitidas (CSV) |
| `AUTH_REQUIRED` | `true` exige Bearer token nas rotas de escrita |
| `UPLOAD_DIR` | Diretório de uploads |
| `PUBLIC_BASE_URL` | Base URL para URLs de imagens |
| `CREATE_TABLES_ON_STARTUP` | `true` para SQLite local (sem Alembic) |

## Testes

~60 testes de integração cobrindo auth, produtos, vendas, doações e relatórios.

```bash
cd backend
pytest
pytest --cov=app --cov-report=term-missing
```

## Documentação adicional

- [backend/README.md](./backend/README.md) — setup detalhado e referência da API
- [FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md) — guia de integração frontend

## Licença

Projeto interno LFCCC.
