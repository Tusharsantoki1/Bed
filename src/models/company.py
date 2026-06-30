"""Company (tenant) profile, branding, bank and invoice-numbering settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .invoice import Invoice
    from .party import Party
    from .subscription import Subscription
    from .user import User


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # GST state code, e.g. "24" for Gujarat. Drives CGST/SGST vs IGST.
    state_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # If set, the company is GST-registered and invoices can carry GST.
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Branding & artefacts (stored as base64 data — image bytes).
    logo_base64: Mapped[Optional[str]] = mapped_column(Text(length=16_000_000), nullable=True)
    signature_base64: Mapped[Optional[str]] = mapped_column(Text(length=16_000_000), nullable=True)
    stamp_base64: Mapped[Optional[str]] = mapped_column(Text(length=16_000_000), nullable=True)
    payment_qr_base64: Mapped[Optional[str]] = mapped_column(Text(length=16_000_000), nullable=True)

    # Bank / payment details printed on invoices.
    bank_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    bank_account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_ifsc: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    upi_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # G-Pay/UPI number

    # Invoice numbering: prefix + running counter (e.g. "EH/" + 46 -> "EH/46").
    invoice_prefix: Mapped[str] = mapped_column(String(20), nullable=False, default="INV/")
    next_invoice_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    default_note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    parties: Mapped[list["Party"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
