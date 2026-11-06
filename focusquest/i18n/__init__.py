"""Lightweight bilingual strings with instant RTL/LTR switching."""
from __future__ import annotations

from focusquest.i18n import ar, en

_LANGS = {"ar": ar.STRINGS, "en": en.STRINGS}
_current = "ar"


def set_language(code: str) -> str:
    global _current
    if code in _LANGS:
        _current = code
    return _current


def language() -> str:
    return _current


def is_rtl() -> bool:
    return _current == "ar"


def d(key: str, **kwargs) -> str:
    table = _LANGS.get(_current, en.STRINGS)
    text = table.get(key, en.STRINGS.get(key, key))
    try:
        return text.format(**kwargs)
    except (IndexError, KeyError, ValueError):
        return text
