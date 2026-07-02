"""Parties = the customers/buyers a company raises invoices for."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company
    from .followup import Followup
    from .invoice import Invoice
    from .payment import Payment


class Party(Base, TimestampMixin):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    # e.g. "24-Gujarat"
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Collection / receivables fields.
    credit_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opening_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    company: Mapped["Company"] = relationship(back_populates="parties")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="party")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="party", cascade="all, delete-orphan"
    )
    followups: Mapped[list["Followup"]] = relationship(
        back_populates="party", cascade="all, delete-orphan"
    )
