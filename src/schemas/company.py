"""Company schemas (profile, branding, bank details)."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .common import ORMModel


class CompanyUpdate(BaseModel):
    """Partial update of the company profile. All fields optional."""

    name: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    state_code: Optional[str] = Field(default=None, max_length=5)
    pincode: Optional[str] = Field(default=None, max_length=10)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    gstin: Optional[str] = Field(default=None, max_length=20)
    pan: Optional[str] = Field(default=None, max_length=20)

    bank_name: Optional[str] = Field(default=None, max_length=150)
    bank_account_no: Optional[str] = Field(default=None, max_length=50)
    bank_ifsc: Optional[str] = Field(default=None, max_length=20)
    upi_number: Optional[str] = Field(default=None, max_length=50)

    invoice_prefix: Optional[str] = Field(default=None, max_length=20)
    next_invoice_number: Optional[int] = Field(default=None, ge=1)
    default_note: Optional[str] = Field(default=None, max_length=1000)


class CompanyBrandingUpdate(BaseModel):
    """Upload/replace base64 images. Send only the ones you want to change.
    Pass an empty string to clear an existing image."""

    logo_base64: Optional[str] = None
    signature_base64: Optional[str] = None
    stamp_base64: Optional[str] = None
    payment_qr_base64: Optional[str] = None


class CompanySummary(ORMModel):
    """Lightweight company view (no heavy base64 image fields)."""

    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool


class CompanyOut(CompanySummary):
    """Full company profile, including branding images and bank details."""

    address: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None
    pan: Optional[str] = None

    logo_base64: Optional[str] = None
    signature_base64: Optional[str] = None
    stamp_base64: Optional[str] = None
    payment_qr_base64: Optional[str] = None

    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_ifsc: Optional[str] = None
    upi_number: Optional[str] = None

    invoice_prefix: str
    next_invoice_number: int
    default_note: Optional[str] = None
