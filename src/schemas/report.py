"""Collection / receivables report schemas (aging, outstanding, ledger,
collection, overdue, summary, WhatsApp reminder)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel

from ..models.enums import PaymentMode
from .followup import FollowupOut


# --- Aging ---------------------------------------------------------------

class AgingBuckets(BaseModel):
    not_due: float = 0
    d1_30: float = 0
    d31_60: float = 0
    d61_90: float = 0
    d91_120: float = 0
    d120_plus: float = 0
    total: float = 0


class PartyAgingRow(AgingBuckets):
    party_id: int
    party_name: str


class AgingReport(BaseModel):
    totals: AgingBuckets
    parties: list[PartyAgingRow]


# --- Outstanding (party-wise & bill-wise) --------------------------------

class OutstandingPartyRow(BaseModel):
    party_id: int
    party_name: str
    phone: Optional[str] = None
    city: Optional[str] = None
    outstanding: float
    overdue: float
    oldest_due_date: Optional[date] = None


class OutstandingReport(BaseModel):
    total_outstanding: float
    total_overdue: float
    parties: list[OutstandingPartyRow]


class BillRow(BaseModel):
    invoice_id: int
    invoice_number: str
    party_id: int
    party_name: str
    invoice_date: date
    due_date: Optional[date] = None
    grand_total: float
    amount_paid: float
    balance: float
    overdue_days: int = 0


class BillReport(BaseModel):
    total_balance: float
    total_overdue: float
    bills: list[BillRow]


# --- Party ledger --------------------------------------------------------

class LedgerEntry(BaseModel):
    date: date
    kind: str            # "opening" | "bill" | "payment"
    ref: Optional[str] = None
    particulars: str
    debit: float = 0     # increases what the party owes (bills)
    credit: float = 0    # reduces it (payments)
    balance: float = 0   # running outstanding


class PartyLedger(BaseModel):
    party_id: int
    party_name: str
    opening_balance: float
    total_billed: float
    total_paid: float
    outstanding: float
    entries: list[LedgerEntry]


# --- Collection ----------------------------------------------------------

class CollectionRow(BaseModel):
    payment_id: int
    payment_date: date
    party_id: int
    party_name: str
    amount: float
    mode: PaymentMode
    reference_no: Optional[str] = None
    invoice_number: Optional[str] = None


class CollectionReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_collected: float
    count: int
    payments: list[CollectionRow]


class DailyCollectionRow(BaseModel):
    day: date
    amount: float
    count: int


class DailyCollectionReport(BaseModel):
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total: float
    days: list[DailyCollectionRow]


# --- Summary (one-page view) ---------------------------------------------

class CollectionSummary(BaseModel):
    total_outstanding: float
    total_overdue: float
    today_collection: float
    month_collection: float
    today_followups: int
    pending_followups: int
    total_parties: int
    recent_payments: list[CollectionRow]
    upcoming_followups: list[FollowupOut]


# --- WhatsApp reminder ---------------------------------------------------

class WhatsAppMessage(BaseModel):
    party_id: int
    party_name: str
    phone: Optional[str] = None
    outstanding: float
    message: str
    wa_link: Optional[str] = None
