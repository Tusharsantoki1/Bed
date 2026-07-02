"""Collection / receivables reports: aging, outstanding, ledger, collection,
daily collection, overdue and the one-page summary."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.followup import Followup
from ..models.enums import FollowupStatus
from ..models.invoice import Invoice
from ..models.party import Party
from ..models.payment import Payment
from ..schemas.report import (
    AgingBuckets,
    AgingReport,
    BillReport,
    BillRow,
    CollectionReport,
    CollectionRow,
    CollectionSummary,
    DailyCollectionReport,
    DailyCollectionRow,
    LedgerEntry,
    OutstandingPartyRow,
    OutstandingReport,
    PartyAgingRow,
    PartyLedger,
)
from ..utils.numbers import money


# --- shared helpers ------------------------------------------------------

def _f(value) -> float:
    return float(money(value))


def _overdue_days(due: Optional[date], today: date) -> int:
    if due is None or due >= today:
        return 0
    return (today - due).days


def _bucket_key(due: Optional[date], today: date) -> str:
    if due is None or due >= today:
        return "not_due"
    d = (today - due).days
    if d <= 30:
        return "d1_30"
    if d <= 60:
        return "d31_60"
    if d <= 90:
        return "d61_90"
    if d <= 120:
        return "d91_120"
    return "d120_plus"


def _open_invoices(db: Session, company_id: int) -> list[Invoice]:
    """Invoices with a positive outstanding balance, party pre-loaded."""
    rows = db.execute(
        select(Invoice)
        .where(Invoice.company_id == company_id)
        .options(selectinload(Invoice.party))
        .order_by(Invoice.invoice_date, Invoice.id)
    ).scalars().all()
    return [inv for inv in rows if money(inv.grand_total) - money(inv.amount_paid) > 0]


def party_outstanding(db: Session, company_id: int, party_id: int) -> float:
    """opening_balance + billed - paid for one party."""
    party = db.get(Party, party_id)
    if party is None or party.company_id != company_id:
        return 0.0
    billed = db.execute(
        select(func.coalesce(func.sum(Invoice.grand_total), 0)).where(
            Invoice.company_id == company_id, Invoice.party_id == party_id
        )
    ).scalar_one()
    paid = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id, Payment.party_id == party_id
        )
    ).scalar_one()
    return _f(Decimal(str(party.opening_balance)) + billed - paid)


# --- Aging ---------------------------------------------------------------

def aging_report(db: Session, company_id: int) -> AgingReport:
    today = date.today()
    per_party: dict[int, dict] = {}
    totals = {k: Decimal("0") for k in ("not_due", "d1_30", "d31_60", "d61_90", "d91_120", "d120_plus")}

    for inv in _open_invoices(db, company_id):
        balance = money(inv.grand_total) - money(inv.amount_paid)
        key = _bucket_key(inv.due_date, today)
        totals[key] += balance
        row = per_party.setdefault(
            inv.party_id,
            {"name": inv.party.name, **{k: Decimal("0") for k in totals}},
        )
        row[key] += balance

    def buckets(d: dict) -> dict:
        total = sum(d[k] for k in totals)
        return {**{k: _f(d[k]) for k in totals}, "total": _f(total)}

    parties = [
        PartyAgingRow(party_id=pid, party_name=d["name"], **buckets(d))
        for pid, d in sorted(per_party.items(), key=lambda kv: -sum(kv[1][k] for k in totals))
    ]
    return AgingReport(totals=AgingBuckets(**buckets(totals)), parties=parties)


# --- Outstanding (party-wise) --------------------------------------------

def outstanding_report(db: Session, company_id: int) -> OutstandingReport:
    """Party-wise outstanding = opening + billed - all payments (incl. on-account)."""
    today = date.today()
    parties: dict[int, dict] = {}

    def row(party: Party) -> dict:
        return parties.setdefault(
            party.id,
            {
                "party": party,
                "billed": Decimal("0"),
                "paid": Decimal("0"),
                "opening": Decimal(str(party.opening_balance)),
                "overdue": Decimal("0"),
                "oldest": None,
            },
        )

    invoices = db.execute(
        select(Invoice)
        .where(Invoice.company_id == company_id)
        .options(selectinload(Invoice.party))
    ).scalars().all()
    for inv in invoices:
        r = row(inv.party)
        r["billed"] += money(inv.grand_total)
        balance = money(inv.grand_total) - money(inv.amount_paid)
        if balance > 0 and _overdue_days(inv.due_date, today) > 0:
            r["overdue"] += balance
            if inv.due_date and (r["oldest"] is None or inv.due_date < r["oldest"]):
                r["oldest"] = inv.due_date

    payments = db.execute(
        select(Payment)
        .where(Payment.company_id == company_id)
        .options(selectinload(Payment.party))
    ).scalars().all()
    for pay in payments:
        row(pay.party)["paid"] += money(pay.amount)

    # Parties with an opening balance but no invoices/payments yet.
    for party in db.execute(
        select(Party).where(Party.company_id == company_id, Party.opening_balance > 0)
    ).scalars():
        row(party)

    rows: list[OutstandingPartyRow] = []
    for pid, d in parties.items():
        outstanding = d["opening"] + d["billed"] - d["paid"]
        if outstanding <= 0:
            continue
        rows.append(
            OutstandingPartyRow(
                party_id=pid,
                party_name=d["party"].name,
                phone=d["party"].phone,
                city=d["party"].city,
                outstanding=_f(outstanding),
                overdue=_f(min(d["overdue"], outstanding)),
                oldest_due_date=d["oldest"],
            )
        )
    rows.sort(key=lambda r: r.outstanding, reverse=True)
    return OutstandingReport(
        total_outstanding=_f(sum((Decimal(str(r.outstanding)) for r in rows), Decimal("0"))),
        total_overdue=_f(sum((Decimal(str(r.overdue)) for r in rows), Decimal("0"))),
        parties=rows,
    )


# --- Bill-wise outstanding / overdue -------------------------------------

def bill_report(db: Session, company_id: int, overdue_only: bool = False) -> BillReport:
    today = date.today()
    rows: list[BillRow] = []
    total_balance = Decimal("0")
    total_overdue = Decimal("0")

    for inv in _open_invoices(db, company_id):
        balance = money(inv.grand_total) - money(inv.amount_paid)
        od = _overdue_days(inv.due_date, today)
        if overdue_only and od == 0:
            continue
        total_balance += balance
        if od > 0:
            total_overdue += balance
        rows.append(
            BillRow(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                party_id=inv.party_id,
                party_name=inv.party.name,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                grand_total=_f(inv.grand_total),
                amount_paid=_f(inv.amount_paid),
                balance=_f(balance),
                overdue_days=od,
            )
        )
    rows.sort(key=lambda r: (r.overdue_days, r.balance), reverse=True)
    return BillReport(
        total_balance=_f(total_balance), total_overdue=_f(total_overdue), bills=rows
    )


# --- Party ledger --------------------------------------------------------

def party_ledger(db: Session, company_id: int, party: Party) -> PartyLedger:
    opening = Decimal(str(party.opening_balance))

    invoices = db.execute(
        select(Invoice).where(
            Invoice.company_id == company_id, Invoice.party_id == party.id
        )
    ).scalars().all()
    payments = db.execute(
        select(Payment).where(
            Payment.company_id == company_id, Payment.party_id == party.id
        )
    ).scalars().all()

    total_billed = sum((money(i.grand_total) for i in invoices), Decimal("0"))
    total_paid = sum((money(p.amount) for p in payments), Decimal("0"))

    tx: list[tuple] = []
    for i in invoices:
        tx.append((i.invoice_date, 0, "bill", i.invoice_number, f"Bill {i.invoice_number}", money(i.grand_total), Decimal("0")))
    for p in payments:
        ref = p.reference_no or p.mode.value
        tx.append((p.payment_date, 1, "payment", ref, f"Payment ({p.mode.value})", Decimal("0"), money(p.amount)))
    tx.sort(key=lambda t: (t[0], t[1]))

    ledger: list[LedgerEntry] = []
    running = opening
    if opening != 0:
        ledger.append(LedgerEntry(
            date=(invoices[0].invoice_date if invoices else date.today()),
            kind="opening", ref=None, particulars="Opening balance",
            debit=_f(opening), credit=0, balance=_f(running),
        ))
    for d, _order, kind, ref, particulars, debit, credit in tx:
        running += debit - credit
        ledger.append(LedgerEntry(
            date=d, kind=kind, ref=ref, particulars=particulars,
            debit=_f(debit), credit=_f(credit), balance=_f(running),
        ))

    return PartyLedger(
        party_id=party.id,
        party_name=party.name,
        opening_balance=_f(opening),
        total_billed=_f(total_billed),
        total_paid=_f(total_paid),
        outstanding=_f(opening + total_billed - total_paid),
        entries=ledger,
    )


# --- Collection ----------------------------------------------------------

def _collection_rows(
    db: Session, company_id: int, from_date: Optional[date], to_date: Optional[date]
) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.company_id == company_id)
        .options(selectinload(Payment.party), selectinload(Payment.invoice))
    )
    if from_date is not None:
        stmt = stmt.where(Payment.payment_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Payment.payment_date <= to_date)
    stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())
    return list(db.execute(stmt).scalars())


def collection_report(
    db: Session, company_id: int, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> CollectionReport:
    payments = _collection_rows(db, company_id, from_date, to_date)
    rows = [
        CollectionRow(
            payment_id=p.id,
            payment_date=p.payment_date,
            party_id=p.party_id,
            party_name=p.party.name if p.party else "",
            amount=_f(p.amount),
            mode=p.mode,
            reference_no=p.reference_no,
            invoice_number=p.invoice.invoice_number if p.invoice else None,
        )
        for p in payments
    ]
    return CollectionReport(
        from_date=from_date,
        to_date=to_date,
        total_collected=_f(sum((money(p.amount) for p in payments), Decimal("0"))),
        count=len(rows),
        payments=rows,
    )


def daily_collection_report(
    db: Session, company_id: int, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> DailyCollectionReport:
    payments = _collection_rows(db, company_id, from_date, to_date)
    per_day_amt: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    per_day_cnt: dict[date, int] = defaultdict(int)
    for p in payments:
        per_day_amt[p.payment_date] += money(p.amount)
        per_day_cnt[p.payment_date] += 1
    days = [
        DailyCollectionRow(day=d, amount=_f(per_day_amt[d]), count=per_day_cnt[d])
        for d in sorted(per_day_amt, reverse=True)
    ]
    return DailyCollectionReport(
        from_date=from_date,
        to_date=to_date,
        total=_f(sum(per_day_amt.values(), Decimal("0"))),
        days=days,
    )


# --- Summary (one-page) --------------------------------------------------

def collection_summary(db: Session, company_id: int) -> CollectionSummary:
    today = date.today()
    month_start = today.replace(day=1)

    outstanding = outstanding_report(db, company_id)

    today_collection = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id, Payment.payment_date == today
        )
    ).scalar_one()
    month_collection = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.company_id == company_id, Payment.payment_date >= month_start
        )
    ).scalar_one()

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
    total_parties = db.execute(
        select(func.count(Party.id)).where(Party.company_id == company_id)
    ).scalar_one()

    from . import followup_service  # local import avoids a circular import
    recent = collection_report(db, company_id).payments[:10]
    upcoming = [
        followup_service.to_out(f)
        for f in followup_service.due_followups(db, company_id)[:10]
    ]

    return CollectionSummary(
        total_outstanding=outstanding.total_outstanding,
        total_overdue=outstanding.total_overdue,
        today_collection=_f(today_collection),
        month_collection=_f(month_collection),
        today_followups=today_followups,
        pending_followups=pending_followups,
        total_parties=total_parties,
        recent_payments=recent,
        upcoming_followups=upcoming,
    )
