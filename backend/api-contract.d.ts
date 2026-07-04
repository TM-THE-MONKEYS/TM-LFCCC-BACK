/**
 * API Contract — Vitrine Backend
 * Gerado em: 2026-07-03
 *
 * Copie este arquivo para o seu projeto frontend (ex: src/types/api.d.ts)
 * e use os tipos nas chamadas Axios/Fetch.
 *
 * Base URL: http://localhost:8000/api/v1
 * Nota: /api/* é um alias retrocompatível para /api/v1/*
 */

// ─────────────────────────────────────────────────────────────────────────────
// Envelopes de resposta
// Todos os endpoints (exceto /reports) retornam um destes dois formatos.
// ─────────────────────────────────────────────────────────────────────────────

/** Resposta de recurso único */
export interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

/** Resposta de lista */
export interface ListResponse<T> {
  success: boolean;
  message: string;
  data: T[];
}

/** Resposta de erro (todos os status 4xx e 5xx) */
export interface ErrorResponse {
  status: number;
  message: string;
  timestamp: string; // ISO 8601 ex: "2026-07-03T10:00:00.000Z"
  details?: ErrorDetail[]; // presente apenas em erros 422
}

/** Detalhe de erro de validação de campo */
export interface ErrorDetail {
  field: string;
  message: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────────────────────────────────────

export type ProductCategory =
  | "camiseta"
  | "calca"
  | "vestido"
  | "saia"
  | "jaqueta"
  | "calcado"
  | "acessorio"
  | "outro";

export type PaymentMethod =
  | "dinheiro"
  | "cartao_credito"
  | "cartao_debito"
  | "pix"
  | "boleto";

export type DonationDirection = "recebida" | "doada";

export type DonationCategory =
  | "dinheiro"
  | "roupas"
  | "calcados"
  | "acessorios"
  | "alimentos"
  | "outros";

// ─────────────────────────────────────────────────────────────────────────────
// Auth — /api/v1/auth
// ─────────────────────────────────────────────────────────────────────────────

/** POST /auth/register */
export interface UserCreate {
  name: string;
  email: string;    // formato válido obrigatório
  password: string; // mínimo 8 caracteres
}

/** POST /auth/login */
export interface LoginRequest {
  email: string;
  password: string;
}

/** data dentro de StandardResponse<TokenResponse> */
export interface TokenResponse {
  accessToken: string; // use no header: Authorization: Bearer <accessToken>
  tokenType: string;   // sempre "bearer"
}

/** data dentro de StandardResponse<UserResponse> */
export interface UserResponse {
  id: string;
  name: string;
  email: string;
  isActive: boolean;
  createdAt: string; // ISO 8601
}

// Exemplos de uso:
//   POST /auth/register  → StandardResponse<UserResponse>   (201)
//   POST /auth/login     → StandardResponse<TokenResponse>  (200)
//   GET  /auth/me        → StandardResponse<UserResponse>   (200) — requer Bearer token

// ─────────────────────────────────────────────────────────────────────────────
// Produtos — /api/v1/products
// ─────────────────────────────────────────────────────────────────────────────

/** POST /products  e  PUT /products/{id} */
export interface ProductInput {
  sku: string;
  name: string;
  description?: string;
  category: ProductCategory;
  sizes?: string[];
  colors?: string[];
  price: number;             // >= 0
  promoPrice?: number;       // >= 0, opcional
  costPrice: number;         // >= 0
  quantity?: number;         // >= 0, default 0
  imageUrl?: string;
}

/** data dentro de StandardResponse<ProductResponse> ou ListResponse<ProductResponse> */
export interface ProductResponse {
  id: string;
  sku: string;
  name: string;
  description: string;
  category: ProductCategory;
  sizes: string[];
  colors: string[];
  price: number;
  promoPrice: number | null;
  costPrice: number;
  quantity: number;
  imageUrl: string | null;
  isActive: boolean;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
}

/** PATCH /products/{id}/stock */
export interface StockPatchInput {
  delta: number; // positivo = aumenta, negativo = diminui (409 se < 0 resultante)
}

// Exemplos de uso:
//   GET    /products              → ListResponse<ProductResponse>    (200)
//   GET    /products?skip=0&limit=100  → ListResponse<ProductResponse>
//   GET    /products/{id}         → StandardResponse<ProductResponse> (200)
//   POST   /products              → StandardResponse<ProductResponse> (201)
//   PUT    /products/{id}         → StandardResponse<ProductResponse> (200)
//   DELETE /products/{id}         → 204 No Content
//   PATCH  /products/{id}/stock   → StandardResponse<ProductResponse> (200)
//   POST   /products/{id}/image   → StandardResponse<ProductResponse> (200)
//     └─ multipart/form-data, campo: "file", tipos: jpeg/png/webp, max: 5MB

// ─────────────────────────────────────────────────────────────────────────────
// Vendas — /api/v1/sales
// ─────────────────────────────────────────────────────────────────────────────

/** POST /sales */
export interface SaleInput {
  productId: string;         // ID do produto no banco
  quantity: number;          // > 0
  unitPrice: number;         // >= 0 — preço cobrado na venda
  discount?: number;         // 0 a 100 (percentual), default 0
  customerName?: string;
  paymentMethod: PaymentMethod;
  size?: string;
  color?: string;
  notes?: string;
  // NÃO enviar: productName, productSku, total — preenchidos pelo servidor
}

/** data dentro de StandardResponse<SaleResponse> ou ListResponse<SaleResponse> */
export interface SaleResponse {
  id: string;
  productId: string | null;
  productName: string;  // snapshot salvo no momento da venda
  productSku: string;   // snapshot salvo no momento da venda
  quantity: number;
  unitPrice: number;
  discount: number;
  total: number;        // calculado pelo servidor: unitPrice * quantity * (1 - discount/100)
  customerName: string | null;
  paymentMethod: PaymentMethod;
  size: string | null;
  color: string | null;
  notes: string | null;
  createdAt: string; // ISO 8601
}

// Exemplos de uso:
//   GET  /sales              → ListResponse<SaleResponse>    (200)
//   GET  /sales?skip=0&limit=100
//   GET  /sales/{id}         → StandardResponse<SaleResponse> (200)
//   POST /sales              → StandardResponse<SaleResponse> (201)
//     └─ 409 se estoque insuficiente
//     └─ 404 se produto não encontrado

// ─────────────────────────────────────────────────────────────────────────────
// Doações — /api/v1/donations
// ─────────────────────────────────────────────────────────────────────────────

/** POST /donations */
export interface DonationInput {
  direction?: DonationDirection; // default: "recebida"
  donorName?: string;            // preencher quando direction="recebida"
  recipientName?: string;        // preencher quando direction="doada"
  description: string;
  category: DonationCategory;
  productType?: string;
  monetaryValue?: number;        // default 0
  notes?: string;
}

/** data dentro de StandardResponse<DonationResponse> ou ListResponse<DonationResponse> */
export interface DonationResponse {
  id: string;
  direction: DonationDirection;
  donorName: string | null;
  recipientName: string | null;
  description: string;
  category: DonationCategory;
  productType: string | null;
  monetaryValue: number;
  notes: string;
  createdAt: string; // ISO 8601
}

// Exemplos de uso:
//   GET    /donations              → ListResponse<DonationResponse>    (200)
//   GET    /donations?skip=0&limit=100
//   GET    /donations/{id}         → StandardResponse<DonationResponse> (200)
//   POST   /donations              → StandardResponse<DonationResponse> (201)
//   DELETE /donations/{id}         → 204 No Content

// ─────────────────────────────────────────────────────────────────────────────
// Relatórios — /api/v1/reports
// ATENÇÃO: este endpoint NÃO usa envelope StandardResponse — retorna direto.
// ─────────────────────────────────────────────────────────────────────────────

export interface TopProduct {
  name: string;
  sku: string;
  revenue: number;
  units: number;
}

export interface SalesByPaymentMethod {
  method: string;
  count: number;
  revenue: number;
  pct: number; // percentual sobre o total de vendas (0-100)
}

export interface RevenueByDay {
  date: string;    // "YYYY-MM-DD"
  revenue: number;
  donations: number;
  count: number;
}

/** GET /reports — retorno DIRETO (sem envelope) */
export interface ReportResponse {
  totalRevenue: number;
  totalSales: number;
  averageTicket: number;
  totalDonationsMonetary: number;
  totalDonationsCount: number;
  totalCombined: number;
  topProductsByRevenue: TopProduct[];  // top 5
  topProductsByUnits: TopProduct[];    // top 5
  salesByPaymentMethod: SalesByPaymentMethod[];
  revenueByDay: RevenueByDay[];        // um item por dia na janela
}

// Query params:
//   days               → número de dias (1-365, default 30)
//   paymentMethods     → CSV ex: "pix,dinheiro"
//   donationCategories → CSV ex: "roupas,dinheiro"
//
// Exemplo: GET /reports?days=30&paymentMethods=pix,dinheiro

// ─────────────────────────────────────────────────────────────────────────────
// Observabilidade — sem autenticação
// ─────────────────────────────────────────────────────────────────────────────

// GET /health → { status: "healthy", timestamp: string }
// GET /ready  → { status: "ready",   timestamp: string }  ou 503 se DB offline
// GET /live   → { status: "alive",   timestamp: string }
