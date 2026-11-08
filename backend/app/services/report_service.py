"""Report aggregations for the sales / donations dashboard window."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import DonationDirection
from app.core.money import quantize_money
from app.models.donation import Donation
from app.models.sale import Sale
from app.schemas.report import (
    ReportResponse,
    RevenueByDay,
    SalesByPaymentMethod,
    TopProduct,
)


def _app_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().APP_TIMEZONE)


def _window_bounds(days: int) -> tuple[datetime, date, list[date]]:
    """Inclusive window of `days` calendar days ending today in APP_TIMEZONE.

    window_start is the start of (today - (days - 1)) in APP_TIMEZONE, as UTC.
    Returns (window_start_utc, today_local, ordered_day_list).
    """
    tz = _app_tz()
    today_local = datetime.now(tz).date()
    first_day = today_local - timedelta(days=days - 1)
    window_start_local = datetime.combine(first_day, datetime.min.time(), tzinfo=tz)
    window_start_utc = window_start_local.astimezone(UTC)
    day_list = [first_day + timedelta(days=i) for i in range(days)]
    return window_start_utc, today_local, day_list


def _to_local_date(dt: datetime) -> date:
    """Normalize a DB timestamp to a calendar date in APP_TIMEZONE."""
    tz = _app_tz()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(tz).date()


def _as_money(value: object) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return quantize_money(value)  # type: ignore[arg-type]


class ReportService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_report(
        self,
        days: int = 30,
        payment_methods: list[str] | None = None,
        donation_categories: list[str] | None = None,
    ) -> ReportResponse:
        window_start, _today, day_list = _window_bounds(days)

        # ── Sales aggregates (SQL) — exclude cancelled/refunded ───────────────
        sale_filters = [Sale.created_at >= window_start, Sale.cancelled_at.is_(None)]
        if payment_methods:
            sale_filters.append(Sale.payment_method.in_(payment_methods))

        sales_totals = self._db.execute(
            select(
                func.coalesce(func.sum(Sale.total), 0),
                func.count(Sale.id),
            ).where(*sale_filters)
        ).one()
        total_revenue = _as_money(sales_totals[0])
        total_sales = int(sales_totals[1] or 0)
        average_ticket = (
            quantize_money(total_revenue / Decimal(total_sales)) if total_sales else Decimal("0.00")
        )

        # ── Donation aggregates (SQL) — split by direction ────────────────────
        don_filters = [Donation.created_at >= window_start]
        if donation_categories:
            don_filters.append(Donation.category.in_(donation_categories))

        is_recebida = Donation.direction == DonationDirection.recebida
        is_doada = Donation.direction == DonationDirection.doada

        don_totals = self._db.execute(
            select(
                func.coalesce(
                    func.sum(case((is_recebida, Donation.monetary_value), else_=0)),
                    0,
                ),
                func.coalesce(func.sum(case((is_recebida, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((is_doada, Donation.monetary_value), else_=0)),
                    0,
                ),
                func.coalesce(func.sum(case((is_doada, 1), else_=0)), 0),
            ).where(*don_filters)
        ).one()
        total_donations_monetary = _as_money(don_totals[0])
        total_donations_count = int(don_totals[1] or 0)
        total_donations_outgoing_monetary = _as_money(don_totals[2])
        total_donations_outgoing_count = int(don_totals[3] or 0)
        total_combined = quantize_money(total_revenue + total_donations_monetary)

        # ── Top products (SQL group_by) ───────────────────────────────────────
        product_rows = self._db.execute(
            select(
                Sale.product_sku,
                Sale.product_name,
                func.sum(Sale.total).label("revenue"),
                func.sum(Sale.quantity).label("units"),
            )
            .where(*sale_filters)
            .group_by(Sale.product_sku, Sale.product_name)
        ).all()
        all_products = [
            TopProduct(
                name=row.product_name,
                sku=row.product_sku,
                revenue=_as_money(row.revenue),
                units=int(row.units or 0),
            )
            for row in product_rows
        ]
        top_by_revenue = sorted(all_products, key=lambda p: p.revenue, reverse=True)[:5]
        top_by_units = sorted(all_products, key=lambda p: p.units, reverse=True)[:5]

        # ── Sales by payment method (SQL group_by) ────────────────────────────
        method_rows = self._db.execute(
            select(
                Sale.payment_method,
                func.count(Sale.id).label("sale_count"),
                func.sum(Sale.total).label("revenue"),
            )
            .where(*sale_filters)
            .group_by(Sale.payment_method)
        ).all()
        sales_by_payment = sorted(
            [
                SalesByPaymentMethod(
                    method=(
                        row.payment_method.value
                        if hasattr(row.payment_method, "value")
                        else str(row.payment_method)
                    ),
                    count=int(row.sale_count or 0),
                    revenue=_as_money(row.revenue),
                    pct=(
                        float(quantize_money(_as_money(row.revenue) / total_revenue * 100))
                        if total_revenue
                        else 0.0
                    ),
                )
                for row in method_rows
            ],
            key=lambda x: x.revenue,
            reverse=True,
        )

        # ── Daily series (bucket in APP_TIMEZONE; length == days) ─────────────
        day_revenue: dict[str, Decimal] = {d.isoformat(): Decimal("0.00") for d in day_list}
        day_donations: dict[str, Decimal] = {d.isoformat(): Decimal("0.00") for d in day_list}
        day_count: dict[str, int] = {d.isoformat(): 0 for d in day_list}

        sale_day_rows = self._db.execute(
            select(Sale.created_at, Sale.total).where(*sale_filters)
        ).all()
        for created_at, total in sale_day_rows:
            d_str = _to_local_date(created_at).isoformat()
            if d_str in day_revenue:
                day_revenue[d_str] = quantize_money(day_revenue[d_str] + _as_money(total))
                day_count[d_str] += 1

        # Incoming (recebida) donations only for daily donations series
        don_day_rows = self._db.execute(
            select(Donation.created_at, Donation.monetary_value).where(*don_filters, is_recebida)
        ).all()
        for created_at, monetary_value in don_day_rows:
            d_str = _to_local_date(created_at).isoformat()
            if d_str in day_donations:
                day_donations[d_str] = quantize_money(
                    day_donations[d_str] + _as_money(monetary_value)
                )

        revenue_by_day = [
            RevenueByDay(
                date=d.isoformat(),
                revenue=day_revenue[d.isoformat()],
                donations=day_donations[d.isoformat()],
                count=day_count[d.isoformat()],
            )
            for d in day_list
        ]

        return ReportResponse(
            totalRevenue=total_revenue,
            totalSales=total_sales,
            averageTicket=average_ticket,
            totalDonationsMonetary=total_donations_monetary,
            totalDonationsCount=total_donations_count,
            totalDonationsOutgoingMonetary=total_donations_outgoing_monetary,
            totalDonationsOutgoingCount=total_donations_outgoing_count,
            totalCombined=total_combined,
            topProductsByRevenue=top_by_revenue,
            topProductsByUnits=top_by_units,
            salesByPaymentMethod=sales_by_payment,
            revenueByDay=revenue_by_day,
        )
