"""Follow-ups = the collection chase log: calls, WhatsApp and visits made to a
party to recover dues, plus the next date we plan to follow up again.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import FollowupStatus, FollowupType
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company
    from .invoice import Invoice
    from .party import Party
    from .user import User


class Followup(Base, TimestampMixin):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    type: Mapped[FollowupType] = mapped_column(
        Enum(FollowupType), nullable=False, default=FollowupType.call
    )
    remarks: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    followup_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_followup_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[FollowupStatus] = mapped_column(
        Enum(FollowupStatus), nullable=False, default=FollowupStatus.done
    )

    company: Mapped["Company"] = relationship(back_populates="followups")
    party: Mapped["Party"] = relationship(back_populates="followups")
    invoice: Mapped[Optional["Invoice"]] = relationship()
    created_by: Mapped[Optional["User"]] = relationship()
