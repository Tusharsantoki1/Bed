"""Company admin-panel dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.dashboard import CompanyDashboard
from ..services import dashboard_service
from ..utils.deps import require_company_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=CompanyDashboard)
def company_dashboard(
    current_user: User = Depends(require_company_user), db: Session = Depends(get_db)
):
    return dashboard_service.company_dashboard(db, current_user.company_id)
