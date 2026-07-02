"""Payment (collection ledger) service.

Payments are the source of truth for how much a bill has been paid. Each row is
one receipt; an invoice's cached ``amount_paid`` is recomputed as the sum of its
linked payments whenever a payment is added or removed.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.enums import PaymentStatus
from ..models.invoice import Invoice
from ..models.payment import Payment
from ..schemas.payment import PaymentCreate
from ..utils.numbers import money
from . import party_service


def _status(paid: Decimal, total: Decimal) -> PaymentStatus:
    if paid <= 0:
        return PaymentStatus.pending
    if paid >= total:
        return PaymentStatus.paid
    return PaymentStatus.partial


def recompute_invoice(db: Session, invoice: Invoice) -> None:
    """Refresh an invoice's cached paid amount / status from its payments."""
    paid = money(
        db.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice.id
            )
        ).scalar_one()
    )
    invoice.amount_paid = paid
    invoice.payment_status = _status(paid, money(invoice.grand_total))
    latest = db.execute(
        select(Payment)
        .where(Payment.invoice_id == invoice.id)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    invoice.payment_date = latest.payment_date if latest else None
    invoice.payment_mode = latest.mode.value if latest else None


def get_payment(db: Session, company_id: int, payment_id: int) -> Payment:
    p = db.get(Payment, payment_id)
    if p is None or p.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return p


def list_payments(
    db: Session, company_id: int, party_id: Optional[int] = None,
    invoice_id: Optional[int] = None, skip: int = 0, limit: int = 100,
) -> list[Payment]:
    stmt = select(Payment).where(Payment.company_id == company_id)
    if party_id is not None:
        stmt = stmt.where(Payment.party_id == party_id)
    if invoice_id is not None:
        stmt = stmt.where(Payment.invoice_id == invoice_id)
    stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


def create_payment(
    db: Session, company_id: int, data: PaymentCreate, created_by_id: Optional[int]
) -> Payment:
    party = party_service.get_party(db, company_id, data.party_id)  # 404 if not ours

    invoice = None
    if data.invoice_id is not None:
        invoice = db.get(Invoice, data.invoice_id)
        if invoice is None or invoice.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        if invoice.party_id != party.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This bill does not belong to the selected party",
            )
        balance = money(invoice.grand_total) - money(invoice.amount_paid)
        if money(data.amount) > balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment exceeds the bill's outstanding balance",
            )

    payment = Payment(
        company_id=company_id,
        party_id=party.id,
        invoice_id=invoice.id if invoice else None,
        created_by_id=created_by_id,
        amount=money(data.amount),
        payment_date=data.payment_date or date.today(),
        mode=data.mode,
        reference_no=data.reference_no,
        remarks=data.remarks,
    )
    db.add(payment)
    if invoice is not None:
        db.flush()
        recompute_invoice(db, invoice)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, company_id: int, payment_id: int) -> None:
    payment = get_payment(db, company_id, payment_id)
    invoice_id = payment.invoice_id
    db.delete(payment)
    db.flush()
    if invoice_id is not None:
        invoice = db.get(Invoice, invoice_id)
        if invoice is not None:
            recompute_invoice(db, invoice)
    db.commit()
