"""Item (product/service catalog) CRUD, always scoped to the caller's company."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.item import Item
from ..schemas.item import ItemCreate, ItemUpdate


def get_item(db: Session, company_id: int, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None or item.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def list_items(
    db: Session, company_id: int, search: str | None = None,
    skip: int = 0, limit: int = 100,
) -> list[Item]:
    stmt = select(Item).where(Item.company_id == company_id)
    if search:
        stmt = stmt.where(Item.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Item.name).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


def count_items(db: Session, company_id: int) -> int:
    return db.execute(
        select(func.count(Item.id)).where(Item.company_id == company_id)
    ).scalar_one()


def create_item(db: Session, company_id: int, data: ItemCreate) -> Item:
    item = Item(company_id=company_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, company_id: int, item_id: int, data: ItemUpdate) -> Item:
    item = get_item(db, company_id, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, company_id: int, item_id: int) -> None:
    # Invoice line items keep their own name/rate snapshot, so deleting a saved
    # item never affects existing invoices.
    item = get_item(db, company_id, item_id)
    db.delete(item)
    db.commit()
