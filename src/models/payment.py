"""Payments = the collection ledger. Every amount received from a party is one
row here, so a bill can be paid in several instalments and we keep full history.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import PaymentMode
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company
    from .invoice import Invoice
    from .party import Party
    from .user import User


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional: a payment can be tied to a specific bill, or be "on account".
    invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode), nullable=False, default=PaymentMode.cash
    )
    reference_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="payments")
    party: Mapped["Party"] = relationship(back_populates="payments")
    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="payments")
    created_by: Mapped[Optional["User"]] = relationship()
