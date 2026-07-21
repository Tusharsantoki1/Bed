"""Build WhatsApp payment-reminder messages and click-to-chat links.

No WhatsApp API integration — we return the message text plus a wa.me deep link
the mobile app opens, so the user sends it from their own WhatsApp.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from sqlalchemy.orm import Session

from ..schemas.report import WhatsAppMessage
from . import company_service, message_templates, party_service, report_service

# Numbers without a country code are read as Indian.
DEFAULT_REGION = "IN"

# Number types WhatsApp can actually deliver to. Landlines and premium/toll-free
# ranges are excluded; FIXED_LINE_OR_MOBILE stays because that type means the
# numbering plan genuinely cannot tell the two apart.
try:  # pragma: no cover - depends on the optional dependency
    import phonenumbers as _pn

    _WHATSAPP_CAPABLE = frozenset(
        {
            _pn.PhoneNumberType.MOBILE,
            _pn.PhoneNumberType.FIXED_LINE_OR_MOBILE,
        }
    )
except ImportError:  # pragma: no cover
    _WHATSAPP_CAPABLE = frozenset()


def _first_number(phone: str) -> str:
    """Take only the first number when the field holds several ("a / b")."""
    return re.split(r"[,/;]|\s{2,}", phone.strip())[0]


def _intl_phone_fallback(first: str) -> str | None:
    """Format-only normalisation, used if `phonenumbers` is unavailable.

    Cannot tell an 079 (Ahmedabad) or 080 (Bangalore) landline from a mobile —
    both are 11 digits starting with 0 — so those are accepted here.
    """
    digits = re.sub(r"\D", "", first)

    # International prefixes: 00xx / +xx both reduce to the bare country code.
    if digits.startswith("00"):
        digits = digits[2:]

    # Strip an Indian trunk zero ("0 98765 43210" -> "9876543210").
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Already country-coded (91XXXXXXXXXX).
    if len(digits) == 12 and digits.startswith("91"):
        subscriber = digits[2:]
    elif len(digits) == 10:
        subscriber = digits
    else:
        return None

    # Indian mobile numbers start with 6-9; 2-5 are landline ranges.
    if subscriber[0] not in "6789":
        return None

    return "91" + subscriber


def _intl_phone(phone: str | None) -> str | None:
    """Normalise a phone number to wa.me digits (country code + number).

    Returns None for anything WhatsApp cannot reach, so callers can warn rather
    than silently opening a dead chat. Landlines are rejected: WhatsApp has no
    landline accounts, and an STD-coded landline is the same length as a mobile,
    so this needs real numbering-plan data rather than a digit-count rule.
    """
    if not phone:
        return None

    first = _first_number(phone)

    try:
        import phonenumbers
    except ImportError:
        return _intl_phone_fallback(first)

    try:
        parsed = phonenumbers.parse(first, DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(parsed):
        return None

    # FIXED_LINE_OR_MOBILE is kept: some ranges are genuinely ambiguous and
    # rejecting them would block reachable customers.
    if phonenumbers.number_type(parsed) not in _WHATSAPP_CAPABLE:
        return None

    # E.164 without the leading "+", which is what wa.me expects.
    return phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164
    ).lstrip("+")


def build_reminder(
    db: Session,
    company_id: int,
    party_id: int,
    language: str = message_templates.DEFAULT_LANGUAGE,
) -> WhatsAppMessage:
    party = party_service.get_party(db, company_id, party_id)
    company = company_service.get_company(db, company_id)
    outstanding = report_service.party_outstanding(db, company_id, party_id)

    # Every language is rendered up front so the UI can switch instantly.
    messages = message_templates.build_all(outstanding, company.name)
    message = messages.get(language, messages[message_templates.DEFAULT_LANGUAGE])

    intl = _intl_phone(party.phone)
    # quote() with an empty safe list percent-encodes spaces as %20 rather than
    # "+", which WhatsApp would otherwise show literally.
    wa_link = f"https://wa.me/{intl}?text={quote(message, safe='')}" if intl else None

    return WhatsAppMessage(
        party_id=party.id,
        party_name=party.name,
        phone=party.phone,
        outstanding=outstanding,
        message=message,
        messages=messages,
        language=language,
        wa_number=intl,
        wa_link=wa_link,
    )
