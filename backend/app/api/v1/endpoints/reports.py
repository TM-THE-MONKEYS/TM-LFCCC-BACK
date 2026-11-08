from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.api.openapi_responses import OPENAPI_ERRORS
from app.core.enums import DonationCategory, PaymentMethod, UserRole
from app.exceptions import UnprocessableError
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter()

_PAYMENT_VALUES = {e.value for e in PaymentMethod}
_DONATION_CATEGORY_VALUES = {e.value for e in DonationCategory}


def _parse_csv_against_enum(
    raw: str | None,
    allowed: set[str],
    field_label: str,
) -> list[str] | None:
    """Split CSV query param and validate each token against an enum value set."""
    if not raw:
        return None
    values = [token.strip() for token in raw.split(",") if token.strip()]
    if not values:
        return None
    invalid = [v for v in values if v not in allowed]
    if invalid:
        accepted = ", ".join(sorted(allowed))
        raise UnprocessableError(
            f"{field_label} inválido(s): {', '.join(invalid)}. Valores aceitos: {accepted}."
        )
    return values


@router.get(
    "",
    response_model=StandardResponse[ReportResponse],
    summary="Relatório agregado de vendas e doações",
    operation_id="get_reports",
    responses={
        401: OPENAPI_ERRORS[401],
        403: OPENAPI_ERRORS[403],
        422: OPENAPI_ERRORS[422],
    },
)
def get_reports(
    days: int = Query(default=30, ge=1, le=365, description="Janela de dias"),
    paymentMethods: str | None = Query(
        default=None,
        description="CSV de métodos de pagamento (ex: pix,dinheiro)",
    ),
    donationCategories: str | None = Query(
        default=None,
        description="CSV de categorias de doação (ex: roupas,dinheiro)",
    ),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    payment_methods_list = _parse_csv_against_enum(
        paymentMethods, _PAYMENT_VALUES, "Método(s) de pagamento"
    )
    donation_categories_list = _parse_csv_against_enum(
        donationCategories, _DONATION_CATEGORY_VALUES, "Categoria(s) de doação"
    )
    report = ReportService(db).get_report(
        days=days,
        payment_methods=payment_methods_list,
        donation_categories=donation_categories_list,
    )
    return StandardResponse(message="Relatório gerado com sucesso.", data=report)
