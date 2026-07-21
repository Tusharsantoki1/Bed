"""Render an invoice to HTML and to PDF from a single shared template.

The PDF (WeasyPrint) and the in-app preview both come from
`templates/invoice.html`, so the printed bill and the on-screen bill cannot
drift apart. WeasyPrint also gives real Unicode support, which the previous
fpdf2 implementation lacked — the rupee sign and Gujarati text render fine.
"""

from __future__ import annotations

import base64
import binascii
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..models.company import Company
from ..models.enums import DocumentType, GstType
from ..models.invoice import Invoice

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Measured off the reference bill: the item area is 115.4pt tall and each line
# occupies 13.5pt. Short bills are padded with a filler row so the bank block
# always lands in the same place.
ITEMS_AREA_PT = 115.4
ITEM_ROW_PT = 13.5
# The product column is 31.8% of a 537.7pt table; at 7.5pt Times that fits
# roughly 48 characters per line. Used to predict wrapping so the filler can
# shrink accordingly instead of pushing the footer off the page.
PRODUCT_CHARS_PER_LINE = 48


# Rows render a fraction over their nominal 13.5pt, so a filler smaller than
# this is dropped rather than tipping a nearly-full bill onto a second page.
MIN_FILLER_PT = 12.0


def _row_lines(name: str) -> int:
    """How many lines the product name will wrap onto."""
    if not name:
        return 1
    longest = max(len(part) for part in name.split("\n"))
    return max(1, -(-longest // PRODUCT_CHARS_PER_LINE))  # ceil division


def _filler_height(rows: list[dict]) -> float:
    """Height of the blank row that pads the item area to the reference height."""
    used = ITEM_ROW_PT * sum(_row_lines(r["product_name"]) for r in rows)
    filler = ITEMS_AREA_PT - used
    return round(filler, 1) if filler >= MIN_FILLER_PT else 0.0

DOC_LABELS = {
    DocumentType.invoice: "Tax Invoice",
    DocumentType.debit_memo: "Debit Memo",
    DocumentType.credit_memo: "Credit Memo",
}

# Sniff the image type from its first bytes so the data URI carries the right
# MIME type — browsers are lenient about this, WeasyPrint is not.
_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


@lru_cache(maxsize=1)
def _stylesheet() -> str:
    return (TEMPLATE_DIR / "invoice.css").read_text(encoding="utf-8")


def _money(value) -> str:
    """Plain 2-decimal money, matching the reference bill (no thousands commas
    inside the item table)."""
    return f"{Decimal(str(value or 0)):.2f}"


def _qty(value) -> str:
    """Quantities print as integers when whole: 12 rather than 12.00."""
    dec = Decimal(str(value or 0))
    return str(int(dec)) if dec == dec.to_integral_value() else f"{dec:.2f}"


def _rate(value) -> str:
    """GST percentage without trailing zeros: 18.00 -> '18', 2.50 -> '2.5'.

    Decimal's 'g' format keeps the stored scale ('18.00'), so normalize first;
    'f' then avoids the exponent form normalize() can produce.
    """
    return format(Decimal(str(value or 0)).normalize(), "f")


def _grand(value) -> str:
    """Grand total keeps thousands separators, as on the reference bill."""
    return f"{Decimal(str(value or 0)):,.2f}"


def _data_uri(b64: Optional[str]) -> Optional[str]:
    """Normalise a stored base64 image into a data URI usable by both renderers."""
    if not b64:
        return None
    data = b64.strip()
    if not data:
        return None
    if data.startswith("data:"):
        return data
    try:
        raw = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None

    mime = _sniff_mime(raw)
    return f"data:{mime};base64,{data}"


def _sniff_mime(raw: bytes) -> str:
    """Detect the image type from its leading bytes, defaulting to PNG."""
    for magic, candidate in _MAGIC:
        if raw.startswith(magic):
            return candidate
    # WEBP and SVG need more than a fixed prefix.
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    head = raw[:256].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in raw[:1024]):
        return "image/svg+xml"
    return "image/png"


def _build_context(invoice: Invoice, company: Company) -> dict:
    party = invoice.party
    has_gst = invoice.gst_type != GstType.none
    inter_state = invoice.gst_type == GstType.inter_state

    rows = []
    for item in invoice.items:
        if not has_gst:
            tax_a = tax_b = ""
        elif inter_state:
            # IGST is a single figure; show it in the first sub-column.
            tax_a, tax_b = _money(item.igst_amount), ""
        else:
            tax_a, tax_b = _money(item.cgst_amount), _money(item.sgst_amount)

        rows.append(
            {
                "sr_no": item.sr_no,
                "product_name": item.product_name,
                "years": item.years or "",
                "quantity": _qty(item.quantity),
                "rate": _money(item.rate),
                "taxable": _money(item.taxable_amount),
                "gst_rate": _rate(item.gst_rate) if has_gst and item.gst_rate else "",
                "tax_a": tax_a,
                "tax_b": tax_b,
                "net": _money(item.net_amount),
            }
        )

    if not has_gst:
        total_a = total_b = ""
    elif inter_state:
        total_a, total_b = _money(invoice.total_igst), ""
    else:
        total_a, total_b = _money(invoice.total_cgst), _money(invoice.total_sgst)

    address_lines = [
        p for p in [
            company.address,
            ", ".join(p for p in [company.city, company.state, company.pincode] if p),
        ] if p
    ]
    party_lines = [
        p for p in [
            party.address,
            ", ".join(p for p in [party.city, party.state] if p),
            f"GSTIN : {party.gstin}" if party.gstin else None,
        ] if p
    ]

    return {
        "company": company,
        "party": party,
        "invoice": invoice,
        "doc_label": DOC_LABELS.get(invoice.document_type, "Tax Invoice"),
        "invoice_date": invoice.invoice_date.strftime("%d/%m/%Y"),
        "due_date": invoice.due_date.strftime("%d/%m/%Y") if invoice.due_date else None,
        "address_lines": address_lines,
        "party_lines": party_lines,
        "rows": rows,
        "filler_height": _filler_height(rows),
        "totals": {
            "taxable": _money(invoice.total_taxable),
            "tax_a": total_a,
            "tax_b": total_b,
            # Sum of the Net column, so it foots against the rows above. This is
            # the grand total *before* round-off, which the Grand Total box shows.
            "net": _money(sum(Decimal(str(i.net_amount or 0)) for i in invoice.items)),
            "grand": _grand(invoice.grand_total),
        },
        "logo": _data_uri(company.logo_base64),
        "qr": _data_uri(company.payment_qr_base64),
        "signature": _data_uri(company.signature_base64),
        "stamp": _data_uri(company.stamp_base64),
        # The VPA shown under the QR; falls back to the G-Pay number if unset.
        "upi_id": getattr(company, "upi_id", None) or company.upi_number or None,
    }


def render_invoice_html(invoice: Invoice, company: Company, standalone: bool = True) -> str:
    """Render the bill as HTML. `standalone=True` inlines the CSS for preview."""
    context = _build_context(invoice, company)
    context["standalone"] = standalone
    context["css"] = _stylesheet()
    return _env().get_template("invoice.html").render(**context)


def generate_invoice_pdf(invoice: Invoice, company: Company) -> bytes:
    """Render the bill to PDF bytes. Signature unchanged from the fpdf2 version."""
    # Imported here so the module still loads (for HTML preview) on machines
    # without WeasyPrint's native libraries installed.
    from weasyprint import CSS, HTML

    html = render_invoice_html(invoice, company, standalone=False)
    return HTML(string=html).write_pdf(stylesheets=[CSS(string=_stylesheet())])
