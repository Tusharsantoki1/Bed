"""Gujarati number-to-words, using the Indian (લાખ / કરોડ) grouping.

`num2words` has no Gujarati locale, so the mapping is written out here. Gujarati
(like Hindi) has an irregular word for every number 0-99, so the units table is
exhaustive rather than composed from tens + ones.
"""

from __future__ import annotations

from decimal import Decimal

from .numbers import money

# 0-99 spelled out. Gujarati compounds these irregularly (21 is "એકવીસ", not
# "વીસ એક"), so there is no shortcut here.
_ONES = [
    "શૂન્ય", "એક", "બે", "ત્રણ", "ચાર", "પાંચ", "છ", "સાત", "આઠ", "નવ",
    "દસ", "અગિયાર", "બાર", "તેર", "ચૌદ", "પંદર", "સોળ", "સત્તર", "અઢાર", "ઓગણીસ",
    "વીસ", "એકવીસ", "બાવીસ", "ત્રેવીસ", "ચોવીસ", "પચ્ચીસ", "છવ્વીસ", "સત્તાવીસ", "અઠ્ઠાવીસ", "ઓગણત્રીસ",
    "ત્રીસ", "એકત્રીસ", "બત્રીસ", "તેત્રીસ", "ચોત્રીસ", "પાંત્રીસ", "છત્રીસ", "સાડત્રીસ", "આડત્રીસ", "ઓગણચાલીસ",
    "ચાલીસ", "એકતાલીસ", "બેતાલીસ", "ત્રેતાલીસ", "ચુંમાલીસ", "પિસ્તાલીસ", "છેતાલીસ", "સુડતાલીસ", "અડતાલીસ", "ઓગણપચાસ",
    "પચાસ", "એકાવન", "બાવન", "ત્રેપન", "ચોપન", "પંચાવન", "છપ્પન", "સત્તાવન", "અઠ્ઠાવન", "ઓગણસાઠ",
    "સાઠ", "એકસઠ", "બાસઠ", "ત્રેસઠ", "ચોસઠ", "પાંસઠ", "છાસઠ", "સડસઠ", "અડસઠ", "ઓગણસિત્તેર",
    "સિત્તેર", "એકોતેર", "બોતેર", "તોતેર", "ચુમોતેર", "પંચોતેર", "છોતેર", "સિત્યોતેર", "ઇઠ્યોતેર", "ઓગણાએંસી",
    "એંસી", "એક્યાસી", "બ્યાસી", "ત્યાસી", "ચોર્યાસી", "પંચ્યાસી", "છ્યાસી", "સિત્યાસી", "ઈઠ્યાસી", "નેવ્યાસી",
    "નેવું", "એકાણું", "બાણું", "ત્રાણું", "ચોરાણું", "પંચાણું", "છન્નું", "સત્તાણું", "અઠ્ઠાણું", "નવ્વાણું",
]

# Indian place values, largest first. Each step is applied to the remainder.
_SCALES = [
    (10_000_000, "કરોડ"),
    (100_000, "લાખ"),
    (1_000, "હજાર"),
    (100, "સો"),
]

# Hundreds normally fuse as digit + સો (આઠસો, નવસો). 200 is irregular: the
# regular form "બેસો" is also the imperative "sit down", so it is written બસો.
_HUNDREDS = {
    1: "એકસો",
    2: "બસો",
    3: "ત્રણસો",
    4: "ચારસો",
    5: "પાંચસો",
    6: "છસો",
    7: "સાતસો",
    8: "આઠસો",
    9: "નવસો",
}


def gujarati_words(number: int) -> str:
    """Spell a non-negative integer in Gujarati, e.g. 11800 -> 'અગિયાર હજાર આઠસો'."""
    if number < 0:
        raise ValueError("gujarati_words expects a non-negative integer")
    if number < 100:
        return _ONES[number]

    parts: list[str] = []
    remainder = number

    for value, name in _SCALES:
        count, remainder = divmod(remainder, value)
        if not count:
            continue
        if name == "સો":
            # Hundreds fuse onto the digit: 800 is "આઠસો", not "આઠ સો".
            parts.append(_HUNDREDS[count])
        else:
            parts.append(f"{gujarati_words(count)} {name}")

    if remainder:
        parts.append(_ONES[remainder])

    return " ".join(parts)


def gujarati_amount_in_words(amount) -> str:
    """Spell a rupee amount in Gujarati, including paise when non-zero.

    11800     -> 'અગિયાર હજાર આઠસો'
    11800.50  -> 'અગિયાર હજાર આઠસો રૂપિયા પચાસ પૈસા'

    A negative amount (a party carrying a credit) is spelled as its magnitude
    prefixed with "ઓછા" — spelling must never raise, because it is reached from
    the reminder endpoint.
    """
    amt: Decimal = money(amount)
    negative = amt < 0
    amt = abs(amt)

    rupees = int(amt)
    paise = int((amt - rupees) * 100)

    if paise:
        text = f"{gujarati_words(rupees)} રૂપિયા {gujarati_words(paise)} પૈસા"
    else:
        text = gujarati_words(rupees)
    return f"ઓછા {text}" if negative else text


def indian_grouping(amount) -> str:
    """Format a number with Indian digit grouping: 1234567.5 -> '12,34,567.50'.

    Python's ',' format spec only knows Western thousands grouping, so the
    integer part is regrouped by hand (last 3 digits, then pairs).
    """
    amt: Decimal = money(amount)
    negative = amt < 0
    amt = abs(amt)

    whole = int(amt)
    fraction = int((amt - whole) * 100)

    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        pairs = []
        while len(head) > 2:
            pairs.insert(0, head[-2:])
            head = head[:-2]
        if head:
            pairs.insert(0, head)
        grouped = ",".join(pairs + [tail])
    else:
        grouped = digits

    text = f"{grouped}.{fraction:02d}"
    return f"-{text}" if negative else text
