"""User accounts: super admins and company users (admin / staff)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import UserRole
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.company_admin
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Null for super admins; set for company admins/staff.
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )

    company: Mapped[Optional["Company"]] = relationship(back_populates="users")
