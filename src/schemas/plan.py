"""Subscription plan (catalog) schemas."""

from typing import Optional

from pydantic import BaseModel, Field

from ..models.enums import PlanCycle
from .common import ORMModel


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    cycle: PlanCycle
    price: float = Field(ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    cycle: Optional[PlanCycle] = None
    price: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class PlanOut(ORMModel):
    id: int
    name: str
    cycle: PlanCycle
    price: float
    description: Optional[str] = None
    is_active: bool
