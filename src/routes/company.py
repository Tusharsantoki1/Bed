"""Company self-service: profile, branding, bank details and staff."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.common import Message
from ..schemas.company import (
    CompanyBrandingUpdate,
    CompanyOut,
    CompanyUpdate,
)
from ..schemas.subscription import SubscriptionStatusInfo
from ..schemas.user import StaffCreate, StaffUpdate, UserOut
from ..services import backup_service, company_service, subscription_service
from ..utils.deps import require_company_admin, require_company_user

router = APIRouter(prefix="/company", tags=["company"])


@router.get("", response_model=CompanyOut)
def get_my_company(
    current_user: User = Depends(require_company_user), db: Session = Depends(get_db)
):
    return company_service.get_company(db, current_user.company_id)


@router.patch("", response_model=CompanyOut)
def update_my_company(
    payload: CompanyUpdate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    company = company_service.get_company(db, current_user.company_id)
    return company_service.update_company(db, company, payload)


@router.put("/branding", response_model=CompanyOut)
def update_branding(
    payload: CompanyBrandingUpdate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    """Upload/replace logo, signature, stamp and payment QR (base64)."""
    company = company_service.get_company(db, current_user.company_id)
    return company_service.update_branding(db, company, payload)


@router.get("/subscription", response_model=SubscriptionStatusInfo)
def my_subscription(
    current_user: User = Depends(require_company_user), db: Session = Depends(get_db)
):
    return subscription_service.get_status_info(db, current_user.company_id)


# --- Staff management (company admin only) ---

@router.get("/staff", response_model=list[UserOut])
def list_staff(
    current_user: User = Depends(require_company_admin), db: Session = Depends(get_db)
):
    return company_service.list_staff(db, current_user.company_id)


@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_staff(
    payload: StaffCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    return company_service.add_staff(db, current_user.company_id, payload)


@router.patch("/staff/{user_id}", response_model=UserOut)
def update_staff(
    user_id: int,
    payload: StaffUpdate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    return company_service.update_staff(db, current_user.company_id, user_id, payload)


@router.patch("/staff/{user_id}/active", response_model=UserOut)
def set_staff_active(
    user_id: int,
    is_active: bool,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
):
    return company_service.set_staff_active(db, current_user.company_id, user_id, is_active)


# --- Backup (company data export) ---

@router.get("/backup")
def export_backup(
    current_user: User = Depends(require_company_admin), db: Session = Depends(get_db)
):
    """Download a JSON snapshot of all this company's data."""
    return backup_service.export_company_data(db, current_user.company_id)
