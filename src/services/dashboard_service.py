"""Aggregations for the company admin panel and the super admin panel."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import FollowupStatus, PaymentStatus, SubscriptionStatus
from ..models.followup import Followup
from ..models.invoice import Invoice
from ..models.party import Party
from ..models.payment import Payment
from ..models.subscription import Subscription


def company_dashboard(db: Session, company_id: int) -> dict:
    total_invoices = db.execute(
        select(func.count(Invoice.id)).where(Invoice.company_id == company_id)
    ).scalar_one()
    total_billed = db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total), 0)).where(
            Invoice.company_id == company_id
        )
    ).scalar_one()
    # Received = every payment collected (bill-linked + on-account).
    total_received = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id
        )
    ).scalar_one()
    total_opening = db.execute(
        select(func.coalesce(func.sum(Party.opening_balance), 0)).where(
            Party.company_id == company_id
        )
    ).scalar_one()

    def count_status(s: PaymentStatus) -> int:
        return db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.company_id == company_id, Invoice.payment_status == s
            )
        ).scalar_one()

    total_parties = db.execute(
        select(func.count(Party.id)).where(Party.company_id == company_id)
    ).scalar_one()

    today = date.today()
    month_start = today.replace(day=1)

    overdue = db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total - Invoice.amount_paid), 0)).where(
            Invoice.company_id == company_id,
            Invoice.due_date.is_not(None),
            Invoice.due_date < today,
            Invoice.payment_status != PaymentStatus.paid,
        )
    ).scalar_one()

    today_due = db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total - Invoice.amount_paid), 0)).where(
            Invoice.company_id == company_id,
            Invoice.due_date == today,
            Invoice.payment_status != PaymentStatus.paid,
        )
    ).scalar_one()

    def collected(since=None) -> float:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id
        )
        stmt = stmt.where(Payment.payment_date == today) if since is None else stmt.where(
            Payment.payment_date >= since
        )
        return float(db.execute(stmt).scalar_one())

    today_followups = db.execute(
        select(func.count(Followup.id)).where(
            Followup.company_id == company_id, Followup.next_followup_date == today
        )
    ).scalar_one()
    pending_followups = db.execute(
        select(func.count(Followup.id)).where(
            Followup.company_id == company_id, Followup.status == FollowupStatus.pending
        )
    ).scalar_one()

    total_billed = float(total_billed)
    total_received = float(total_received)
    total_opening = float(total_opening)
    return {
        "total_invoices": total_invoices,
        "total_billed": total_billed,
        "total_received": total_received,
        "total_outstanding": round(total_opening + total_billed - total_received, 2),
        "paid_count": count_status(PaymentStatus.paid),
        "partial_count": count_status(PaymentStatus.partial),
        "pending_count": count_status(PaymentStatus.pending),
        "total_parties": total_parties,
        "total_overdue": round(float(overdue), 2),
        "today_due": round(float(today_due), 2),
        "today_collection": collected(),
        "month_collection": collected(month_start),
        "today_followups": today_followups,
        "pending_followups": pending_followups,
    }


def super_admin_dashboard(db: Session) -> dict:
    today = date.today()

    total_companies = db.execute(select(func.count(Company.id))).scalar_one()
    active_companies = db.execute(
        select(func.count(Company.id)).where(Company.is_active.is_(True))
    ).scalar_one()

    active_subscriptions = db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.active,
            Subscription.start_date <= today,
            Subscription.end_date >= today,
        )
    ).scalar_one()
    expired_subscriptions = db.execute(
        select(func.count(Subscription.id)).where(Subscription.end_date < today)
    ).scalar_one()
    revenue = db.execute(
        select(func.coalesce(func.sum(Subscription.amount), 0))
    ).scalar_one()
    total_invoices = db.execute(select(func.count(Invoice.id))).scalar_one()

    return {
        "total_companies": total_companies,
        "active_companies": active_companies,
        "inactive_companies": total_companies - active_companies,
        "active_subscriptions": active_subscriptions,
        "expired_subscriptions": expired_subscriptions,
        "total_subscription_revenue": float(revenue),
        "total_invoices": total_invoices,
    }
