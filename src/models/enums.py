"""Enumerations shared across models and schemas."""

import enum


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    company_admin = "company_admin"
    company_staff = "company_staff"


class PlanCycle(str, enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    half_yearly = "half_yearly"   # 6 months
    yearly = "yearly"


# Number of days each billing cycle adds to a subscription.
PLAN_CYCLE_DAYS: dict[PlanCycle, int] = {
    PlanCycle.monthly: 30,
    PlanCycle.quarterly: 90,
    PlanCycle.half_yearly: 180,
    PlanCycle.yearly: 365,
}


class SubscriptionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class DocumentType(str, enum.Enum):
    invoice = "invoice"
    debit_memo = "debit_memo"
    credit_memo = "credit_memo"


class GstType(str, enum.Enum):
    none = "none"            # no GST on this invoice
    intra_state = "intra_state"   # CGST + SGST (same state)
    inter_state = "inter_state"   # IGST (different state)


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    partial = "partial"
    paid = "paid"
