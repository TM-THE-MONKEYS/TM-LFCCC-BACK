# Guia de Integração Frontend ↔ Backend — Vitrine

> **Para o agente de frontend:** Este documento descreve o contrato completo da API REST do backend Vitrine.
> Use-o como fonte única de verdade para corrigir chamadas existentes e implementar integrações novas.

---

## 1. Configuração Base

```
Base URL local:    http://localhost:8000
Prefixo da API:    /api/v1         (canônico)
                   /api            (alias — ambos funcionam)
Swagger UI:        http://localhost:8000/docs
```

Todo request com body deve ter `Content-Type: application/json`, exceto upload de imagem (`multipart/form-data`).

---

## 2. Convenção de Campos — camelCase OBRIGATÓRIO

**O backend usa `alias_generator=to_camel` em todos os schemas.**

Isso significa:

- Requests: enviar campos em **camelCase** (`productId`, `unitPrice`, `createdAt`)
- Responses: receber campos em **camelCase**

### ⚠️ Correções obrigatórias no frontend

| Campo errado (snake_case) | Campo correto (camelCase) | Onde ocorre                      |
| ------------------------- | ------------------------- | -------------------------------- |
| `access_token`            | `accessToken`             | Response do `/auth/login`        |
| `token_type`              | `tokenType`               | Response do `/auth/login`        |
| `product_id`              | `productId`               | Body de venda, response de venda |
| `product_name`            | `productName`             | Body e response de venda         |
| `product_sku`             | `productSku`              | Body e response de venda         |
| `unit_price`              | `unitPrice`               | Body e response de venda         |
| `payment_method`          | `paymentMethod`           | Body e response de venda         |
| `customer_name`           | `customerName`            | Body e response de venda         |
| `promo_price`             | `promoPrice`              | Body e response de produto       |
| `cost_price`              | `costPrice`               | Body e response de produto       |
| `image_url`               | `imageUrl`                | Response de produto              |
| `is_active`               | `isActive`                | Response de produto e usuário    |
| `created_at`              | `createdAt`               | Todos os responses               |
| `updated_at`              | `updatedAt`               | Response de produto              |
| `donor_name`              | `donorName`               | Body e response de doação        |
| `recipient_name`          | `recipientName`           | Body e response de doação        |
| `product_type`            | `productType`             | Body e response de doação        |
| `monetary_value`          | `monetaryValue`           | Body e response de doação        |

---

## 3. Formato de Datas

Todas as datas retornam como string ISO 8601 UTC com milissegundos:

```
"2026-06-12T10:30:00.000Z"
```

Ao exibir no frontend, fazer parse com `new Date(str)` ou `dayjs(str)`.

---

## 4. Envelope de Listas

Todos os endpoints de listagem retornam no formato:

```json
{ "data": [ ...itens... ] }
```

O frontend deve sempre acessar `.data` para obter o array.

---

## 5. Erros

Todos os erros seguem o shape:

```json
{
  "status": 422,
  "message": "Validation error",
  "details": [
    { "field": "price", "message": "Valor deve ser maior ou igual a zero" }
  ],
  "timestamp": "2026-06-12T10:30:00.000Z"
}
```

`details` é opcional (presente em erros de validação 422). Tratar sempre via `response.status` e `response.data.message`.

---

## 6. Autenticação JWT

### Login

```
POST /api/v1/auth/login
Body: { "email": "...", "password": "..." }
```

Response **200**:

```json
{
  "accessToken": "eyJ...",
  "tokenType": "bearer"
}
```

> ⚠️ O campo é `accessToken` (camelCase), **não** `access_token`.

### Armazenar e usar o token

```js
// Salvar
localStorage.setItem("token", data.accessToken); // ← accessToken, não access_token

// Enviar em requests autenticados
headers: {
  Authorization: `Bearer ${token}`;
}
```

### Endpoints que exigem autenticação (Bearer obrigatório)

| Endpoint              | Motivo                  |
| --------------------- | ----------------------- |
| `GET /api/v1/auth/me` | Dados do usuário logado |

### Endpoints com autenticação opcional

Os demais endpoints (produtos, vendas, doações) aceitam token mas **não exigem** quando `AUTH_REQUIRED=false` (padrão em dev).

---

## 7. Endpoints Completos

### 7.1 Produtos — `/api/v1/products`

#### GET `/api/v1/products`

Retorna todos os produtos.

```json
{ "data": [ ProductResponse ] }
```

#### GET `/api/v1/products/{id}`

Retorna produto por ID. **404** se não encontrado.

#### POST `/api/v1/products` → 201

```json
{
  "sku": "CAM-001",
  "name": "Camiseta Básica",
  "description": "Descrição opcional",
  "category": "camiseta",
  "sizes": ["P", "M", "G"],
  "colors": ["branco", "preto"],
  "price": 25.0,
  "promoPrice": null,
  "costPrice": 10.0,
  "quantity": 10,
  "imageUrl": null
}
```

**409** se SKU já existe.

#### PUT `/api/v1/products/{id}` → 200

Mesmo body do POST. Substitui todos os campos.

#### DELETE `/api/v1/products/{id}` → 204

Sem body. **404** se não encontrado.

#### PATCH `/api/v1/products/{id}/stock` → 200

```json
{ "delta": -1 }
```

`delta` positivo = incrementa, negativo = decrementa. Estoque nunca vai abaixo de 0.

#### POST `/api/v1/products/{id}/image` → 200

`multipart/form-data`, campo `file`.

- Tipos aceitos: `image/jpeg`, `image/png`, `image/webp`
- Tamanho máximo: 5 MB
- Retorna `ProductResponse` com `imageUrl` preenchida.

**ProductResponse:**

```json
{
  "id": "uuid",
  "sku": "CAM-001",
  "name": "Camiseta Básica",
  "description": "",
  "category": "camiseta",
  "sizes": ["P", "M"],
  "colors": ["branco"],
  "price": 25.0,
  "promoPrice": null,
  "costPrice": 10.0,
  "quantity": 5,
  "imageUrl": "/uploads/products/uuid.jpg",
  "isActive": true,
  "createdAt": "2026-06-12T10:00:00.000Z",
  "updatedAt": "2026-06-12T10:00:00.000Z"
}
```

---

### 7.2 Vendas — `/api/v1/sales`

#### GET `/api/v1/sales`

Retorna vendas ordenadas por `createdAt` decrescente.

```json
{ "data": [ SaleResponse ] }
```

#### POST `/api/v1/sales` → 201

```json
{
  "productId": "uuid-do-produto",
  "productName": "Camiseta Básica",
  "productSku": "CAM-001",
  "quantity": 2,
  "unitPrice": 25.0,
  "discount": 10,
  "total": 45.0,
  "customerName": "João Silva",
  "paymentMethod": "pix",
  "size": "M",
  "color": "branco",
  "notes": ""
}
```

> ⚠️ O campo `total` enviado pelo frontend é **ignorado** — o backend recalcula:
> `total = round(unitPrice * quantity * (1 - discount/100), 2)`

**Erros possíveis:**

- **404** — produto não encontrado
- **409** — estoque insuficiente (`quantity` > `product.quantity`)

**SaleResponse:**

```json
{
  "id": "uuid",
  "productId": "uuid",
  "productName": "Camiseta Básica",
  "productSku": "CAM-001",
  "quantity": 2,
  "unitPrice": 25.0,
  "discount": 10.0,
  "total": 45.0,
  "customerName": "João Silva",
  "paymentMethod": "pix",
  "size": "M",
  "color": "branco",
  "notes": "",
  "createdAt": "2026-06-12T10:00:00.000Z"
}
```

---

### 7.3 Doações — `/api/v1/donations`

#### GET `/api/v1/donations`

Retorna doações ordenadas por `createdAt` decrescente.

```json
{ "data": [ DonationResponse ] }
```

#### POST `/api/v1/donations` → 201

```json
{
  "direction": "recebida",
  "donorName": "Maria",
  "recipientName": null,
  "description": "Roupas de inverno",
  "category": "roupas",
  "productType": "casacos",
  "monetaryValue": 0.0,
  "notes": ""
}
```

`direction` padrão: `"recebida"`. Valores: `"recebida"` | `"doada"`.

#### DELETE `/api/v1/donations/{id}` → 204

Sem body. **404** se não encontrado.

**DonationResponse:**

```json
{
  "id": "uuid",
  "direction": "recebida",
  "donorName": "Maria",
  "recipientName": null,
  "description": "Roupas de inverno",
  "category": "roupas",
  "productType": "casacos",
  "monetaryValue": 0.0,
  "notes": "",
  "createdAt": "2026-06-12T10:00:00.000Z"
}
```

---

### 7.4 Relatórios — `/api/v1/reports`

#### GET `/api/v1/reports`

Query params (todos opcionais):
| Param | Tipo | Padrão | Descrição |
|---|---|---|---|
| `days` | int | 30 | Janela de dias (1-365) |
| `paymentMethods` | string | null | CSV: `"pix,dinheiro"` |
| `donationCategories` | string | null | CSV: `"roupas,dinheiro"` |

**Response (não usa envelope `{ data }`):**

```json
{
  "totalRevenue": 1500.0,
  "totalSales": 42,
  "averageTicket": 35.71,
  "totalDonationsMonetary": 300.0,
  "totalDonationsCount": 8,
  "totalCombined": 1800.0,
  "topProductsByRevenue": [
    { "name": "Camiseta", "sku": "CAM-001", "revenue": 500.0, "units": 20 }
  ],
  "topProductsByUnits": [
    { "name": "Camiseta", "sku": "CAM-001", "revenue": 500.0, "units": 20 }
  ],
  "salesByPaymentMethod": [
    { "method": "pix", "count": 30, "revenue": 1000.0, "pct": 66.67 }
  ],
  "revenueByDay": [
    { "date": "2026-06-12", "revenue": 200.0, "donations": 50.0, "count": 5 }
  ]
}
```

> `revenueByDay` contém **todos os dias** da janela, incluindo dias com `revenue: 0`.

---

### 7.5 Autenticação — `/api/v1/auth`

#### POST `/api/v1/auth/register` → 201

```json
{ "name": "Admin", "email": "admin@vitrine.local", "password": "changeme" }
```

**409** se email já cadastrado.

Response: `UserResponse`

#### POST `/api/v1/auth/login` → 200

```json
{ "email": "admin@vitrine.local", "password": "changeme" }
```

Response:

```json
{ "accessToken": "eyJ...", "tokenType": "bearer" }
```

#### GET `/api/v1/auth/me` → 200

Header: `Authorization: Bearer <token>`

Response: `UserResponse`

```json
{
  "id": "uuid",
  "name": "Admin",
  "email": "admin@vitrine.local",
  "isActive": true,
  "createdAt": "2026-06-12T10:00:00.000Z"
}
```

---

## 8. Enums Válidos

### Categorias de Produto (`category`)

```
"camiseta" | "calca" | "vestido" | "saia" | "jaqueta" | "calcado" | "acessorio" | "outro"
```

### Método de Pagamento (`paymentMethod`)

```
"dinheiro" | "cartao_credito" | "cartao_debito" | "pix" | "boleto"
```

### Direção de Doação (`direction`)

```
"recebida" | "doada"
```

### Categoria de Doação (`category`)

```
"dinheiro" | "roupas" | "calcados"
```

### Tamanhos de Roupa (`sizes[]`)

```
"PP" | "P" | "M" | "G" | "GG" | "XGG" | "36" | "38" | "40" | "42" | "44" | "46" | "48"
```

---

## 9. CORS

Origens liberadas por padrão:

```
http://localhost:5173   (Vite)
http://localhost:3000
http://localhost:8080
```

Para adicionar origens, alterar `CORS_ORIGINS` no `.env` do backend (CSV).

---

## 10. Upload de Imagem

A imagem fica acessível via URL relativa ao backend:

```
http://localhost:8000/uploads/products/<uuid>.jpg
```

O `imageUrl` retornado no `ProductResponse` já vem como path completo (`/uploads/products/...`).
Para exibir: `http://localhost:8000${product.imageUrl}` (concatenar com a base URL em dev).

---

## 11. Checklist de Integração

- [ ] `axios` (ou equivalente) configurado com `baseURL = http://localhost:8000`
- [ ] Interceptor de request adicionando `Authorization: Bearer <token>` quando logado
- [ ] Interceptor de response tratando 401 (redirecionar para login) e 422 (mostrar `details`)
- [ ] Substituir todos os campos snake_case por camelCase nas chamadas (seção 2)
- [ ] Login: ler `data.accessToken` (não `data.access_token`)
- [ ] Listas: acessar `response.data.data` (envelope `{ data: [] }`)
- [ ] Relatórios: acessar `response.data` diretamente (sem envelope)
- [ ] Datas: fazer parse com `new Date()` ou `dayjs()` antes de exibir
- [ ] Upload de imagem: usar `FormData` com campo `file`
- [ ] Imagens: prefixar `imageUrl` com a base URL do backend
