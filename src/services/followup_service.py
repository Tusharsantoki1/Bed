"""Follow-up (collection chase log) service."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.enums import FollowupStatus
from ..models.followup import Followup
from ..models.invoice import Invoice
from ..schemas.followup import FollowupCreate, FollowupOut, FollowupUpdate
from . import party_service


def to_out(followup: Followup) -> FollowupOut:
    """FollowupOut with the party name folded in (for list/summary views)."""
    out = FollowupOut.model_validate(followup)
    out.party_name = followup.party.name if followup.party else None
    return out


def get_followup(db: Session, company_id: int, followup_id: int) -> Followup:
    f = db.get(Followup, followup_id)
    if f is None or f.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return f


def list_followups(
    db: Session, company_id: int, party_id: Optional[int] = None,
    status_filter: Optional[FollowupStatus] = None, skip: int = 0, limit: int = 100,
) -> list[Followup]:
    stmt = (
        select(Followup)
        .where(Followup.company_id == company_id)
        .options(selectinload(Followup.party))
    )
    if party_id is not None:
        stmt = stmt.where(Followup.party_id == party_id)
    if status_filter is not None:
        stmt = stmt.where(Followup.status == status_filter)
    stmt = stmt.order_by(Followup.followup_date.desc(), Followup.id.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


def due_followups(db: Session, company_id: int, on_date: Optional[date] = None) -> list[Followup]:
    """Pending follow-ups whose next date is on/before the given date (today)."""
    on_date = on_date or date.today()
    stmt = (
        select(Followup)
        .where(
            Followup.company_id == company_id,
            Followup.status == FollowupStatus.pending,
            Followup.next_followup_date.is_not(None),
            Followup.next_followup_date <= on_date,
        )
        .options(selectinload(Followup.party))
        .order_by(Followup.next_followup_date.asc(), Followup.id.asc())
    )
    return list(db.execute(stmt).scalars())


def create_followup(
    db: Session, company_id: int, data: FollowupCreate, created_by_id: Optional[int]
) -> Followup:
    party_service.get_party(db, company_id, data.party_id)  # 404 if not ours
    if data.invoice_id is not None:
        inv = db.get(Invoice, data.invoice_id)
        if inv is None or inv.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    followup = Followup(
        company_id=company_id,
        party_id=data.party_id,
        invoice_id=data.invoice_id,
        created_by_id=created_by_id,
        type=data.type,
        remarks=data.remarks,
        followup_date=data.followup_date or date.today(),
        next_followup_date=data.next_followup_date,
        status=data.status,
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


def update_followup(
    db: Session, company_id: int, followup_id: int, data: FollowupUpdate
) -> Followup:
    followup = get_followup(db, company_id, followup_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(followup, field, value)
    db.commit()
    db.refresh(followup)
    return followup


def delete_followup(db: Session, company_id: int, followup_id: int) -> None:
    followup = get_followup(db, company_id, followup_id)
    db.delete(followup)
    db.commit()
