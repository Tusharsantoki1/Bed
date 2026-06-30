"""Invoice and invoice-item schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from ..models.enums import DocumentType, GstType, PaymentStatus
from .common import ORMModel
from .party import PartyOut


class InvoiceItemCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=300)
    years: Optional[str] = Field(default=None, max_length=50)
    quantity: float = Field(gt=0)
    rate: float = Field(ge=0)
    gst_rate: float = Field(default=0, ge=0, le=100)  # percent; ignored if GST is off


class InvoiceItemOut(ORMModel):
    id: int
    sr_no: int
    product_name: str
    years: Optional[str] = None
    quantity: float
    rate: float
    taxable_amount: float
    gst_rate: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    tax_amount: float
    net_amount: float


class InvoiceCreate(BaseModel):
    party_id: int
    invoice_date: Optional[date] = None  # defaults to today
    document_type: DocumentType = DocumentType.invoice
    copy_type: str = Field(default="Original", max_length=20)
    invoice_number: Optional[str] = Field(default=None, max_length=50)  # auto if omitted
    place_of_supply: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=1000)
    # None -> auto (apply GST when the company is GST-registered).
    # False -> force a non-GST bill. True -> force GST.
    apply_gst: Optional[bool] = None
    round_off: float = 0
    items: list[InvoiceItemCreate] = Field(min_length=1)


class InvoiceUpdate(BaseModel):
    """Replace the editable fields of an invoice (re-computes totals)."""

    party_id: Optional[int] = None
    invoice_date: Optional[date] = None
    document_type: Optional[DocumentType] = None
    copy_type: Optional[str] = Field(default=None, max_length=20)
    place_of_supply: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=1000)
    apply_gst: Optional[bool] = None
    round_off: Optional[float] = None
    items: Optional[list[InvoiceItemCreate]] = Field(default=None, min_length=1)


class PaymentUpdate(BaseModel):
    amount_paid: float = Field(ge=0)
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = Field(default=None, max_length=50)


class InvoiceSummary(ORMModel):
    id: int
    invoice_number: str
    invoice_date: date
    party_id: int
    grand_total: float
    amount_paid: float
    payment_status: PaymentStatus
    document_type: DocumentType


class InvoiceOut(ORMModel):
    id: int
    company_id: int
    party_id: int
    invoice_number: str
    invoice_date: date
    document_type: DocumentType
    copy_type: str
    place_of_supply: Optional[str] = None
    gst_type: GstType

    total_taxable: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_tax: float
    round_off: float
    grand_total: float
    amount_in_words: Optional[str] = None
    note: Optional[str] = None

    payment_status: PaymentStatus
    amount_paid: float
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None

    party: PartyOut
    items: list[InvoiceItemOut]
