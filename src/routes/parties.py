"""Party (customer) routes — scoped to the caller's company."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.common import Message
from ..schemas.party import PartyCreate, PartyOut, PartyUpdate
from ..services import party_service
from ..utils.deps import require_company_user

router = APIRouter(prefix="/parties", tags=["parties"])


@router.get("", response_model=list[PartyOut])
def list_parties(
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return party_service.list_parties(db, current_user.company_id, search, skip, limit)


@router.post("", response_model=PartyOut, status_code=status.HTTP_201_CREATED)
def create_party(
    payload: PartyCreate,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return party_service.create_party(db, current_user.company_id, payload)


@router.get("/{party_id}", response_model=PartyOut)
def get_party(
    party_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return party_service.get_party(db, current_user.company_id, party_id)


@router.patch("/{party_id}", response_model=PartyOut)
def update_party(
    party_id: int,
    payload: PartyUpdate,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return party_service.update_party(db, current_user.company_id, party_id, payload)


@router.delete("/{party_id}", response_model=Message)
def delete_party(
    party_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    party_service.delete_party(db, current_user.company_id, party_id)
    return Message(detail="Party deleted")
