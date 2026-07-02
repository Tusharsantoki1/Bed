"""Party (customer) schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .common import ORMModel


class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    state_code: Optional[str] = Field(default=None, max_length=5)
    place_of_supply: Optional[str] = Field(default=None, max_length=100)
    gstin: Optional[str] = Field(default=None, max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    credit_days: int = Field(default=0, ge=0, le=3650)
    opening_balance: float = Field(default=0, ge=0)


class PartyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    state_code: Optional[str] = Field(default=None, max_length=5)
    place_of_supply: Optional[str] = Field(default=None, max_length=100)
    gstin: Optional[str] = Field(default=None, max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    credit_days: Optional[int] = Field(default=None, ge=0, le=3650)
    opening_balance: Optional[float] = Field(default=None, ge=0)


class PartyOut(ORMModel):
    id: int
    company_id: int
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    place_of_supply: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    credit_days: int = 0
    opening_balance: float = 0
