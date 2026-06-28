from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, optional_auth
from app.models.user import User
from app.schemas.common import ListResponse
from app.schemas.donation import DonationInput, DonationResponse
from app.services.donation_service import DonationService

router = APIRouter()


@router.get("", response_model=ListResponse[DonationResponse])
def list_donations(db: Session = Depends(get_db)):
    return ListResponse(
        data=[DonationResponse.model_validate(d) for d in DonationService(db).list_all()]
    )


@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def create_donation(
    data: DonationInput,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    return DonationResponse.model_validate(DonationService(db).create(data))


@router.delete("/{donation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donation(
    donation_id: str,
    db: Session = Depends(get_db),
    _: Optional[User] = Depends(optional_auth),
):
    DonationService(db).delete(donation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
