"""Invoice routes: create/list/get/update/payment/delete + PDF download."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.enums import PaymentStatus
from ..models.user import User
from ..schemas.common import Message
from ..schemas.invoice import (
    InvoiceCreate,
    InvoiceOut,
    InvoiceSummary,
    InvoiceUpdate,
    OutstandingCreate,
    PaymentUpdate,
)
from ..services import company_service, invoice_service, pdf_service
from ..utils.deps import (
    require_active_subscription,
    require_company_editor,
    require_company_user,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceSummary])
def list_invoices(
    payment_status: PaymentStatus | None = None,
    party_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return invoice_service.list_invoices(
        db, current_user.company_id, payment_status, party_id, skip, limit
    )


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
):
    company = company_service.get_company(db, current_user.company_id)
    return invoice_service.create_invoice(db, company, payload, current_user.id)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    return invoice_service.get_invoice(db, current_user.company_id, invoice_id)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    company = company_service.get_company(db, current_user.company_id)
    return invoice_service.update_invoice(db, company, invoice_id, payload)


@router.post("/outstanding", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_outstanding(
    payload: OutstandingCreate,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    """Quick manual outstanding entry (a bill without GST line items)."""
    company = company_service.get_company(db, current_user.company_id)
    return invoice_service.create_outstanding(db, company, payload, current_user.id)


@router.post("/{invoice_id}/payment", response_model=InvoiceOut)
def record_payment(
    invoice_id: int,
    payload: PaymentUpdate,
    current_user: User = Depends(require_company_editor),
    db: Session = Depends(get_db),
):
    return invoice_service.record_payment(
        db, current_user.company_id, invoice_id, payload, current_user.id
    )


@router.delete("/{invoice_id}", response_model=Message)
def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    invoice_service.delete_invoice(db, current_user.company_id, invoice_id)
    return Message(detail="Invoice deleted")


@router.get("/{invoice_id}/pdf")
def invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    invoice = invoice_service.get_invoice(db, current_user.company_id, invoice_id)
    company = company_service.get_company(db, current_user.company_id)
    pdf_bytes = pdf_service.generate_invoice_pdf(invoice, company)
    safe_no = invoice.invoice_number.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="invoice-{safe_no}.pdf"'},
    )
