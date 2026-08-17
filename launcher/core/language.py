"""
Maps a language code to the instruction sentence appended to the system
prompt. Kept separate from the user-editable general prompt so the GUI's
language dropdown can change this independently.
"""

_LANGUAGE_INSTRUCTIONS = {
    "es-419": "Always respond in neutral Latin American Spanish.",
    "en": "Always respond in English.",
    "pt-br": "Always respond in Brazilian Portuguese.",
}

DEFAULT_LANGUAGE = "es-419"


def get_language_instruction(language_code: str) -> str:
    return _LANGUAGE_INSTRUCTIONS.get(language_code, _LANGUAGE_INSTRUCTIONS[DEFAULT_LANGUAGE])


def list_languages() -> list:
    """Returns [(code, label), ...] for populating a dropdown."""
    return [
        ("es-419", "Spanish (Latin America)"),
        ("en", "English"),
        ("pt-br", "Portuguese (Brazil)"),
    ]
