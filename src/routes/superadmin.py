"""Super admin panel: manage companies, plans and subscriptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.company import Company
from ..models.user import User
from ..schemas.auth import CompanyRegisterRequest
from ..schemas.common import Message
from ..schemas.company import (
    CompanyOut,
    CompanySummary,
    PasswordReset,
    SuperAdminCompanyUpdate,
)
from ..schemas.dashboard import SuperAdminDashboard
from ..schemas.plan import PlanCreate, PlanOut, PlanUpdate
from ..schemas.subscription import SubscriptionCreate, SubscriptionOut
from ..schemas.user import UserOut
from ..services import (
    auth_service,
    company_service,
    dashboard_service,
    plan_service,
    subscription_service,
)
from ..utils.deps import require_super_admin

router = APIRouter(prefix="/admin", tags=["super-admin"], dependencies=[Depends(require_super_admin)])


# --- Dashboard ---

@router.get("/dashboard", response_model=SuperAdminDashboard)
def dashboard(db: Session = Depends(get_db)):
    return dashboard_service.super_admin_dashboard(db)


# --- Plans (catalog) ---

@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return plan_service.list_plans(db)


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    return plan_service.create_plan(db, payload)


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, payload: PlanUpdate, db: Session = Depends(get_db)):
    return plan_service.update_plan(db, plan_id, payload)


@router.delete("/plans/{plan_id}", response_model=Message)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan_service.delete_plan(db, plan_id)
    return Message(detail="Plan deleted")


# --- Companies ---

@router.get("/companies", response_model=list[CompanySummary])
def list_companies(
    search: str | None = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    stmt = select(Company)
    if search:
        stmt = stmt.where(Company.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Company.name).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


@router.post("/companies", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyRegisterRequest, db: Session = Depends(get_db)):
    """Create a company and its admin user (returns the admin account)."""
    return auth_service.register_company(db, payload)


@router.get("/companies/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    return company_service.get_company(db, company_id)


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int, payload: SuperAdminCompanyUpdate, db: Session = Depends(get_db)
):
    """Change a company's locked identity: name, invoice prefix and numbering."""
    company = company_service.get_company(db, company_id)
    return company_service.admin_update_company(db, company, payload)


@router.patch("/companies/{company_id}/password", response_model=Message)
def reset_company_password(
    company_id: int, payload: PasswordReset, db: Session = Depends(get_db)
):
    """Reset the login password of the company's admin user."""
    company_service.reset_company_admin_password(db, company_id, payload.new_password)
    return Message(detail="Company admin password has been reset")


@router.patch("/companies/{company_id}/active", response_model=CompanySummary)
def set_company_active(company_id: int, is_active: bool, db: Session = Depends(get_db)):
    company = company_service.get_company(db, company_id)
    company.is_active = is_active
    db.commit()
    db.refresh(company)
    return company


# --- Subscriptions ---

@router.get("/companies/{company_id}/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(company_id: int, db: Session = Depends(get_db)):
    company_service.get_company(db, company_id)  # 404 if missing
    return subscription_service.list_subscriptions(db, company_id)


@router.post(
    "/companies/{company_id}/subscriptions",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    company_id: int, payload: SubscriptionCreate, db: Session = Depends(get_db)
):
    company_service.get_company(db, company_id)  # 404 if missing
    return subscription_service.create_subscription(db, company_id, payload)


@router.post("/companies/{company_id}/subscriptions/{subscription_id}/cancel",
             response_model=SubscriptionOut)
def cancel_subscription(company_id: int, subscription_id: int, db: Session = Depends(get_db)):
    return subscription_service.cancel_subscription(db, company_id, subscription_id)
