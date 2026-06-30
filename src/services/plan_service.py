"""Subscription plan catalog (managed by the super admin)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.subscription import Plan
from ..schemas.plan import PlanCreate, PlanUpdate


def list_plans(db: Session, only_active: bool = False) -> list[Plan]:
    stmt = select(Plan).order_by(Plan.price)
    if only_active:
        stmt = stmt.where(Plan.is_active.is_(True))
    return list(db.execute(stmt).scalars())


def get_plan(db: Session, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def create_plan(db: Session, data: PlanCreate) -> Plan:
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, plan_id: int, data: PlanUpdate) -> Plan:
    plan = get_plan(db, plan_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan_id: int) -> None:
    plan = get_plan(db, plan_id)
    db.delete(plan)
    db.commit()
