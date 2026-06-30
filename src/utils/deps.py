"""FastAPI dependencies: current user, role guards, and subscription guard."""

from __future__ import annotations

from datetime import date

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import SubscriptionStatus, UserRole
from ..models.subscription import Subscription
from ..models.user import User
from .security import decode_token

bearer_scheme = HTTPBearer(auto_error=True)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR

    if payload.get("type") != "access":
        raise _CREDENTIALS_ERROR

    user_id = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_ERROR

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    return user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def require_company_user(current_user: User = Depends(get_current_user)) -> User:
    """Any user attached to a company (admin or staff)."""
    if current_user.role not in (UserRole.company_admin, UserRole.company_staff):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company account required",
        )
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No company associated with this account",
        )
    return current_user


def require_company_admin(current_user: User = Depends(get_current_user)) -> User:
    """Company admins only (e.g. for the company admin panel / settings)."""
    if current_user.role != UserRole.company_admin or current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company admin access required",
        )
    return current_user


def require_active_subscription(
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
) -> User:
    """Block billing actions when the company has no active subscription."""
    today = date.today()
    stmt = (
        select(Subscription)
        .where(
            Subscription.company_id == current_user.company_id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.start_date <= today,
            Subscription.end_date >= today,
        )
        .limit(1)
    )
    active = db.execute(stmt).scalar_one_or_none()
    if active is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Your subscription is inactive or expired. Please contact the administrator.",
        )
    return current_user
