"""Dashboard / reporting schemas."""

from pydantic import BaseModel


class CompanyDashboard(BaseModel):
    total_invoices: int
    total_billed: float
    total_received: float
    total_outstanding: float
    paid_count: int
    partial_count: int
    pending_count: int
    total_parties: int


class SuperAdminDashboard(BaseModel):
    total_companies: int
    active_companies: int
    inactive_companies: int
    active_subscriptions: int
    expired_subscriptions: int
    total_subscription_revenue: float
    total_invoices: int
