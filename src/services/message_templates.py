"""Payment-reminder message templates, in English and Gujarati.

Kept apart from `whatsapp_service` so the wording can be reviewed and changed
without touching the link-building logic.
"""

from __future__ import annotations

from ..utils.gujarati_numbers import gujarati_amount_in_words, indian_grouping

LANGUAGES = ("en", "gu")
DEFAULT_LANGUAGE = "en"


def _english(amount, company_name: str) -> str:
    return (
        "Hi,\n"
        f"It's a friendly reminder to you for paying {indian_grouping(amount)} to me.\n"
        "\n"
        "Thank you,\n"
        f"{company_name}"
    )


def _gujarati(amount, company_name: str) -> str:
    # The amount is shown as digits with the Gujarati words in brackets, e.g.
    # "11,800 (અગિયાર હજાર આઠસો)". Paise are only spelled when non-zero, so a
    # round amount reads naturally.
    grouped = indian_grouping(amount)
    if grouped.endswith(".00"):
        grouped = grouped[:-3]
    words = gujarati_amount_in_words(amount)

    return (
        "નમસ્તે,\n"
        "\n"
        f"તમને {grouped} ({words})ની રકમ ચૂકવવા માટેની આ એક સૌજન્યપૂર્ણ "
        "યાદ-અપાવણી (રિમાઇન્ડર) છે.\n"
        "\n"
        "આભાર,\n"
        f"{company_name}"
    )


_BUILDERS = {"en": _english, "gu": _gujarati}


def build_message(language: str, amount, company_name: str) -> str:
    """Render the reminder in `language`, falling back to English if unknown."""
    builder = _BUILDERS.get(language, _BUILDERS[DEFAULT_LANGUAGE])
    return builder(amount, company_name)


def build_all(amount, company_name: str) -> dict[str, str]:
    """Render every language at once, so the UI can toggle without a refetch."""
    return {lang: build_message(lang, amount, company_name) for lang in LANGUAGES}
