"""Company schemas (profile, branding, bank details)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .common import ORMModel, validate_pincode


class CompanyUpdate(BaseModel):
    """Partial update of the company profile by the company admin.

    The company *name*, *invoice prefix* and *invoice numbering* are
    deliberately absent: they are locked to the company's identity and can
    only be changed by a super admin (see ``SuperAdminCompanyUpdate``).
    """

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

    default_note: Optional[str] = Field(default=None, max_length=1000)

    # Collection settings.
    default_credit_days: Optional[int] = Field(default=None, ge=0, le=3650)
    financial_year_start: Optional[date] = None
    financial_year_end: Optional[date] = None

    @field_validator("pincode")
    @classmethod
    def _check_pincode(cls, v: Optional[str]) -> Optional[str]:
        return validate_pincode(v)


class SuperAdminCompanyUpdate(BaseModel):
    """Identity fields only a super admin may change."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    invoice_prefix: Optional[str] = Field(default=None, min_length=1, max_length=20)
    next_invoice_number: Optional[int] = Field(default=None, ge=1)


class PasswordReset(BaseModel):
    """Super admin sets a new login password for a company's admin user."""

    new_password: str = Field(min_length=8, max_length=128)


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

    default_credit_days: int = 0
    financial_year_start: Optional[date] = None
    financial_year_end: Optional[date] = None
