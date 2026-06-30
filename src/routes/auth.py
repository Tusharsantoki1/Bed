"""Authentication routes: register a company, login, refresh, current user."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.auth import (
    AccessToken,
    CompanyRegisterRequest,
    LoginRequest,
    RefreshRequest,
    Token,
)
from ..schemas.user import UserOut
from ..services import auth_service
from ..utils.deps import get_current_user
from ..utils.security import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> Token:
    return Token(
        access_token=create_access_token(user.id, user.role.value, user.company_id),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/register-company", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_company(payload: CompanyRegisterRequest, db: Session = Depends(get_db)):
    """Self-service sign up: creates the company and its admin account."""
    user = auth_service.register_company(db, payload)
    return _tokens_for(user)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    return _tokens_for(user)


@router.post("/refresh", response_model=AccessToken)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return AccessToken(access_token=create_access_token(user.id, user.role.value, user.company_id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
