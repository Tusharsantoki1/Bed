"""Aggregations for the company admin panel and the super admin panel."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import PaymentStatus, SubscriptionStatus
from ..models.invoice import Invoice
from ..models.party import Party
from ..models.subscription import Subscription


def company_dashboard(db: Session, company_id: int) -> dict:
    base = select(
        func.count(Invoice.id),
        func.coalesce(func.sum(Invoice.grand_total), 0),
        func.coalesce(func.sum(Invoice.amount_paid), 0),
    ).where(Invoice.company_id == company_id)
    total_invoices, total_billed, total_received = db.execute(base).one()

    def count_status(s: PaymentStatus) -> int:
        return db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.company_id == company_id, Invoice.payment_status == s
            )
        ).scalar_one()

    total_parties = db.execute(
        select(func.count(Party.id)).where(Party.company_id == company_id)
    ).scalar_one()

    total_billed = float(total_billed)
    total_received = float(total_received)
    return {
        "total_invoices": total_invoices,
        "total_billed": total_billed,
        "total_received": total_received,
        "total_outstanding": round(total_billed - total_received, 2),
        "paid_count": count_status(PaymentStatus.paid),
        "partial_count": count_status(PaymentStatus.partial),
        "pending_count": count_status(PaymentStatus.pending),
        "total_parties": total_parties,
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
