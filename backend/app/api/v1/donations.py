from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse, StandardResponse
from app.schemas.donation import DonationInput, DonationResponse
from app.services.donation_service import DonationService

router = APIRouter()


@router.get("", response_model=ListResponse[DonationResponse])
def list_donations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return ListResponse(
        message="Doações listadas com sucesso.",
        data=[DonationResponse.model_validate(d) for d in DonationService(db).list_all(skip=skip, limit=limit)],
    )


@router.get("/{donation_id}", response_model=StandardResponse[DonationResponse])
def get_donation(donation_id: str, db: Session = Depends(get_db)):
    return StandardResponse(
        message="Doação encontrada.",
        data=DonationResponse.model_validate(DonationService(db).get_by_id(donation_id)),
    )


@router.post("", response_model=StandardResponse[DonationResponse], status_code=status.HTTP_201_CREATED)
def create_donation(
    data: DonationInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return StandardResponse(
        message="Doação registrada com sucesso.",
        data=DonationResponse.model_validate(DonationService(db).create(data)),
    )


@router.delete("/{donation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donation(
    donation_id: str,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    DonationService(db).delete(donation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
