"""Company data backup — export the whole company as a JSON snapshot the user
can download and keep. (Restore/import is a future enhancement.)"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.enums import (
    DocumentType,
    FollowupStatus,
    FollowupType,
    GstType,
    PaymentMode,
    PaymentStatus,
)
from ..models.followup import Followup
from ..models.invoice import Invoice, InvoiceItem
from ..models.item import Item
from ..models.party import Party
from ..models.payment import Payment
from . import company_service, payment_service


def _val(v: Any) -> Any:
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, enum.Enum):
        return v.value
    return v


def _dump(obj) -> dict:
    return {c.key: _val(getattr(obj, c.key)) for c in sa_inspect(obj).mapper.column_attrs}


def _all(db: Session, model, company_id: int) -> list[dict]:
    rows = db.execute(select(model).where(model.company_id == company_id)).scalars().all()
    return [_dump(r) for r in rows]


def export_company_data(db: Session, company_id: int) -> dict:
    company = company_service.get_company(db, company_id)
    invoice_ids = [i.id for i in company.invoices]
    invoice_items = (
        db.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id.in_(invoice_ids))
        ).scalars().all()
        if invoice_ids
        else []
    )
    return {
        "exported_at": datetime.now().isoformat(),  # noqa: DTZ005 - local stamp for the file
        "company": _dump(company),
        "parties": _all(db, Party, company_id),
        "items": _all(db, Item, company_id),
        "invoices": _all(db, Invoice, company_id),
        "invoice_items": [_dump(r) for r in invoice_items],
        "payments": _all(db, Payment, company_id),
        "followups": _all(db, Followup, company_id),
    }


# --- Restore (import a snapshot into the current company) -----------------

def _d(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None


def restore_company_data(db: Session, company_id: int, data: dict) -> dict:
    """Import a snapshot (from export_company_data) into the CURRENT company.

    Additive: parties/items are matched by name (reused if present, else
    created); invoices, payments and follow-ups are re-created with remapped
    ids. The company profile itself is left untouched. One transaction.
    """
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup file")

    try:
        # Parties (match by name).
        existing_parties = {
            (p.name or "").strip().lower(): p.id
            for p in db.execute(select(Party).where(Party.company_id == company_id)).scalars()
        }
        party_map: dict[int, int] = {}
        for row in data.get("parties", []):
            key = (row.get("name") or "").strip().lower()
            if key in existing_parties:
                party_map[row["id"]] = existing_parties[key]
                continue
            p = Party(
                company_id=company_id,
                name=row.get("name") or "Unnamed",
                address=row.get("address"), city=row.get("city"), state=row.get("state"),
                state_code=row.get("state_code"), place_of_supply=row.get("place_of_supply"),
                gstin=row.get("gstin"), phone=row.get("phone"), email=row.get("email"),
                credit_days=int(row.get("credit_days") or 0),
                opening_balance=Decimal(str(row.get("opening_balance") or 0)),
            )
            db.add(p)
            db.flush()
            party_map[row["id"]] = p.id
            existing_parties[key] = p.id

        # Items (match by name).
        existing_items = {
            (i.name or "").strip().lower()
            for i in db.execute(select(Item).where(Item.company_id == company_id)).scalars()
        }
        for row in data.get("items", []):
            key = (row.get("name") or "").strip().lower()
            if not key or key in existing_items:
                continue
            db.add(Item(
                company_id=company_id, name=row.get("name"),
                hsn_code=row.get("hsn_code"), unit=row.get("unit"),
                default_rate=Decimal(str(row.get("default_rate") or 0)),
                default_gst_rate=Decimal(str(row.get("default_gst_rate") or 0)),
                description=row.get("description"),
            ))
            existing_items.add(key)

        # Invoices (+ their line items). Dedup invoice numbers within company.
        used_numbers = {
            n for (n,) in db.execute(
                select(Invoice.invoice_number).where(Invoice.company_id == company_id)
            )
        }
        items_by_invoice: dict[int, list[dict]] = {}
        for it in data.get("invoice_items", []):
            items_by_invoice.setdefault(it["invoice_id"], []).append(it)

        invoice_map: dict[int, int] = {}
        touched_invoices: list[int] = []
        for row in data.get("invoices", []):
            if row["party_id"] not in party_map:
                continue
            number = row.get("invoice_number") or "INV"
            if number in used_numbers:
                suffix, cand = 1, f"{number}-R1"
                while cand in used_numbers:
                    suffix += 1
                    cand = f"{number}-R{suffix}"
                number = cand
            used_numbers.add(number)

            inv = Invoice(
                company_id=company_id,
                party_id=party_map[row["party_id"]],
                invoice_number=number,
                invoice_date=_d(row.get("invoice_date")) or date.today(),
                due_date=_d(row.get("due_date")),
                document_type=DocumentType(row.get("document_type", "invoice")),
                copy_type=row.get("copy_type") or "Original",
                place_of_supply=row.get("place_of_supply"),
                gst_type=GstType(row.get("gst_type", "none")),
                total_taxable=Decimal(str(row.get("total_taxable") or 0)),
                total_cgst=Decimal(str(row.get("total_cgst") or 0)),
                total_sgst=Decimal(str(row.get("total_sgst") or 0)),
                total_igst=Decimal(str(row.get("total_igst") or 0)),
                total_tax=Decimal(str(row.get("total_tax") or 0)),
                round_off=Decimal(str(row.get("round_off") or 0)),
                grand_total=Decimal(str(row.get("grand_total") or 0)),
                amount_in_words=row.get("amount_in_words"),
                note=row.get("note"),
                payment_status=PaymentStatus.pending,
                amount_paid=Decimal("0"),
                items=[
                    InvoiceItem(
                        sr_no=int(li.get("sr_no") or idx),
                        product_name=li.get("product_name") or "Item",
                        years=li.get("years"),
                        quantity=Decimal(str(li.get("quantity") or 1)),
                        rate=Decimal(str(li.get("rate") or 0)),
                        taxable_amount=Decimal(str(li.get("taxable_amount") or 0)),
                        gst_rate=Decimal(str(li.get("gst_rate") or 0)),
                        cgst_amount=Decimal(str(li.get("cgst_amount") or 0)),
                        sgst_amount=Decimal(str(li.get("sgst_amount") or 0)),
                        igst_amount=Decimal(str(li.get("igst_amount") or 0)),
                        tax_amount=Decimal(str(li.get("tax_amount") or 0)),
                        net_amount=Decimal(str(li.get("net_amount") or 0)),
                    )
                    for idx, li in enumerate(items_by_invoice.get(row["id"], []), start=1)
                ],
            )
            db.add(inv)
            db.flush()
            invoice_map[row["id"]] = inv.id
            touched_invoices.append(inv.id)

        # Payments.
        for row in data.get("payments", []):
            if row["party_id"] not in party_map:
                continue
            db.add(Payment(
                company_id=company_id,
                party_id=party_map[row["party_id"]],
                invoice_id=invoice_map.get(row.get("invoice_id")),
                amount=Decimal(str(row.get("amount") or 0)),
                payment_date=_d(row.get("payment_date")) or date.today(),
                mode=PaymentMode(row.get("mode", "cash")),
                reference_no=row.get("reference_no"),
                remarks=row.get("remarks"),
            ))

        # Follow-ups.
        for row in data.get("followups", []):
            if row["party_id"] not in party_map:
                continue
            db.add(Followup(
                company_id=company_id,
                party_id=party_map[row["party_id"]],
                invoice_id=invoice_map.get(row.get("invoice_id")),
                type=FollowupType(row.get("type", "call")),
                remarks=row.get("remarks"),
                followup_date=_d(row.get("followup_date")) or date.today(),
                next_followup_date=_d(row.get("next_followup_date")),
                status=FollowupStatus(row.get("status", "done")),
            ))

        db.flush()
        for inv_id in touched_invoices:
            inv = db.get(Invoice, inv_id)
            if inv is not None:
                payment_service.recompute_invoice(db, inv)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # malformed data
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not restore backup: {exc}",
        )

    return {
        "parties": len(party_map),
        "invoices": len(invoice_map),
        "payments": len(data.get("payments", [])),
        "followups": len(data.get("followups", [])),
    }
