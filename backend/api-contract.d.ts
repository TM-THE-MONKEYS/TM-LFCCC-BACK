/**
 * API Contract — Vitrine Backend
 * Atualizado: Fase 5 — API redesign + errors/logging + app factory (2026-11-07)
 *
 * Copie para o frontend (ex: src/types/api.d.ts) e use nas chamadas Axios/Fetch.
 * Guia narrativo: FRONTEND_INTEGRATION.md (manter alinhado com este arquivo).
 *
 * Base URL: http://localhost:8000/api/v1
 *
 * BREAKING (Fase 5):
 * - ListResponse inclui meta { total, skip, limit }
 * - PUT /products/{id} removido → PATCH parcial (sem quantity)
 * - DELETE /products/{id} é soft-delete (isActive=false); catálogo oculta inativos
 * - GET /products/{id}/manage (admin) → ProductResponse com costPrice
 * - PATCH stock: operator → ProductPublicResponse; admin → ProductResponse
 * - POST /sales/{id}/cancel (admin) restaura estoque
 * - PATCH /donations/{id} parcial
 * - GET /reports agora em StandardResponse<ReportResponse>
 * - Path IDs devem ser UUID (inválido → 422; inexistente → 404)
 *
 * BREAKING (Fases anteriores): alias /api removido; register público removido; sem refresh.
 * Dinheiro: number no JSON, 2 casas.
 *
 * Frontend migration: ver FRONTEND_INTEGRATION.md §10.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Envelopes de resposta
// ─────────────────────────────────────────────────────────────────────────────

export interface PaginationMeta {
  total: number;
  skip: number;
  limit: number;
}

/** Recurso único — GET/{id}, POST, PATCH */
export interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

/** Lista — GET sem id (products, sales, donations, users) */
export interface ListResponse<T> {
  success: boolean;
  message: string;
  data: T[];
  meta: PaginationMeta;
}

/**
 * Erro (todos os 4xx e 5xx, inclusive rota inexistente).
 * Sem envelope { success, data }.
 */
export interface ErrorResponse {
  status: number;
  message: string;
  timestamp: string; // ISO 8601 UTC
  details?: ErrorDetail[];
}

export interface ErrorDetail {
  field: string;
  message: string;
}

export interface HealthProbeResponse {
  status: string; // "healthy" | "ready" | "alive"
  timestamp: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────────────────────────────────────

export type UserRole = "admin" | "operator";

export type ProductCategory =
  | "camiseta"
  | "calca"
  | "vestido"
  | "saia"
  | "jaqueta"
  | "calcado"
  | "acessorio"
  | "outro";

export type ClothingSize =
  | "PP"
  | "P"
  | "M"
  | "G"
  | "GG"
  | "XGG"
  | "36"
  | "38"
  | "40"
  | "42"
  | "44"
  | "46"
  | "48";

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

export interface ListQuery {
  skip?: number;
  limit?: number;
}

export interface ProductListQuery extends ListQuery {
  q?: string;
  category?: ProductCategory;
  /** Default true (só ativos). false = inativos. Sem modo "todos". */
  isActive?: boolean;
  inStock?: boolean;
  /** name|sku|price|quantity|created_at|updated_at; prefix "-" = desc. Omitido → -created_at. */
  sort?: string;
}

export interface SaleListQuery extends ListQuery {
  from?: string; // YYYY-MM-DD | ISO
  to?: string; // YYYY-MM-DD = fim do dia UTC
  paymentMethod?: PaymentMethod;
  productId?: string; // UUID
  includeCancelled?: boolean; // default false
}

export interface DonationListQuery extends ListQuery {
  direction?: DonationDirection;
  category?: DonationCategory;
  from?: string; // YYYY-MM-DD | ISO
  to?: string; // YYYY-MM-DD = fim do dia UTC
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth — /api/v1/auth
// ─────────────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: string; // "bearer"
}

export interface UserResponse {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
}

export interface UserCreate {
  name: string;
  email: string;
  password: string;
  role?: UserRole; // default: operator
}

// ─────────────────────────────────────────────────────────────────────────────
// Produtos — /api/v1/products
// ─────────────────────────────────────────────────────────────────────────────

/** POST /products — admin (quantity só na criação) */
export interface ProductInput {
  sku: string;
  name: string;
  description?: string;
  category: ProductCategory;
  sizes?: ClothingSize[];
  colors?: string[];
  price: number;
  promoPrice?: number;
  costPrice: number;
  quantity?: number;
  imageUrl?: string;
}

/** PATCH /products/{id} — admin; NÃO inclui quantity */
export interface ProductPatchInput {
  sku?: string;
  name?: string;
  description?: string;
  category?: ProductCategory;
  sizes?: ClothingSize[];
  colors?: string[];
  price?: number;
  promoPrice?: number;
  costPrice?: number;
  imageUrl?: string;
  isActive?: boolean;
}

/** GET público — sem costPrice */
export interface ProductPublicResponse {
  id: string;
  sku: string;
  name: string;
  description: string;
  category: ProductCategory;
  sizes: string[];
  colors: string[];
  price: number;
  promoPrice: number | null;
  quantity: number;
  imageUrl: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Admin writes + GET /products/{id}/manage */
export interface ProductResponse extends ProductPublicResponse {
  costPrice: number;
}

export interface StockPatchInput {
  delta: number; // ≠ 0
}

// Authz:
//   GET    /products                 → público (+ meta); sem costPrice
//   GET    /products/{id}            → público (ativo; inativo → 404); sem costPrice
//   GET    /products/{id}/manage     → admin → ProductResponse (incl. inativos + costPrice)
//   POST   /products                 → admin → 201 ProductResponse
//   PATCH  /products/{id}            → admin (sem quantity); reativa com { isActive: true }
//   DELETE /products/{id}            → admin → 204 soft-delete (isActive=false)
//   PATCH  /products/{id}/stock      → admin → ProductResponse; operator → ProductPublicResponse
//   POST   /products/{id}/image      → admin → ProductResponse

// ─────────────────────────────────────────────────────────────────────────────
// Vendas — /api/v1/sales
// ─────────────────────────────────────────────────────────────────────────────

export interface SaleInput {
  productId: string;
  quantity: number;
  discount?: number;
  customerName?: string;
  paymentMethod: PaymentMethod;
  size?: string;
  color?: string;
  notes?: string;
  unitPriceOverride?: number; // admin-only effect
}

export interface SaleResponse {
  id: string;
  productId: string | null;
  productName: string;
  productSku: string;
  quantity: number;
  unitPrice: number;
  discount: number;
  total: number;
  customerName: string | null;
  paymentMethod: PaymentMethod;
  size: string | null;
  color: string | null;
  notes: string | null;
  cancelledAt: string | null;
  createdAt: string;
}

// Authz:
//   GET    /sales                    → autenticado (+ meta)
//   GET    /sales/{id}               → autenticado
//   POST   /sales                    → admin|operator → 201
//   POST   /sales/{id}/cancel        → admin → StandardResponse<SaleResponse>; restaura estoque; 2º → 409

// ─────────────────────────────────────────────────────────────────────────────
// Doações — /api/v1/donations  (admin only)
// ─────────────────────────────────────────────────────────────────────────────

export interface DonationInput {
  direction?: DonationDirection;
  donorName?: string;
  recipientName?: string;
  description: string;
  category: DonationCategory;
  productType?: string;
  monetaryValue?: number;
  notes?: string;
}

export interface DonationPatchInput {
  direction?: DonationDirection;
  donorName?: string;
  recipientName?: string;
  description?: string;
  category?: DonationCategory;
  productType?: string;
  monetaryValue?: number;
  notes?: string;
}

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
  createdAt: string;
}

// Authz (admin only):
//   GET    /donations                → ListResponse + meta
//   GET    /donations/{id}           → StandardResponse
//   POST   /donations                → 201
//   PATCH  /donations/{id}           → parcial (DonationPatchInput)
//   DELETE /donations/{id}           → 204 hard delete

// ─────────────────────────────────────────────────────────────────────────────
// Relatórios — /api/v1/reports  (admin only, COM envelope StandardResponse)
// ─────────────────────────────────────────────────────────────────────────────

export interface ReportQuery {
  days?: number;
  paymentMethods?: string;
  donationCategories?: string;
}

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
  pct: number;
}

export interface RevenueByDay {
  date: string;
  revenue: number;
  donations: number;
  count: number;
}

/**
 * Payload em StandardResponse<ReportResponse> — GET /reports.
 * Vendas canceladas NÃO entram nos totais.
 */
export interface ReportResponse {
  totalRevenue: number;
  totalSales: number;
  averageTicket: number;
  totalDonationsMonetary: number;
  totalDonationsCount: number;
  totalDonationsOutgoingMonetary: number;
  totalDonationsOutgoingCount: number;
  totalCombined: number;
  topProductsByRevenue: TopProduct[];
  topProductsByUnits: TopProduct[];
  salesByPaymentMethod: SalesByPaymentMethod[];
  revenueByDay: RevenueByDay[];
}

// GET /health | /ready | /live — raiz do host (fora do envelope)
