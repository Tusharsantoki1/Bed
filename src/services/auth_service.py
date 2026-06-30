"""Authentication & registration business logic."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import UserRole
from ..models.user import User
from ..schemas.auth import CompanyRegisterRequest
from ..utils.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.execute(
        select(User).where(User.email == email.lower())
    ).scalar_one_or_none()


def register_company(db: Session, data: CompanyRegisterRequest) -> User:
    """Create a company and its first admin user in one transaction."""
    if get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    company = Company(
        name=data.company_name,
        address=data.address,
        city=data.city,
        state=data.state,
        state_code=data.state_code,
        phone=data.phone,
        gstin=data.gstin,
        invoice_prefix="INV/",
        next_invoice_number=1,
    )
    db.add(company)
    db.flush()  # assign company.id

    admin = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.admin_name,
        phone=data.phone,
        role=UserRole.company_admin,
        company_id=company.id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def authenticate(db: Session, email: str, password: str) -> User:
    """Return the user on success; raise 401 otherwise (generic message)."""
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled",
        )
    return user
