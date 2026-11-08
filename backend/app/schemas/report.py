from pydantic import BaseModel

from app.core.money import MoneyDecimal


class TopProduct(BaseModel):
    name: str
    sku: str
    revenue: MoneyDecimal
    units: int


class SalesByPaymentMethod(BaseModel):
    method: str
    count: int
    revenue: MoneyDecimal
    pct: float


class RevenueByDay(BaseModel):
    date: str
    revenue: MoneyDecimal
    donations: MoneyDecimal
    count: int


class ReportResponse(BaseModel):
    """Payload de relatórios (envolvido por StandardResponse na rota GET /reports)."""

    totalRevenue: MoneyDecimal
    totalSales: int
    averageTicket: MoneyDecimal
    totalDonationsMonetary: MoneyDecimal
    totalDonationsCount: int
    totalDonationsOutgoingMonetary: MoneyDecimal
    totalDonationsOutgoingCount: int
    totalCombined: MoneyDecimal
    topProductsByRevenue: list[TopProduct]
    topProductsByUnits: list[TopProduct]
    salesByPaymentMethod: list[SalesByPaymentMethod]
    revenueByDay: list[RevenueByDay]
