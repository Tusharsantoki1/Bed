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
