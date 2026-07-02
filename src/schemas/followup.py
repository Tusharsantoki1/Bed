"""Follow-up (collection chase log) schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from ..models.enums import FollowupStatus, FollowupType
from .common import ORMModel


class FollowupCreate(BaseModel):
    party_id: int
    invoice_id: Optional[int] = None
    type: FollowupType = FollowupType.call
    remarks: Optional[str] = Field(default=None, max_length=1000)
    followup_date: Optional[date] = None  # defaults to today
    next_followup_date: Optional[date] = None
    status: FollowupStatus = FollowupStatus.done


class FollowupUpdate(BaseModel):
    type: Optional[FollowupType] = None
    remarks: Optional[str] = Field(default=None, max_length=1000)
    followup_date: Optional[date] = None
    next_followup_date: Optional[date] = None
    status: Optional[FollowupStatus] = None


class FollowupOut(ORMModel):
    id: int
    company_id: int
    party_id: int
    invoice_id: Optional[int] = None
    type: FollowupType
    remarks: Optional[str] = None
    followup_date: date
    next_followup_date: Optional[date] = None
    status: FollowupStatus
    # convenience for lists
    party_name: Optional[str] = None
