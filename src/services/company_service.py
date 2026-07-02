"""Company profile, branding and staff management."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import UserRole
from ..models.user import User
from ..schemas.company import (
    CompanyBrandingUpdate,
    CompanyUpdate,
    SuperAdminCompanyUpdate,
)
from ..schemas.user import StaffCreate, StaffUpdate
from ..utils.security import hash_password


def default_invoice_prefix(name: str) -> str:
    """Derive the default invoice prefix from the company name: the first two
    alphanumeric characters, upper-cased, followed by '/'.

    e.g. "E&H Fincorp Associates" -> "EH/". Falls back to "INV/" when the name
    has no usable characters.
    """
    code = "".join(ch for ch in name if ch.isalnum())[:2].upper()
    return f"{code}/" if code else "INV/"


def get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def update_company(db: Session, company: Company, data: CompanyUpdate) -> Company:
    """Company-admin self-service update (identity fields excluded by schema)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


def admin_update_company(
    db: Session, company: Company, data: SuperAdminCompanyUpdate
) -> Company:
    """Super-admin-only update of the company's locked identity fields
    (name, invoice prefix and invoice numbering)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company_id: int) -> None:
    """Super admin removes a company and everything under it (users, parties,
    items, invoices, subscriptions cascade)."""
    company = get_company(db, company_id)
    db.delete(company)
    db.commit()


def reset_company_admin_password(db: Session, company_id: int, new_password: str) -> User:
    """Super admin sets a new login password for the company's admin user."""
    get_company(db, company_id)  # 404 if the company doesn't exist
    admin = db.execute(
        select(User)
        .where(User.company_id == company_id, User.role == UserRole.company_admin)
        .order_by(User.id)
    ).scalars().first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This company has no admin account",
        )
    admin.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(admin)
    return admin


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


# Roles a company admin may assign to a staff user (not admin/super admin).
_ASSIGNABLE_STAFF_ROLES = (
    UserRole.company_staff,
    UserRole.collection_executive,
    UserRole.viewer,
)


def _validate_staff_role(role: UserRole) -> UserRole:
    if role not in _ASSIGNABLE_STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: staff, collection executive, viewer",
        )
    return role


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
        role=_validate_staff_role(data.role),
        company_id=company_id,
        is_active=True,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def update_staff(db: Session, company_id: int, user_id: int, data: StaffUpdate) -> User:
    staff = db.get(User, user_id)
    if staff is None or staff.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found")
    if staff.role == UserRole.company_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The company admin account cannot be edited here",
        )
    fields = data.model_dump(exclude_unset=True)
    if "role" in fields and fields["role"] is not None:
        fields["role"] = _validate_staff_role(fields["role"])
    for field, value in fields.items():
        setattr(staff, field, value)
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
