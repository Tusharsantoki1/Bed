"""Payment (collection ledger) schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from ..models.enums import PaymentMode
from .common import ORMModel


class PaymentCreate(BaseModel):
    party_id: int
    invoice_id: Optional[int] = None  # None = on-account (not tied to a bill)
    amount: float = Field(gt=0)
    payment_date: Optional[date] = None  # defaults to today
    mode: PaymentMode = PaymentMode.cash
    reference_no: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=500)


class PaymentOut(ORMModel):
    id: int
    company_id: int
    party_id: int
    invoice_id: Optional[int] = None
    amount: float
    payment_date: date
    mode: PaymentMode
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
