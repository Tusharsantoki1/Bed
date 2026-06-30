"""Invoice creation, computation, listing, payments and deletion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.company import Company
from ..models.enums import GstType, PaymentStatus
from ..models.invoice import Invoice, InvoiceItem
from ..models.party import Party
from ..schemas.invoice import (
    InvoiceCreate,
    InvoiceItemCreate,
    InvoiceUpdate,
    PaymentUpdate,
)
from ..utils.numbers import amount_in_words, money
from . import party_service


# --- Helpers ---------------------------------------------------------------

def _resolve_gst(company: Company, party: Party, apply_gst: Optional[bool]) -> GstType:
    """Decide whether/how GST applies to this invoice."""
    if apply_gst is False:
        return GstType.none
    company_registered = bool(company.gstin)
    if apply_gst is True and not company_registered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company has no GSTIN set; cannot create a GST invoice.",
        )
    if apply_gst is None and not company_registered:
        return GstType.none

    # GST applies — intra-state (CGST+SGST) vs inter-state (IGST).
    if company.state_code and party.state_code and company.state_code != party.state_code:
        return GstType.inter_state
    return GstType.intra_state  # default when same state or codes unknown


def _build_items(
    items: Iterable[InvoiceItemCreate], gst_type: GstType
) -> tuple[list[InvoiceItem], dict[str, Decimal]]:
    """Build InvoiceItem rows and accumulate invoice totals."""
    rows: list[InvoiceItem] = []
    totals = {
        "taxable": Decimal("0"),
        "cgst": Decimal("0"),
        "sgst": Decimal("0"),
        "igst": Decimal("0"),
        "tax": Decimal("0"),
        "net": Decimal("0"),
    }

    for idx, item in enumerate(items, start=1):
        taxable = money(Decimal(str(item.quantity)) * Decimal(str(item.rate)))
        gst_rate = Decimal(str(item.gst_rate)) if gst_type != GstType.none else Decimal("0")

        cgst = sgst = igst = Decimal("0")
        if gst_rate > 0:
            tax = money(taxable * gst_rate / Decimal("100"))
            if gst_type == GstType.inter_state:
                igst = tax
            else:  # intra-state: split evenly
                cgst = money(tax / Decimal("2"))
                sgst = tax - cgst
        tax_amount = cgst + sgst + igst
        net = taxable + tax_amount

        rows.append(
            InvoiceItem(
                sr_no=idx,
                product_name=item.product_name,
                years=item.years,
                quantity=money(item.quantity),
                rate=money(item.rate),
                taxable_amount=taxable,
                gst_rate=gst_rate,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                tax_amount=tax_amount,
                net_amount=net,
            )
        )
        totals["taxable"] += taxable
        totals["cgst"] += cgst
        totals["sgst"] += sgst
        totals["igst"] += igst
        totals["tax"] += tax_amount
        totals["net"] += net

    return rows, totals


def _next_invoice_number(db: Session, company: Company) -> str:
    """Generate the next free invoice number for the company and bump the counter."""
    while True:
        number = f"{company.invoice_prefix}{company.next_invoice_number}"
        company.next_invoice_number += 1
        exists = db.execute(
            select(Invoice.id).where(
                Invoice.company_id == company.id, Invoice.invoice_number == number
            )
        ).first()
        if not exists:
            return number


def _payment_status(amount_paid: Decimal, grand_total: Decimal) -> PaymentStatus:
    if amount_paid <= 0:
        return PaymentStatus.pending
    if amount_paid >= grand_total:
        return PaymentStatus.paid
    return PaymentStatus.partial


# --- Public API ------------------------------------------------------------

def get_invoice(db: Session, company_id: int, invoice_id: int) -> Invoice:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.company_id == company_id)
        .options(selectinload(Invoice.items), selectinload(Invoice.party))
    )
    invoice = db.execute(stmt).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def list_invoices(
    db: Session,
    company_id: int,
    payment_status: PaymentStatus | None = None,
    party_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Invoice]:
    stmt = select(Invoice).where(Invoice.company_id == company_id)
    if payment_status is not None:
        stmt = stmt.where(Invoice.payment_status == payment_status)
    if party_id is not None:
        stmt = stmt.where(Invoice.party_id == party_id)
    stmt = stmt.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())


def create_invoice(db: Session, company: Company, data: InvoiceCreate, created_by_id: int) -> Invoice:
    party = party_service.get_party(db, company.id, data.party_id)
    gst_type = _resolve_gst(company, party, data.apply_gst)
    rows, totals = _build_items(data.items, gst_type)

    round_off = money(data.round_off)
    grand_total = totals["net"] + round_off

    if data.invoice_number:
        clash = db.execute(
            select(Invoice.id).where(
                Invoice.company_id == company.id,
                Invoice.invoice_number == data.invoice_number,
            )
        ).first()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An invoice with this number already exists",
            )
        invoice_number = data.invoice_number
    else:
        invoice_number = _next_invoice_number(db, company)

    invoice = Invoice(
        company_id=company.id,
        party_id=party.id,
        created_by_id=created_by_id,
        invoice_number=invoice_number,
        invoice_date=data.invoice_date or date.today(),
        document_type=data.document_type,
        copy_type=data.copy_type,
        place_of_supply=data.place_of_supply or party.place_of_supply,
        gst_type=gst_type,
        total_taxable=totals["taxable"],
        total_cgst=totals["cgst"],
        total_sgst=totals["sgst"],
        total_igst=totals["igst"],
        total_tax=totals["tax"],
        round_off=round_off,
        grand_total=grand_total,
        amount_in_words=amount_in_words(grand_total),
        note=data.note or company.default_note,
        payment_status=PaymentStatus.pending,
        amount_paid=Decimal("0"),
        items=rows,
    )
    db.add(invoice)
    db.commit()
    return get_invoice(db, company.id, invoice.id)


def update_invoice(db: Session, company: Company, invoice_id: int, data: InvoiceUpdate) -> Invoice:
    invoice = get_invoice(db, company.id, invoice_id)

    party = invoice.party
    if data.party_id is not None and data.party_id != invoice.party_id:
        party = party_service.get_party(db, company.id, data.party_id)
        invoice.party_id = party.id

    # Simple fields
    if data.invoice_date is not None:
        invoice.invoice_date = data.invoice_date
    if data.document_type is not None:
        invoice.document_type = data.document_type
    if data.copy_type is not None:
        invoice.copy_type = data.copy_type
    if data.place_of_supply is not None:
        invoice.place_of_supply = data.place_of_supply
    if data.note is not None:
        invoice.note = data.note

    # Re-compute money if items / gst / round_off changed
    if data.items is not None or data.apply_gst is not None or data.round_off is not None:
        apply_gst = data.apply_gst
        gst_type = _resolve_gst(company, party, apply_gst) if apply_gst is not None else invoice.gst_type
        items_source = data.items if data.items is not None else [
            InvoiceItemCreate(
                product_name=i.product_name, years=i.years,
                quantity=float(i.quantity), rate=float(i.rate), gst_rate=float(i.gst_rate),
            )
            for i in invoice.items
        ]
        rows, totals = _build_items(items_source, gst_type)
        round_off = money(data.round_off) if data.round_off is not None else money(invoice.round_off)
        grand_total = totals["net"] + round_off

        invoice.items = rows
        invoice.gst_type = gst_type
        invoice.total_taxable = totals["taxable"]
        invoice.total_cgst = totals["cgst"]
        invoice.total_sgst = totals["sgst"]
        invoice.total_igst = totals["igst"]
        invoice.total_tax = totals["tax"]
        invoice.round_off = round_off
        invoice.grand_total = grand_total
        invoice.amount_in_words = amount_in_words(grand_total)
        invoice.payment_status = _payment_status(money(invoice.amount_paid), grand_total)

    db.commit()
    return get_invoice(db, company.id, invoice.id)


def record_payment(db: Session, company_id: int, invoice_id: int, data: PaymentUpdate) -> Invoice:
    invoice = get_invoice(db, company_id, invoice_id)
    amount_paid = money(data.amount_paid)
    if amount_paid > money(invoice.grand_total):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount paid cannot exceed the grand total",
        )
    invoice.amount_paid = amount_paid
    invoice.payment_status = _payment_status(amount_paid, money(invoice.grand_total))
    invoice.payment_date = data.payment_date or (date.today() if amount_paid > 0 else None)
    invoice.payment_mode = data.payment_mode
    db.commit()
    return get_invoice(db, company_id, invoice.id)


def delete_invoice(db: Session, company_id: int, invoice_id: int) -> None:
    invoice = get_invoice(db, company_id, invoice_id)
    db.delete(invoice)
    db.commit()
