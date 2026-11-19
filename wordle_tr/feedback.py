"""Wordle feedback, pattern encoding, display helpers and the reference candidate filter.

Pattern encoding: the five colours are the digits of a base-3 number, grey = 0,
yellow = 1, green = 2, with position 0 (the first letter) as the most
significant digit. Patterns are therefore 0..242, and 242 (all green) is
``ALL_GREEN``. Example: green, green, grey, grey, grey = 22000 in base 3 = 216.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from wordle_tr.alphabet import WORD_LENGTH, to_upper

GREY, YELLOW, GREEN = 0, 1, 2
NUM_PATTERNS = 3**WORD_LENGTH
ALL_GREEN = NUM_PATTERNS - 1
ALL_GREY = 0

History = list[tuple[str, int]]

EMOJI = {GREY: "⬜", YELLOW: "🟨", GREEN: "🟩"}
LETTERS = {GREY: "x", YELLOW: "y", GREEN: "g"}
_PARSE = {
    "g": GREEN, "🟩": GREEN,
    "y": YELLOW, "🟨": YELLOW,
    "x": GREY, ".": GREY, "⬜": GREY, "⬛": GREY,
}


def feedback(guess: str, answer: str) -> int:
    """Pattern of ``guess`` against ``answer`` (standard two-pass duplicate rule).

    Pass 1 marks greens and collects the answer's unmatched letters. Pass 2 goes
    left to right: a non-green letter is yellow if an unused copy is left
    (the copy is consumed), otherwise grey.
    """
    if guess == answer:
        return ALL_GREEN
    unmatched = [a for g, a in zip(guess, answer) if g != a]
    pattern = 0
    for g, a in zip(guess, answer):
        if g == a:
            pattern = pattern * 3 + GREEN
        elif g in unmatched:
            unmatched.remove(g)
            pattern = pattern * 3 + YELLOW
        else:
            pattern = pattern * 3
    return pattern


def encode_colors(colors: Sequence[int]) -> int:
    """Colours (0/1/2 per position) -> pattern number."""
    if len(colors) != WORD_LENGTH or any(c not in (GREY, YELLOW, GREEN) for c in colors):
        raise ValueError(f"expected {WORD_LENGTH} colours in 0..2, got {list(colors)}")
    pattern = 0
    for color in colors:
        pattern = pattern * 3 + color
    return pattern


def decode_pattern(pattern: int) -> list[int]:
    """Pattern number -> list of colours (position 0 first)."""
    if not 0 <= pattern < NUM_PATTERNS:
        raise ValueError(f"pattern must be in 0..{NUM_PATTERNS - 1}, got {pattern}")
    colors = []
    for _ in range(WORD_LENGTH):
        colors.append(pattern % 3)
        pattern //= 3
    return colors[::-1]


def pattern_to_emoji(pattern: int) -> str:
    """E.g. 216 -> '🟩🟩⬜⬜⬜'."""
    return "".join(EMOJI[c] for c in decode_pattern(pattern))


def pattern_to_text(pattern: int) -> str:
    """E.g. 216 -> 'ggxxx' (the format accepted by :func:`parse_pattern`)."""
    return "".join(LETTERS[c] for c in decode_pattern(pattern))


def parse_pattern(text: str) -> int:
    """Parse a typed pattern: g = green, y = yellow, x or . = grey; emoji also work.

    >>> parse_pattern("ggy..") == encode_colors([2, 2, 1, 0, 0])
    True
    """
    symbols = [c for c in text.strip().lower() if c not in " ️"]
    if len(symbols) != WORD_LENGTH or any(c not in _PARSE for c in symbols):
        raise ValueError(
            f"pattern must be {WORD_LENGTH} symbols of g (green), y (yellow), x or . (grey), "
            f"or ⬜🟨🟩; got {text!r}")
    return encode_colors([_PARSE[c] for c in symbols])


def render_guess(guess: str, pattern: int, color: bool = True) -> str:
    """One row of tiles: ANSI-coloured letters, or the word followed by emoji."""
    if not color:
        return f"{to_upper(guess)}  {pattern_to_emoji(pattern)}"
    style = {GREEN: "\x1b[1;97;42m", YELLOW: "\x1b[1;30;43m", GREY: "\x1b[1;97;100m"}
    return " ".join(f"{style[c]} {to_upper(letter)} \x1b[0m"
                    for letter, c in zip(guess, decode_pattern(pattern)))


def letter_states(history: History) -> dict[str, int]:
    """Best colour seen so far for each guessed letter (green > yellow > grey)."""
    states: dict[str, int] = {}
    for guess, pattern in history:
        for letter, c in zip(guess, decode_pattern(pattern)):
            states[letter] = max(states.get(letter, GREY), c)
    return states


def is_consistent(word: str, history: History) -> bool:
    """True if ``word`` could be the answer given every (guess, pattern) so far."""
    return all(feedback(guess, word) == pattern for guess, pattern in history)


def filter_candidates(candidates: Iterable[str], guess: str, pattern: int) -> list[str]:
    """Reference filter: keep the words that would have produced ``pattern``."""
    return [w for w in candidates if feedback(guess, w) == pattern]
