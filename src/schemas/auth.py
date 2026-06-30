"""Authentication-related schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .user import UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class CompanyRegisterRequest(BaseModel):
    """Self-service company sign-up: creates the company + its admin user."""

    # Company
    company_name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    state_code: Optional[str] = Field(default=None, max_length=5)
    phone: Optional[str] = Field(default=None, max_length=20)
    gstin: Optional[str] = Field(default=None, max_length=20)

    # Admin user
    admin_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
