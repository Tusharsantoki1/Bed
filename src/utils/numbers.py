"""Number helpers: amount in words (Indian style) and money rounding."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from num2words import num2words

TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    """Quantize any numeric to 2 decimal places using bankers-safe rounding."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def amount_in_words(amount) -> str:
    """Convert an amount to Indian-English words, e.g. 17900 ->
    'Rupees Seventeen Thousand Nine Hundred Only'."""
    amt = money(amount)
    rupees = int(amt)
    paise = int((amt - rupees) * 100)

    rupee_words = num2words(rupees, lang="en_IN").replace(",", "").title()
    text = f"Rupees {rupee_words}"
    if paise:
        paise_words = num2words(paise, lang="en_IN").replace(",", "").title()
        text += f" and {paise_words} Paise"
    return f"{text} Only"
