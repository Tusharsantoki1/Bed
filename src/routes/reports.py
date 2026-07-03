"""Collection / receivables report routes — scoped to the caller's company."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.report import (
    AgingReport,
    BillReport,
    CollectionReport,
    CollectionSummary,
    DailyCollectionReport,
    NotificationList,
    OutstandingReport,
    PartyLedger,
    WebDashboard,
)
from ..services import party_service, report_service
from ..utils.deps import require_company_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard", response_model=WebDashboard)
def web_dashboard(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    """Aggregated data for the web dashboard (KPIs, overdue top-5, recent
    collections, aging summary, today's follow-ups) in one call."""
    return report_service.web_dashboard(db, current_user.company_id)


@router.get("/notifications", response_model=NotificationList)
def notifications(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    return report_service.notifications(db, current_user.company_id)


@router.get("/summary", response_model=CollectionSummary)
def summary(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    return report_service.collection_summary(db, current_user.company_id)


@router.get("/aging", response_model=AgingReport)
def aging(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    return report_service.aging_report(db, current_user.company_id)


@router.get("/outstanding", response_model=OutstandingReport)
def outstanding(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    """Party-wise outstanding."""
    return report_service.outstanding_report(db, current_user.company_id)


@router.get("/bills", response_model=BillReport)
def bills(
    overdue_only: bool = False,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    """Bill-wise outstanding (set overdue_only=true for the overdue report)."""
    return report_service.bill_report(db, current_user.company_id, overdue_only)


@router.get("/overdue", response_model=BillReport)
def overdue(current_user: User = Depends(require_company_user), db: Session = Depends(get_db)):
    return report_service.bill_report(db, current_user.company_id, overdue_only=True)


@router.get("/collection", response_model=CollectionReport)
def collection(
    from_date: date | None = None,
    to_date: date | None = None,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return report_service.collection_report(db, current_user.company_id, from_date, to_date)


@router.get("/daily-collection", response_model=DailyCollectionReport)
def daily_collection(
    from_date: date | None = None,
    to_date: date | None = None,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return report_service.daily_collection_report(
        db, current_user.company_id, from_date, to_date
    )


@router.get("/ledger/{party_id}", response_model=PartyLedger)
def party_ledger(
    party_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    party = party_service.get_party(db, current_user.company_id, party_id)
    return report_service.party_ledger(db, current_user.company_id, party)
