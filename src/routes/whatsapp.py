"""WhatsApp payment-reminder routes — build a message + wa.me link."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..schemas.report import WhatsAppMessage
from ..services import message_templates, whatsapp_service
from ..utils.deps import require_company_user

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/reminder/{party_id}", response_model=WhatsAppMessage)
def reminder(
    party_id: int,
    lang: str = Query(
        message_templates.DEFAULT_LANGUAGE,
        pattern="^(en|gu)$",
        description="Message language: 'en' (English) or 'gu' (Gujarati).",
    ),
    current_user: User = Depends(require_company_user),
    db: Session = Depends(get_db),
):
    """Build an outstanding-reminder message and click-to-chat link for a party."""
    return whatsapp_service.build_reminder(
        db, current_user.company_id, party_id, language=lang
    )
