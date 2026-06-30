"""Render an invoice to a PDF (bytes) using fpdf2, matching the sample layout."""

from __future__ import annotations

import base64
import binascii
from io import BytesIO
from typing import Optional

from fpdf import FPDF

from ..models.company import Company
from ..models.enums import GstType
from ..models.invoice import Invoice

# Item table column widths (mm); must sum to the usable page width (190).
COLS = {
    "sr": 8,
    "product": 54,
    "years": 20,
    "qty": 12,
    "rate": 20,
    "taxable": 24,
    "gst": 12,
    "tax": 16,
    "net": 24,
}


def _money(value) -> str:
    return f"{float(value):,.2f}"


def _img_reader(b64: Optional[str]) -> Optional[BytesIO]:
    """Decode a base64 (optionally data-URI) image into a BytesIO, or None."""
    if not b64:
        return None
    data = b64.strip()
    if data.startswith("data:") and "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError):
        return None
    if not raw:
        return None
    return BytesIO(raw)


def _safe_image(pdf: FPDF, b64: Optional[str], x: float, y: float, w: float, h: float) -> None:
    reader = _img_reader(b64)
    if reader is None:
        return
    try:
        pdf.image(reader, x=x, y=y, w=w, h=h)
    except Exception:
        # A bad image must never break invoice generation.
        pass


def generate_invoice_pdf(invoice: Invoice, company: Company) -> bytes:
    party = invoice.party
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(left=10, top=10, right=10)
    pdf.add_page()
    epw = pdf.epw  # effective page width (190mm)
    x0 = pdf.l_margin

    # --- Header: company name/address (left) + logo (right) ---
    header_h = 22
    top = pdf.get_y()
    pdf.rect(x0, top, epw, header_h)
    _safe_image(pdf, company.logo_base64, x=x0 + epw - 32, y=top + 2, w=28, h=18)

    pdf.set_xy(x0 + 2, top + 2)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(epw - 36, 8, company.name, align="L")
    pdf.set_xy(x0 + 2, top + 11)
    pdf.set_font("Helvetica", "", 8)
    addr_parts = [p for p in [company.address, company.city, company.state, company.pincode] if p]
    pdf.multi_cell(epw - 36, 4, ", ".join(addr_parts), align="L")
    pdf.set_y(top + header_h)

    # --- Document type band ---
    band_h = 7
    by = pdf.get_y()
    pdf.rect(x0, by, epw, band_h)
    doc_label = {"invoice": "INVOICE", "debit_memo": "DEBIT MEMO", "credit_memo": "CREDIT MEMO"}.get(
        invoice.document_type.value, "INVOICE"
    )
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(x0, by)
    pdf.cell(epw / 3, band_h, "  Tax Invoice", align="L")
    pdf.cell(epw / 3, band_h, doc_label, align="C")
    pdf.cell(epw / 3, band_h, f"{invoice.copy_type}  ", align="R")
    pdf.set_y(by + band_h)

    # --- Party (left) + invoice meta (right) ---
    info_h = 26
    iy = pdf.get_y()
    half = epw / 2
    pdf.rect(x0, iy, half, info_h)
    pdf.rect(x0 + half, iy, half, info_h)

    pdf.set_xy(x0 + 2, iy + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(half - 4, 5, f"M/s. : {party.name}", align="L")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(x0 + 2, iy + 8)
    city_state = ", ".join(p for p in [party.city, party.state] if p)
    party_lines = [p for p in [party.address, city_state] if p]
    if party_lines:
        pdf.multi_cell(half - 4, 4, "\n".join(party_lines), align="L")
    # Place of supply + GSTIN pinned to the bottom of the box.
    pdf.set_xy(x0 + 2, iy + info_h - 9)
    pdf.cell(half - 4, 4, f"Place of Supply : {invoice.place_of_supply or '-'}", align="L")
    pdf.set_xy(x0 + 2, iy + info_h - 5)
    pdf.cell(half - 4, 4, f"GSTIN : {party.gstin or '-'}", align="L")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(x0 + half + 2, iy + 4)
    pdf.cell(half - 4, 6, f"Invoice No.  :  {invoice.invoice_number}", align="L")
    pdf.set_xy(x0 + half + 2, iy + 12)
    pdf.cell(half - 4, 6, f"Date         :  {invoice.invoice_date.strftime('%d/%m/%Y')}", align="L")
    pdf.set_y(iy + info_h)

    # --- Items table header ---
    pdf.set_font("Helvetica", "B", 8)
    row_h = 7
    headers = [
        ("sr", "Sr"), ("product", "Product Name"), ("years", "Years"),
        ("qty", "Qty"), ("rate", "Rate"), ("taxable", "Taxable"),
        ("gst", "GST%"), ("tax", "Tax"), ("net", "Net Amt"),
    ]
    hy = pdf.get_y()
    for key, label in headers:
        align = "L" if key == "product" else "C"
        pdf.cell(COLS[key], row_h, label, border=1, align=align)
    pdf.ln(row_h)

    # --- Items rows ---
    pdf.set_font("Helvetica", "", 8)
    has_gst = invoice.gst_type != GstType.none
    for item in invoice.items:
        pdf.cell(COLS["sr"], row_h, str(item.sr_no), border=1, align="C")
        name = item.product_name if len(item.product_name) <= 40 else item.product_name[:39] + "…"
        pdf.cell(COLS["product"], row_h, name, border=1, align="L")
        pdf.cell(COLS["years"], row_h, item.years or "", border=1, align="C")
        pdf.cell(COLS["qty"], row_h, _money(item.quantity), border=1, align="R")
        pdf.cell(COLS["rate"], row_h, _money(item.rate), border=1, align="R")
        pdf.cell(COLS["taxable"], row_h, _money(item.taxable_amount), border=1, align="R")
        pdf.cell(COLS["gst"], row_h, f"{float(item.gst_rate):g}" if has_gst and item.gst_rate else "", border=1, align="C")
        pdf.cell(COLS["tax"], row_h, _money(item.tax_amount) if has_gst else "", border=1, align="R")
        pdf.cell(COLS["net"], row_h, _money(item.net_amount), border=1, align="R")
        pdf.ln(row_h)

    # --- Totals row ---
    pdf.set_font("Helvetica", "B", 8)
    label_w = COLS["sr"] + COLS["product"] + COLS["years"] + COLS["qty"] + COLS["rate"]
    pdf.cell(label_w, row_h, "Total", border=1, align="R")
    pdf.cell(COLS["taxable"], row_h, _money(invoice.total_taxable), border=1, align="R")
    pdf.cell(COLS["gst"], row_h, "", border=1)
    pdf.cell(COLS["tax"], row_h, _money(invoice.total_tax) if has_gst else "", border=1, align="R")
    pdf.cell(COLS["net"], row_h, _money(invoice.grand_total), border=1, align="R")
    pdf.ln(row_h)

    # --- GST breakup line (only when GST applies) ---
    pdf.set_font("Helvetica", "", 8)
    if has_gst:
        if invoice.gst_type == GstType.inter_state:
            breakup = f"IGST: {_money(invoice.total_igst)}"
        else:
            breakup = f"CGST: {_money(invoice.total_cgst)}   SGST: {_money(invoice.total_sgst)}"
        pdf.cell(epw, 5, breakup, align="R")
        pdf.ln(6)
    else:
        pdf.ln(2)

    # --- Bank details (left) + QR (right) ---
    box_h = 30
    bxy = pdf.get_y()
    left_w = epw * 0.62
    right_w = epw - left_w
    pdf.rect(x0, bxy, left_w, box_h)
    pdf.rect(x0 + left_w, bxy, right_w, box_h)

    pdf.set_xy(x0 + 2, bxy + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(left_w - 4, 5, "Bank Details", align="L")
    pdf.set_font("Helvetica", "", 8)
    bank_lines = [
        f"Bank Name   : {company.bank_name or '-'}",
        f"A/c No.     : {company.bank_account_no or '-'}",
        f"IFSC Code   : {company.bank_ifsc or '-'}",
        f"G-Pay / UPI : {company.upi_number or '-'}",
    ]
    pdf.set_xy(x0 + 2, bxy + 8)
    pdf.multi_cell(left_w - 4, 5, "\n".join(bank_lines), align="L")

    _safe_image(pdf, company.payment_qr_base64, x=x0 + left_w + (right_w - 24) / 2, y=bxy + 3, w=24, h=24)
    pdf.set_y(bxy + box_h)

    # --- Amount in words + grand total ---
    words_h = 9
    wy = pdf.get_y()
    pdf.rect(x0, wy, left_w, words_h)
    pdf.rect(x0 + left_w, wy, right_w, words_h)
    pdf.set_xy(x0 + 2, wy)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(left_w - 4, words_h, f"Amount: {invoice.amount_in_words or ''}", align="L")
    pdf.set_xy(x0 + left_w, wy)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(right_w, words_h, f"Total  {_money(invoice.grand_total)}", align="C")
    pdf.set_y(wy + words_h)

    # --- Note + signature/stamp ---
    sy = pdf.get_y() + 2
    pdf.set_xy(x0, sy)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(left_w, 4, f"Note: {invoice.note or ''}", align="L")

    _safe_image(pdf, company.stamp_base64, x=x0 + left_w, y=sy, w=22, h=22)
    _safe_image(pdf, company.signature_base64, x=x0 + epw - 40, y=sy, w=34, h=18)
    pdf.set_xy(x0 + left_w, sy + 22)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(right_w, 5, f"For {company.name}", align="R")
    pdf.set_xy(x0 + left_w, sy + 27)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(right_w, 4, "(Authorised Signatory)", align="R")

    out = pdf.output()
    return bytes(out)
