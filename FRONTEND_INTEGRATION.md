# Guia de Integração Frontend ↔ Backend — Vitrine

> **Para o agente / engenheiro de frontend:** contrato da API REST após **Fase 5** (API redesign + errors/logging + app factory).
> Tipos TypeScript espelhados em `backend/api-contract.d.ts` — mantenha os dois alinhados.
>
> **Breaking (Fase 5):** listas com `meta`; `PUT /products` → `PATCH`; soft-delete; `GET /reports` no envelope `StandardResponse`; IDs de path devem ser UUID (senão 422); stock do operator sem `costPrice`.

---

## 1. Configuração Base

```
Base URL local:    http://localhost:8000
Prefixo da API:    /api/v1          ← único (alias /api REMOVIDO)
Axios/fetch base:  http://localhost:8000/api/v1
Swagger UI:        http://localhost:8000/docs  (desabilitado em production)
```

- Todo body JSON: `Content-Type: application/json`
- Upload de imagem: `multipart/form-data` (campo `file`)
- Health probes ficam na **raiz** do host (não sob `/api/v1`): `/health`, `/ready`, `/live`
- Respostas incluem header `X-Correlation-ID` (eco validado ou UUID gerado)

---

## 2. camelCase obrigatório

O backend usa `alias_generator=to_camel` em todos os schemas de domínio.

| Errado (snake_case)   | Correto (camelCase)   | Onde                         |
| --------------------- | --------------------- | ---------------------------- |
| `access_token`        | `accessToken`         | Login                        |
| `token_type`          | `tokenType`           | Login                        |
| `product_id`          | `productId`           | Venda                        |
| `cost_price`          | `costPrice`           | Produto (admin)              |
| `unit_price_override` | `unitPriceOverride`   | Venda (só admin)             |
| `promo_price`         | `promoPrice`          | Produto                      |
| `payment_method`      | `paymentMethod`       | Venda / reports query        |
| `cancelled_at`        | `cancelledAt`         | Venda                        |
| `is_active`           | `isActive`            | Produto / filtros            |

---

## 3. Datas

Strings ISO 8601 UTC com milissegundos:

```
"2026-06-12T10:30:00.000Z"
```

Filtros `from` / `to` aceitam `YYYY-MM-DD` ou ISO 8601.  
Relatórios agregam por **calendário local** (`APP_TIMEZONE`, default `America/Sao_Paulo`) — ver §6.4.

---

## 4. Formato de resposta e erro

### 4.1 Envelope padrão

**Recurso único** → `StandardResponse<T>`:

```json
{ "success": true, "message": "...", "data": { ... } }
```

**Lista** → `ListResponse<T>` (agora com **meta**):

```json
{
  "success": true,
  "message": "...",
  "data": [ ... ],
  "meta": { "total": 42, "skip": 0, "limit": 100 }
}
```

No client HTTP tipado (Axios), o payload útil costuma ser `response.data.data`; paginação em `response.data.meta`.

### 4.2 Exceções ao envelope

| Caso                         | Shape                                              |
| ---------------------------- | -------------------------------------------------- |
| `DELETE /products/{id}`      | **204** sem body (soft-delete)                     |
| `DELETE /donations/{id}`     | **204** sem body                                   |
| `/health`, `/ready`, `/live` | `{ status, timestamp }` (fora do envelope)         |

> **Breaking:** `GET /api/v1/reports` agora vem em `StandardResponse<ReportResponse>` (`data.totalRevenue`, etc.).

### 4.3 Erros (todos os 4xx / 5xx, inclusive rota inexistente)

```json
{
  "status": 422,
  "message": "Erro de validação dos dados enviados.",
  "details": [{ "field": "price", "message": "..." }],
  "timestamp": "2026-06-12T10:30:00.000Z"
}
```

- Sempre: `status`, `message`, `timestamp`
- `details` costuma aparecer em **422** de validação; outros erros podem omitir `details`
- **Não** há envelope `{ success, data }` em erro
- Path ID inválido (não-UUID) → **422**
- UUID válido inexistente → **404**

Códigos: `401` · `403` · `404` · `409` (conflito/estoque/integridade) · `422` · `429` · `500` · `503` (ready)

---

## 5. Autenticação JWT

### Decisões travadas

- **Sem refresh token.** Só `accessToken` (JWT Bearer).
- Expiração default: `JWT_EXPIRE_MINUTES=60`.
- **Registro público removido.** Usuários via CLI ou `POST /users` (admin).

### Login (público)

```
POST /api/v1/auth/login
Body: { "email": "...", "password": "..." }
```

Response **200** (`StandardResponse<TokenResponse>`):

```json
{
  "success": true,
  "message": "Login realizado com sucesso.",
  "data": { "accessToken": "eyJ...", "tokenType": "bearer" }
}
```

### Rotas públicas (sem Bearer)

| Endpoint                         | Notas                                      |
| -------------------------------- | ------------------------------------------ |
| `GET /api/v1/products`           | Catálogo **sem** `costPrice`; só ativos    |
| `GET /api/v1/products/{id}`      | Detalhe **sem** `costPrice`; inativo → 404 |
| `POST /api/v1/auth/login`        | Login                                      |
| `GET /health` `/ready` `/live`   | Probes                                     |

### Matriz de papéis

| Recurso / ação                              | Público | operator | admin |
| ------------------------------------------- | :-----: | :------: | :---: |
| `GET /products`, `GET /products/{id}`       |    ✓    |    ✓*    |   ✓*  |
| `GET /products/{id}/manage`                 |         |          |   ✓   |
| `POST /products`, `PATCH /products/{id}`    |         |          |   ✓   |
| `DELETE /products/{id}` (soft)              |         |          |   ✓   |
| `POST /products/{id}/image`                 |         |          |   ✓   |
| `PATCH /products/{id}/stock`                |         |    ✓†    |   ✓‡  |
| `GET /sales`, `GET /sales/{id}`             |         |    ✓     |   ✓   |
| `POST /sales`                               |         |    ✓     |   ✓   |
| `POST /sales/{id}/cancel`                   |         |          |   ✓   |
| `unitPriceOverride` em `POST /sales`        |         | ignorado | honrado |
| CRUD `/donations` + `PATCH`                 |         |          |   ✓   |
| `GET /reports`                              |         |          |   ✓   |
| `GET /auth/me`                              |         |    ✓     |   ✓   |
| `GET/POST /users`                           |         |          |   ✓   |

\* Schema público (sem `costPrice`).  
† Resposta `ProductPublicResponse` (sem `costPrice`).  
‡ Resposta `ProductResponse` (com `costPrice`).

---

## 6. Endpoints

Paginação: `?skip=0&limit=100` (`limit` máx. 500) + `meta.total`.

### 6.1 Produtos — `/api/v1/products`

#### Schemas

| Schema                   | Quando                                                         | `costPrice` |
| ------------------------ | -------------------------------------------------------------- | ----------- |
| `ProductPublicResponse`  | `GET` list/detail público; stock do **operator**               | **ausente** |
| `ProductResponse`        | `POST`, `PATCH`, `GET .../manage`, stock **admin**, image      | presente    |
| `ProductInput`           | body de `POST` (admin) — quantity só na criação                | obrigatório |
| `ProductPatchInput`      | body de `PATCH` (admin) — **sem** `quantity`                   | opcional    |

#### Filtros de listagem

| Query      | Default | Notas                                              |
| ---------- | ------- | -------------------------------------------------- |
| `q`        | —       | Busca em nome / SKU / descrição                    |
| `category` | —       | `ProductCategory`                                  |
| `isActive` | `true`  | Só ativos; `false` = inativos; sem modo “todos”    |
| `inStock`  | —       | `true` → quantity > 0; `false` → quantity ≤ 0      |
| `sort`     | omitido → `-created_at` | `name`, `sku`, `price`, `quantity`, `created_at`, `updated_at`; prefixo `-` = desc; chave inválida cai no default |

#### Operações

| Método | Rota              | Auth            | Response                                      |
| ------ | ----------------- | --------------- | --------------------------------------------- |
| GET    | `/`               | público         | `ListResponse<ProductPublic…>` + meta         |
| GET    | `/{id}`           | público         | `StandardResponse<ProductPublic…>`            |
| GET    | `/{id}/manage`    | admin           | `StandardResponse<ProductResponse>`           |
| POST   | `/`               | admin           | `201` + `ProductResponse`                     |
| PATCH  | `/{id}`           | admin           | `ProductResponse` (não altera estoque)        |
| DELETE | `/{id}`           | admin           | `204` soft-delete (`isActive=false`)          |
| PATCH  | `/{id}/stock`     | admin\|operator | admin→`ProductResponse`; op→`ProductPublic…`  |
| POST   | `/{id}/image`     | admin           | `ProductResponse`                             |

Stock:

```json
{ "delta": -1 }
```

> Estoque **somente** via venda, cancelamento de venda ou `PATCH /stock`. `ProductPatchInput` **não** tem `quantity`.
> Soft-delete: catálogo público e `GET /{id}` ocultam inativos (404). Admin ainda lê via `GET /{id}/manage`. Reativar com `PATCH` `{ "isActive": true }`.
> `isActive` na listagem: default `true` (só ativos). `isActive=false` lista inativos. Não há modo “todos” num único request.

---

### 6.2 Vendas — `/api/v1/sales`

#### Filtros de listagem

| Query               | Default | Notas                                              |
| ------------------- | ------- | -------------------------------------------------- |
| `from` / `to`       | —       | `YYYY-MM-DD` ou ISO 8601 (`to` = fim do dia UTC)   |
| `paymentMethod`     | —       | `PaymentMethod`                                    |
| `productId`         | —       | UUID                                               |
| `includeCancelled`  | `false` | `true` inclui vendas com `cancelledAt` preenchido  |

| Método | Rota            | Auth            | Envelope                                            |
| ------ | --------------- | --------------- | --------------------------------------------------- |
| GET    | `/`             | autenticado     | `ListResponse<SaleResponse>` + meta                 |
| GET    | `/{id}`         | autenticado     | `StandardResponse<SaleResponse>`                    |
| POST   | `/`             | admin\|operator | `201` + `StandardResponse<SaleResponse>`            |
| POST   | `/{id}/cancel`  | admin           | `StandardResponse<SaleResponse>` — **restaura estoque** |

`SaleResponse` inclui `cancelledAt` (`null` se ativa). Cancelar de novo → **409**.

---

### 6.3 Doações — `/api/v1/donations` — **admin only**

#### Filtros de listagem

| Query         | Default | Notas                                            |
| ------------- | ------- | ------------------------------------------------ |
| `direction`   | —       | `DonationDirection` (`recebida` \| `doada`)      |
| `category`    | —       | `DonationCategory`                               |
| `from` / `to` | —       | `YYYY-MM-DD` ou ISO 8601 (`to` = fim do dia UTC) |

| Método | Rota    | Status / envelope                              |
| ------ | ------- | ---------------------------------------------- |
| GET    | `/`     | `ListResponse<DonationResponse>` + meta        |
| GET    | `/{id}` | `StandardResponse<DonationResponse>`           |
| POST   | `/`     | `201` + `StandardResponse<DonationResponse>`   |
| PATCH  | `/{id}` | `StandardResponse<DonationResponse>` (parcial) |
| DELETE | `/{id}` | `204` (hard delete)                            |

---

### 6.4 Relatórios — `/api/v1/reports` — **admin only**

```
GET /api/v1/reports?days=30&paymentMethods=pix,dinheiro&donationCategories=roupas,dinheiro
```

**Response (breaking):** `StandardResponse<ReportResponse>` — ler `response.data.data.*`.

Vendas canceladas **não** entram nos totais.

#### Campos de doação — recebida vs outgoing

| Campo                              | Significado                                      |
| ---------------------------------- | ------------------------------------------------ |
| `totalDonationsMonetary`           | Soma monetária **recebida**                      |
| `totalDonationsCount`              | Contagem **recebida**                            |
| `totalDonationsOutgoingMonetary`   | Soma monetária **doada**                         |
| `totalDonationsOutgoingCount`      | Contagem **doada**                               |
| `totalCombined`                    | `totalRevenue + totalDonationsMonetary`          |

Timezone: buckets diários / janela `days` usam `APP_TIMEZONE` (default **America/Sao_Paulo**).

---

### 6.5 Usuários — `/api/v1/users` — **admin only**

| Método | Rota | Response                          |
| ------ | ---- | --------------------------------- |
| GET    | `/`  | `ListResponse<UserResponse>` + meta |
| POST   | `/`  | `201` + `StandardResponse<User…>` |

---

## 7. Enums

```
UserRole:          "admin" | "operator"
PaymentMethod:     "dinheiro" | "cartao_credito" | "cartao_debito" | "pix" | "boleto"
DonationDirection: "recebida" | "doada"
DonationCategory:  "dinheiro" | "roupas" | "calcados" | "acessorios" | "alimentos" | "outros"
ProductCategory:   "camiseta" | "calca" | "vestido" | "saia" | "jaqueta" | "calcado" | "acessorio" | "outro"
ClothingSize:      "PP"|"P"|"M"|"G"|"GG"|"XGG"|"36"|"38"|"40"|"42"|"44"|"46"|"48"
```

---

## 8. CORS / HTTP / Observabilidade

- `allow_credentials=False`
- Origens via `CORS_ORIGINS` (CSV)
- `X-Correlation-ID` validado (charset + length); inválido → UUID novo
- Logs estruturados com `correlation_id`; `/ready` loga exceção antes do 503
- `ENVIRONMENT=production`: TrustedHost; docs/redoc/openapi off

---

## 9. Dinheiro

- Campos monetários são **`number` no JSON**, 2 casas (`ROUND_HALF_UP`).
- `promoPrice` ≤ `price` (senão 422).
- Doação `category: "dinheiro"` exige `monetaryValue > 0`.
- `PATCH .../stock` com `delta: 0` → 422.
- SKU normalizado para **UPPERCASE** no create/patch.

## 10. Frontend migration checklist (Fase 5 → Next app)

Para o futuro app Next: alinhar client tipado e telas com o contrato abaixo (fonte: este guia + `backend/api-contract.d.ts`).

### Tipos e HTTP client
- [ ] Copiar/atualizar `backend/api-contract.d.ts` (ex.: `src/types/api.d.ts`)
- [ ] Tipar listas como `ListResponse<T>` com `meta: { total, skip, limit }` — paginação UI lê `meta`, não `data.length`
- [ ] Tipar recurso único / reports / cancel como `StandardResponse<T>` — payload em `.data`
- [ ] Erros: parsear `ErrorResponse` (`status`, `message`, `timestamp`, `details?`) — **sem** `{ success, data }`
- [ ] Path params: só UUID; inválido → **422**; inexistente → **404**

### Produtos
- [ ] Remover qualquer `PUT /products/{id}` → usar `PATCH` com `ProductPatchInput` (**sem** `quantity`)
- [ ] Estoque só via `PATCH /products/{id}/stock` `{ delta }` (≠ 0) ou fluxo de venda/cancel
- [ ] Catálogo público: `ProductPublicResponse` (sem `costPrice`); soft-delete some da lista/`GET /{id}`
- [ ] Admin detalhe/custo: `GET /products/{id}/manage` → `ProductResponse` (com `costPrice`)
- [ ] Operator `PATCH .../stock`: tipar resposta como `ProductPublicResponse` (sem `costPrice`); admin como `ProductResponse`
- [ ] Filtros: `q`, `category`, `isActive` (default true), `inStock`, `sort` (`name|sku|price|quantity|created_at|updated_at`, `-` = desc)
- [ ] Soft-delete UI: `DELETE` → 204; reativar com `PATCH { isActive: true }`

### Vendas / doações / reports
- [ ] Cancelamento: `POST /sales/{id}/cancel` (admin) — estoque restaurado; 2º cancel → 409; listar canceladas com `includeCancelled=true`
- [ ] Filtros vendas: `from`, `to`, `paymentMethod`, `productId`, `includeCancelled`
- [ ] Doações: `PATCH /donations/{id}` parcial; filtros `direction`, `category`, `from`, `to`
- [ ] Reports: `GET /reports` → `StandardResponse<ReportResponse>` (ler `response.data.data.*`, não o body raiz)
- [ ] Reports: vendas canceladas **não** entram nos totais

### Auth / misc
- [ ] Base URL `/api/v1` (sem alias `/api`); Bearer JWT sem refresh
- [ ] Headers: ecoar / logar `X-Correlation-ID` quando útil para suporte
- [ ] Money: `number` com 2 casas; `promoPrice` ≤ `price`
