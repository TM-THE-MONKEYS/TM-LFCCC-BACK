from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.donation import Donation
from app.models.sale import Sale
from app.schemas.report import (
    ReportResponse,
    RevenueByDay,
    SalesByPaymentMethod,
    TopProduct,
)


class ReportService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_report(
        self,
        days: int = 30,
        payment_methods: Optional[List[str]] = None,
        donation_categories: Optional[List[str]] = None,
    ) -> ReportResponse:
        # ── Window ────────────────────────────────────────────────────────────
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        window_start = today - timedelta(days=days)

        # ── Sales query ───────────────────────────────────────────────────────
        sale_q = self._db.query(Sale).filter(Sale.created_at >= window_start)
        if payment_methods:
            sale_q = sale_q.filter(Sale.payment_method.in_(payment_methods))
        sales: List[Sale] = sale_q.order_by(desc(Sale.created_at)).all()

        # ── Donations query ───────────────────────────────────────────────────
        don_q = self._db.query(Donation).filter(Donation.created_at >= window_start)
        if donation_categories:
            don_q = don_q.filter(Donation.category.in_(donation_categories))
        donations: List[Donation] = don_q.all()

        # ── Aggregations ──────────────────────────────────────────────────────
        total_revenue = round(sum(s.total for s in sales), 2)
        total_sales = len(sales)
        average_ticket = round(total_revenue / total_sales, 2) if total_sales else 0.0
        total_donations_monetary = round(sum(d.monetary_value for d in donations), 2)
        total_donations_count = len(donations)
        total_combined = round(total_revenue + total_donations_monetary, 2)

        # ── Top products ──────────────────────────────────────────────────────
        product_agg: dict[str, dict] = defaultdict(
            lambda: {"name": "", "sku": "", "revenue": 0.0, "units": 0}
        )
        for sale in sales:
            key = sale.product_sku
            product_agg[key]["name"] = sale.product_name
            product_agg[key]["sku"] = sale.product_sku
            product_agg[key]["revenue"] = round(
                product_agg[key]["revenue"] + sale.total, 2
            )
            product_agg[key]["units"] += sale.quantity

        all_products = [
            TopProduct(**v) for v in product_agg.values()
        ]
        top_by_revenue = sorted(all_products, key=lambda p: p.revenue, reverse=True)[:5]
        top_by_units = sorted(all_products, key=lambda p: p.units, reverse=True)[:5]

        # ── Sales by payment method ───────────────────────────────────────────
        method_agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "revenue": 0.0})
        for sale in sales:
            method_agg[sale.payment_method]["count"] += 1
            method_agg[sale.payment_method]["revenue"] = round(
                method_agg[sale.payment_method]["revenue"] + sale.total, 2
            )

        sales_by_payment = sorted(
            [
                SalesByPaymentMethod(
                    method=method,
                    count=data["count"],
                    revenue=data["revenue"],
                    pct=round((data["revenue"] / total_revenue * 100), 2)
                    if total_revenue
                    else 0.0,
                )
                for method, data in method_agg.items()
            ],
            key=lambda x: x.revenue,
            reverse=True,
        )

        # ── Revenue by day (include zero days) ────────────────────────────────
        day_revenue: dict[str, float] = defaultdict(float)
        day_donations: dict[str, float] = defaultdict(float)
        day_count: dict[str, int] = defaultdict(int)

        for sale in sales:
            d = sale.created_at.strftime("%Y-%m-%d")
            day_revenue[d] = round(day_revenue[d] + sale.total, 2)
            day_count[d] += 1

        for donation in donations:
            d = donation.created_at.strftime("%Y-%m-%d")
            day_donations[d] = round(day_donations[d] + donation.monetary_value, 2)

        revenue_by_day: List[RevenueByDay] = []
        for i in range(days):
            day = (today - timedelta(days=days - 1 - i)).date()
            d_str = day.strftime("%Y-%m-%d")
            revenue_by_day.append(
                RevenueByDay(
                    date=d_str,
                    revenue=day_revenue.get(d_str, 0.0),
                    donations=day_donations.get(d_str, 0.0),
                    count=day_count.get(d_str, 0),
                )
            )

        return ReportResponse(
            totalRevenue=total_revenue,
            totalSales=total_sales,
            averageTicket=average_ticket,
            totalDonationsMonetary=total_donations_monetary,
            totalDonationsCount=total_donations_count,
            totalCombined=total_combined,
            topProductsByRevenue=top_by_revenue,
            topProductsByUnits=top_by_units,
            salesByPaymentMethod=sales_by_payment,
            revenueByDay=revenue_by_day,
        )
