"""Company profile, branding and staff management."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import UserRole
from ..models.user import User
from ..schemas.company import CompanyBrandingUpdate, CompanyUpdate
from ..schemas.user import StaffCreate
from ..utils.security import hash_password


def get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


def update_branding(db: Session, company: Company, data: CompanyBrandingUpdate) -> Company:
    # Only touch fields the client actually sent. Empty string clears an image.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value or None)
    db.commit()
    db.refresh(company)
    return company


def list_staff(db: Session, company_id: int) -> list[User]:
    return list(
        db.execute(
            select(User).where(User.company_id == company_id).order_by(User.id)
        ).scalars()
    )


def add_staff(db: Session, company_id: int, data: StaffCreate) -> User:
    existing = db.execute(
        select(User).where(User.email == data.email.lower())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    staff = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.company_staff,
        company_id=company_id,
        is_active=True,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def set_staff_active(db: Session, company_id: int, user_id: int, is_active: bool) -> User:
    staff = db.get(User, user_id)
    if staff is None or staff.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found")
    if staff.role == UserRole.company_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate the company admin",
        )
    staff.is_active = is_active
    db.commit()
    db.refresh(staff)
    return staff
