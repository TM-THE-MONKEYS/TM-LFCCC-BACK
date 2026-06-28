from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.get("", response_model=ReportResponse)
def get_reports(
    days: int = Query(default=30, ge=1, le=365, description="Janela de dias"),
    paymentMethods: Optional[str] = Query(
        default=None,
        description="CSV de métodos de pagamento (ex: pix,dinheiro)",
    ),
    donationCategories: Optional[str] = Query(
        default=None,
        description="CSV de categorias de doação (ex: roupas,dinheiro)",
    ),
    db: Session = Depends(get_db),
):
    payment_methods_list: Optional[List[str]] = (
        [m.strip() for m in paymentMethods.split(",") if m.strip()]
        if paymentMethods
        else None
    )
    donation_categories_list: Optional[List[str]] = (
        [c.strip() for c in donationCategories.split(",") if c.strip()]
        if donationCategories
        else None
    )
    return ReportService(db).get_report(
        days=days,
        payment_methods=payment_methods_list,
        donation_categories=donation_categories_list,
    )
