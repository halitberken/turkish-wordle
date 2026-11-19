"""Constraints implied by (guess, pattern) observations.

Four kinds, per observation:

* fixed letter:     green  -> that letter at that position;
* forbidden letter: yellow/grey -> that letter not at that position;
* minimum count:    k = green + yellow copies of L in the guess -> L appears >= k times;
* exact count:      if any copy of L is grey -> L appears exactly k times (k = 0: absent).

Several observations combine by taking the max of the minimums and the min of the
maximums. For a real pattern p = f(g, s), a word satisfies the constraints of
(g, p) exactly when f(g, w) = p (proof in docs/week8).
"""

from __future__ import annotations

from wordle_tr.alphabet import ALPHABET, WORD_LENGTH, sort_key, to_upper
from wordle_tr.feedback import GREEN, GREY, YELLOW, History, decode_pattern


class ContradictionError(ValueError):
    """The observations cannot all be true for any word."""


class Constraints:
    """Accumulated knowledge about the hidden word."""

    def __init__(self) -> None:
        self.fixed: list[str | None] = [None] * WORD_LENGTH
        self.forbidden: list[set[str]] = [set() for _ in range(WORD_LENGTH)]
        self.min_count: dict[str, int] = {}
        self.max_count: dict[str, int] = {}
        self._checks: tuple | None = None  # compiled form for is_satisfied, built on demand

    @classmethod
    def from_history(cls, history: History) -> Constraints:
        constraints = cls()
        for guess, pattern in history:
            constraints.add_observation(guess, pattern)
        return constraints

    def add_observation(self, guess: str, pattern: int) -> None:
        """Add the constraints of one observation.

        Raises :class:`ContradictionError` (and leaves ``self`` unchanged) if the
        pattern is impossible or contradicts earlier observations.
        """
        colors = decode_pattern(pattern)
        _check_pattern_is_possible(guess, colors)
        new = self.copy()
        for i, (letter, color) in enumerate(zip(guess, colors)):
            if color == GREEN:
                if new.fixed[i] not in (None, letter):
                    raise ContradictionError(
                        f"letter {i + 1} cannot be both {to_upper(new.fixed[i])} and {to_upper(letter)}")
                new.fixed[i] = letter
            else:
                new.forbidden[i].add(letter)
        for letter in set(guess):
            marks = [c for g, c in zip(guess, colors) if g == letter]
            k = sum(c != GREY for c in marks)
            new.min_count[letter] = max(new.min_count.get(letter, 0), k)
            if GREY in marks:
                new.max_count[letter] = min(new.max_count.get(letter, WORD_LENGTH), k)
        new._check()
        self.__dict__.update(new.__dict__)

    def copy(self) -> Constraints:
        new = Constraints()
        new.fixed = list(self.fixed)
        new.forbidden = [set(s) for s in self.forbidden]
        new.min_count = dict(self.min_count)
        new.max_count = dict(self.max_count)
        return new

    def is_satisfied(self, word: str) -> bool:
        """True if ``word`` satisfies every constraint."""
        if self._checks is None:
            self._checks = self._compile()
        fixed, forbidden, absent, counts = self._checks
        for i, letter in fixed:
            if word[i] != letter:
                return False
        for i, letters in forbidden:
            if word[i] in letters:
                return False
        if not absent.isdisjoint(word):
            return False
        for letter, lo, hi in counts:
            n = word.count(letter)
            if n < lo or n > hi:
                return False
        return True

    def _compile(self) -> tuple:
        """Only the checks that are not implied by others, as tuples (fast to loop over)."""
        absent = frozenset(self.absent_letters())
        fixed = tuple((i, c) for i, c in enumerate(self.fixed) if c is not None)
        forbidden = tuple((i, frozenset(s - absent)) for i, s in enumerate(self.forbidden)
                          if self.fixed[i] is None and s - absent)
        counts = []
        for letter in sorted(set(self.min_count) | set(self.max_count), key=sort_key):
            lo, hi = self.min_count.get(letter, 0), self.max_count.get(letter, WORD_LENGTH)
            if letter not in absent and (lo > self.fixed.count(letter) or hi < WORD_LENGTH):
                counts.append((letter, lo, hi))
        return fixed, forbidden, absent, tuple(counts)

    def absent_letters(self) -> set[str]:
        return {letter for letter, k in self.max_count.items() if k == 0}

    def domains(self) -> list[set[str]]:
        """Letters still allowed at each position (node consistency)."""
        absent = self.absent_letters()
        return [
            {fixed} if fixed is not None else set(ALPHABET) - self.forbidden[i] - absent
            for i, fixed in enumerate(self.fixed)
        ]

    def describe(self) -> str:
        """Known facts in plain English, e.g. 'Letter 1 is K; not in word: P; A is not elsewhere'."""
        facts = [f"letter {i + 1} is {to_upper(letter)}"
                 for i, letter in enumerate(self.fixed) if letter is not None]
        absent = sorted(self.absent_letters(), key=sort_key)
        if absent:
            facts.append("not in word: " + ", ".join(to_upper(c) for c in absent))
        present = sorted((c for c, k in self.min_count.items() if k > 0), key=sort_key)
        for letter in present:
            placed = self.fixed.count(letter)
            lo, hi = self.min_count[letter], self.max_count.get(letter, WORD_LENGTH)
            big = to_upper(letter)
            if lo > placed:
                fact = f"contains {big}"
                if hi == lo:
                    fact += " exactly " + _times(lo)
                elif lo > 1:
                    fact += " at least " + _times(lo)
                excluded = [i + 1 for i in range(WORD_LENGTH)
                            if letter in self.forbidden[i] and self.fixed[i] is None]
                if excluded:
                    fact += ", not as letter " + _join_or(excluded)
                facts.append(fact)
            elif hi == placed:
                facts.append(f"{big} is not elsewhere")
        if not facts:
            return "Nothing known yet"
        text = "; ".join(facts)
        return text[0].upper() + text[1:]

    def _check(self) -> None:
        for i, letter in enumerate(self.fixed):
            if letter is not None and letter in self.forbidden[i]:
                raise ContradictionError(f"letter {i + 1} cannot be both {to_upper(letter)} and not {to_upper(letter)}")
        for letter, k in self.max_count.items():
            if self.min_count.get(letter, 0) > k:
                raise ContradictionError(
                    f"{to_upper(letter)} must appear at least {self.min_count[letter]} and at most {k} times")
            if self.fixed.count(letter) > k:
                raise ContradictionError(f"{to_upper(letter)} is fixed more often than it may appear")
        if sum(self.min_count.values()) > WORD_LENGTH:
            raise ContradictionError(f"more than {WORD_LENGTH} letters are required")
        domains = self.domains()
        for i, domain in enumerate(domains):
            if not domain:
                raise ContradictionError(f"no letter is possible at position {i + 1}")
        for letter, k in self.min_count.items():
            if sum(letter in d for d in domains) < k:
                raise ContradictionError(f"{to_upper(letter)} has no room left in the word")


def _check_pattern_is_possible(guess: str, colors: list[int]) -> None:
    """Among the non-green copies of a letter, yellows always come before greys."""
    seen_grey: set[str] = set()
    for i, (letter, color) in enumerate(zip(guess, colors)):
        if color == GREY:
            seen_grey.add(letter)
        elif color == YELLOW and letter in seen_grey:
            raise ContradictionError(
                f"impossible pattern: the yellow {to_upper(letter)} at letter {i + 1} would have "
                f"gone to the earlier grey {to_upper(letter)}")


def _times(n: int) -> str:
    return {1: "once", 2: "twice"}.get(n, f"{n} times")


def _join_or(numbers: list[int]) -> str:
    items = [str(n) for n in numbers]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]
