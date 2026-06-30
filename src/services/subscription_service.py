"""Per-company subscription management."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import PLAN_CYCLE_DAYS, PlanCycle, SubscriptionStatus
from ..models.subscription import Plan, Subscription
from ..schemas.subscription import SubscriptionCreate


def get_current_subscription(db: Session, company_id: int) -> Optional[Subscription]:
    """The active subscription covering today, if any (latest end_date wins)."""
    today = date.today()
    stmt = (
        select(Subscription)
        .where(
            Subscription.company_id == company_id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.start_date <= today,
            Subscription.end_date >= today,
        )
        .order_by(Subscription.end_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_status_info(db: Session, company_id: int) -> dict:
    current = get_current_subscription(db, company_id)
    if current is None:
        return {"is_active": False, "current": None, "days_remaining": None}
    return {
        "is_active": True,
        "current": current,
        "days_remaining": (current.end_date - date.today()).days,
    }


def list_subscriptions(db: Session, company_id: int) -> list[Subscription]:
    return list(
        db.execute(
            select(Subscription)
            .where(Subscription.company_id == company_id)
            .order_by(Subscription.start_date.desc())
        ).scalars()
    )


def create_subscription(db: Session, company_id: int, data: SubscriptionCreate) -> Subscription:
    cycle: Optional[PlanCycle] = data.cycle
    amount = data.amount
    plan_id = data.plan_id

    if plan_id is not None:
        plan = db.get(Plan, plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        cycle = plan.cycle
        if amount is None:
            amount = float(plan.price)

    if cycle is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a plan_id or a cycle for the subscription",
        )

    start = data.start_date or date.today()
    end = start + timedelta(days=PLAN_CYCLE_DAYS[cycle])

    subscription = Subscription(
        company_id=company_id,
        plan_id=plan_id,
        cycle=cycle,
        amount=amount or 0,
        start_date=start,
        end_date=end,
        status=SubscriptionStatus.active,
        notes=data.notes,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def cancel_subscription(db: Session, company_id: int, subscription_id: int) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None or sub.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    sub.status = SubscriptionStatus.cancelled
    db.commit()
    db.refresh(sub)
    return sub
