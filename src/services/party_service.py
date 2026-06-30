"""Party (customer) CRUD, always scoped to the caller's company."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.party import Party
from ..schemas.party import PartyCreate, PartyUpdate


def get_party(db: Session, company_id: int, party_id: int) -> Party:
    party = db.get(Party, party_id)
    if party is None or party.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Party not found")
    return party


def list_parties(
    db: Session, company_id: int, search: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Party]:
    stmt = select(Party).where(Party.company_id == company_id)
    if search:
        stmt = stmt.where(Party.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Party.name).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


def count_parties(db: Session, company_id: int) -> int:
    return db.execute(
        select(func.count(Party.id)).where(Party.company_id == company_id)
    ).scalar_one()


def create_party(db: Session, company_id: int, data: PartyCreate) -> Party:
    party = Party(company_id=company_id, **data.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


def update_party(db: Session, company_id: int, party_id: int, data: PartyUpdate) -> Party:
    party = get_party(db, company_id, party_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party


def delete_party(db: Session, company_id: int, party_id: int) -> None:
    party = get_party(db, company_id, party_id)
    if party.invoices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a party that has invoices",
        )
    db.delete(party)
    db.commit()
