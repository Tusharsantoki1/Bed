"""Follow-up (collection chase log) routes — scoped to the caller's company."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import FollowupStatus
from ..models.user import User
from ..schemas.common import Message
from ..schemas.followup import FollowupCreate, FollowupOut, FollowupUpdate
from ..services import followup_service
from ..utils.deps import require_company_editor, require_company_user

router = APIRouter(prefix="/followups", tags=["followups"])


@router.get("", response_model=list[FollowupOut])
def list_followups(
    party_id: int | None = None,
    status: FollowupStatus | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    rows = followup_service.list_followups(
        db, current_user.company_id, party_id, status, skip, limit
    )
    return [followup_service.to_out(f) for f in rows]


@router.get("/due", response_model=list[FollowupOut])
def due_followups(
    current_user: User = Depends(require_company_user), db: Session = Depends(get_db)
):
    """Pending follow-ups that are due today or earlier."""
    rows = followup_service.due_followups(db, current_user.company_id)
    return [followup_service.to_out(f) for f in rows]


@router.post("", response_model=FollowupOut, status_code=status.HTTP_201_CREATED)
def create_followup(
    payload: FollowupCreate,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    f = followup_service.create_followup(
        db, current_user.company_id, payload, current_user.id
    )
    return followup_service.to_out(f)


@router.patch("/{followup_id}", response_model=FollowupOut)
def update_followup(
    followup_id: int,
    payload: FollowupUpdate,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    f = followup_service.update_followup(db, current_user.company_id, followup_id, payload)
    return followup_service.to_out(f)


@router.delete("/{followup_id}", response_model=Message)
def delete_followup(
    followup_id: int,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    followup_service.delete_followup(db, current_user.company_id, followup_id)
    return Message(detail="Follow-up deleted")
