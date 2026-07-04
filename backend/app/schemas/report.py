from typing import List

from pydantic import BaseModel


class TopProduct(BaseModel):
    name: str
    sku: str
    revenue: float
    units: int


class SalesByPaymentMethod(BaseModel):
    method: str
    count: int
    revenue: float
    pct: float


class RevenueByDay(BaseModel):
    date: str
    revenue: float
    donations: float
    count: int


class ReportResponse(BaseModel):
    """Formato da resposta de relatórios, sem envelope StandardResponse."""

    totalRevenue: float
    totalSales: int
    averageTicket: float
    totalDonationsMonetary: float
    totalDonationsCount: int
    totalCombined: float
    topProductsByRevenue: List[TopProduct]
    topProductsByUnits: List[TopProduct]
    salesByPaymentMethod: List[SalesByPaymentMethod]
    revenueByDay: List[RevenueByDay]
