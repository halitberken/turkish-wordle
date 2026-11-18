"""Turkish alphabet, Turkish-aware case conversion, normalisation and sorting.

Python's built-in case mapping is not Turkish-aware: ``"I".lower()`` gives
``"i"`` (should be ``"ı"``), ``"İ".lower()`` gives two characters (``"i"`` plus
a combining dot) and ``"i".upper()`` gives ``"I"`` (should be ``"İ"``). The
functions here map the two I's explicitly before falling back to ``str``.
"""

from __future__ import annotations

import unicodedata

ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"
UPPER_ALPHABET = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
WORD_LENGTH = 5
LETTER_INDEX: dict[str, int] = {letter: i for i, letter in enumerate(ALPHABET)}

_LOWER_I = str.maketrans({"I": "ı", "İ": "i"})
_UPPER_I = str.maketrans({"i": "İ", "ı": "I"})
_CIRCUMFLEX = str.maketrans({"â": "a", "î": "i", "û": "u"})


def to_lower(text: str) -> str:
    """Lower-case ``text`` with Turkish rules (I -> ı, İ -> i)."""
    return unicodedata.normalize("NFC", text).translate(_LOWER_I).lower()


def to_upper(text: str) -> str:
    """Upper-case ``text`` with Turkish rules (i -> İ, ı -> I)."""
    return unicodedata.normalize("NFC", text).translate(_UPPER_I).upper()


def normalize(text: str) -> str:
    """Strip surrounding whitespace, lower-case (Turkish) and drop circumflexes.

    >>> normalize("  Kâğıt ")
    'kağıt'
    """
    return to_lower(text.strip()).translate(_CIRCUMFLEX)


def is_valid_word(word: str, length: int = WORD_LENGTH) -> bool:
    """True if ``word`` is exactly ``length`` lower-case Turkish letters."""
    return len(word) == length and all(letter in LETTER_INDEX for letter in word)


def sort_key(word: str) -> tuple[int, ...]:
    """Key for sorting in Turkish alphabetical order (c < ç < d, ı < i).

    Characters outside the alphabet sort after all Turkish letters.
    """
    return tuple(LETTER_INDEX.get(c, len(ALPHABET) + ord(c)) for c in word)


def turkish_sorted(words: list[str] | set[str]) -> list[str]:
    """Return ``words`` sorted in Turkish alphabetical order."""
    return sorted(words, key=sort_key)
