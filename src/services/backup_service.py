"""Company data backup — export the whole company as a JSON snapshot the user
can download and keep. (Restore/import is a future enhancement.)"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.followup import Followup
from ..models.invoice import Invoice, InvoiceItem
from ..models.item import Item
from ..models.party import Party
from ..models.payment import Payment
from . import company_service


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
