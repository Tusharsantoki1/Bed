"""Item (product/service catalog) routes — scoped to the caller's company."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.common import Message
from ..schemas.item import ItemCreate, ItemOut, ItemUpdate
from ..services import item_service
from ..utils.deps import require_company_user

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
def list_items(
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return item_service.list_items(db, current_user.company_id, search, skip, limit)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return item_service.create_item(db, current_user.company_id, payload)


@router.get("/{item_id}", response_model=ItemOut)
def get_item(
    item_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return item_service.get_item(db, current_user.company_id, item_id)


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return item_service.update_item(db, current_user.company_id, item_id, payload)


@router.delete("/{item_id}", response_model=Message)
def delete_item(
    item_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    item_service.delete_item(db, current_user.company_id, item_id)
    return Message(detail="Item deleted")
