"""Items = the products/services a company reuses on its invoices (a catalog).

Like parties, items are saved per company so they can be picked again when
creating a bill. Invoice line items store their own name/rate snapshot, so an
item can be edited or deleted without affecting past invoices.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company


class Item(Base, TimestampMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    hsn_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g. "Nos", "Year"
    default_rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    default_gst_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)  # percent
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="items")
