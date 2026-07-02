"""Invoices and their line items."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import DocumentType, GstType, PaymentStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company
    from .party import Party
    from .payment import Payment
    from .user import User


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    __table_args__ = (
        # Invoice numbers are unique within a single company.
        UniqueConstraint("company_id", "invoice_number", name="uq_company_invoice_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_id: Mapped[int] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    # When payment is due (drives overdue / aging). Auto = invoice_date + credit_days.
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False, default=DocumentType.invoice
    )
    copy_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Original")
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    gst_type: Mapped[GstType] = mapped_column(
        Enum(GstType), nullable=False, default=GstType.none
    )

    # Money (all computed on the server from the line items).
    total_taxable: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_cgst: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_sgst: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_igst: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    round_off: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    grand_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount_in_words: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Payment tracking (for the company admin panel).
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="invoices")
    party: Mapped["Party"] = relationship(back_populates="invoices")
    created_by: Mapped[Optional["User"]] = relationship()
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.sr_no",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice",
        order_by="Payment.payment_date",
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    sr_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    years: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. "2024-2025"
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    taxable_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gst_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)  # percent
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")
