"""Build WhatsApp payment-reminder messages and click-to-chat links.

No WhatsApp API integration — we return the message text plus a wa.me deep link
the mobile app opens, so the user sends it from their own WhatsApp.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import quote

from sqlalchemy.orm import Session

from ..schemas.report import WhatsAppMessage
from . import company_service, party_service, report_service


def _intl_phone(phone: str | None) -> str | None:
    """Normalise an Indian phone number to wa.me digits (country code + number)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:            # local 10-digit -> prefix India country code
        digits = "91" + digits
    if len(digits) < 11:
        return None
    return digits


def build_reminder(db: Session, company_id: int, party_id: int) -> WhatsAppMessage:
    party = party_service.get_party(db, company_id, party_id)
    company = company_service.get_company(db, company_id)
    outstanding = report_service.party_outstanding(db, company_id, party_id)

    today = date.today().strftime("%d-%m-%Y")
    message = (
        f"Dear {party.name},\n\n"
        f"Your outstanding balance with {company.name} is "
        f"Rs. {outstanding:,.2f} as on {today}.\n"
        f"Kindly arrange the payment at the earliest.\n\n"
        f"Thank you."
    )

    intl = _intl_phone(party.phone)
    wa_link = f"https://wa.me/{intl}?text={quote(message)}" if intl else None

    return WhatsAppMessage(
        party_id=party.id,
        party_name=party.name,
        phone=party.phone,
        outstanding=outstanding,
        message=message,
        wa_link=wa_link,
    )
