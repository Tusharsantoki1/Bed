"""Subscription plans (catalog) and per-company subscriptions."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .enums import PlanCycle, SubscriptionStatus
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company


class Plan(Base, TimestampMixin):
    """A subscription plan defined by the super admin (the catalog)."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cycle: Mapped[PlanCycle] = mapped_column(Enum(PlanCycle), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base, TimestampMixin):
    """A subscription granted to a company by the super admin."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )

    cycle: Mapped[PlanCycle] = mapped_column(Enum(PlanCycle), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.active
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="subscriptions")
    plan: Mapped[Optional["Plan"]] = relationship(back_populates="subscriptions")
