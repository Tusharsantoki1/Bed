"""Item (product/service catalog) schemas."""

from typing import Optional

from pydantic import BaseModel, Field

from .common import ORMModel


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    hsn_code: Optional[str] = Field(default=None, max_length=20)
    unit: Optional[str] = Field(default=None, max_length=20)
    default_rate: float = Field(default=0, ge=0)
    default_gst_rate: float = Field(default=0, ge=0, le=100)
    description: Optional[str] = Field(default=None, max_length=500)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=300)
    hsn_code: Optional[str] = Field(default=None, max_length=20)
    unit: Optional[str] = Field(default=None, max_length=20)
    default_rate: Optional[float] = Field(default=None, ge=0)
    default_gst_rate: Optional[float] = Field(default=None, ge=0, le=100)
    description: Optional[str] = Field(default=None, max_length=500)


class ItemOut(ORMModel):
    id: int
    company_id: int
    name: str
    hsn_code: Optional[str] = None
    unit: Optional[str] = None
    default_rate: float
    default_gst_rate: float
    description: Optional[str] = None
