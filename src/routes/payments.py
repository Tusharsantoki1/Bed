"""Payment (collection ledger) routes — scoped to the caller's company."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.common import Message
from ..schemas.payment import PaymentCreate, PaymentOut
from ..services import payment_service
from ..utils.deps import require_company_editor, require_company_user

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(
    party_id: int | None = None,
    invoice_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return payment_service.list_payments(
        db, current_user.company_id, party_id, invoice_id, skip, limit
    )


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    return payment_service.create_payment(
        db, current_user.company_id, payload, current_user.id
    )


@router.delete("/{payment_id}", response_model=Message)
def delete_payment(
    payment_id: int,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    payment_service.delete_payment(db, current_user.company_id, payment_id)
    return Message(detail="Payment deleted")
