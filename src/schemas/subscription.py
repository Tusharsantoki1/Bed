"""Subscription schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from ..models.enums import PlanCycle, SubscriptionStatus
from .common import ORMModel


class SubscriptionCreate(BaseModel):
    """Super admin grants a subscription to a company.

    Either provide a plan_id (cycle/amount copied from the plan) or specify
    cycle + amount directly. start_date defaults to today.
    """

    plan_id: Optional[int] = None
    cycle: Optional[PlanCycle] = None
    amount: Optional[float] = Field(default=None, ge=0)
    start_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class SubscriptionOut(ORMModel):
    id: int
    company_id: int
    plan_id: Optional[int] = None
    cycle: PlanCycle
    amount: float
    start_date: date
    end_date: date
    status: SubscriptionStatus
    notes: Optional[str] = None


class SubscriptionStatusInfo(BaseModel):
    """A company's current subscription status (for the company app)."""

    is_active: bool
    current: Optional[SubscriptionOut] = None
    days_remaining: Optional[int] = None
