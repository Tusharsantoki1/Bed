"""User schemas."""

from typing import Optional

from pydantic import EmailStr, Field

from ..models.enums import UserRole
from .common import ORMModel


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    company_id: Optional[int] = None


class StaffCreate(ORMModel):
    """A company admin adds a staff user to their own company."""

    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=20)
    # Which company role to grant. Defaults to plain staff. company_admin and
    # super_admin are not assignable here.
    role: UserRole = UserRole.company_staff


class StaffUpdate(ORMModel):
    """A company admin edits one of their staff users."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
