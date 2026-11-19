"""The Wordle environment: one hidden word, a guess limit and the feedback history."""

from __future__ import annotations

from collections.abc import Iterable

from wordle_tr.alphabet import WORD_LENGTH, is_valid_word, normalize, to_upper
from wordle_tr.feedback import ALL_GREEN, History, feedback


class InvalidGuessError(ValueError):
    """The guess was rejected; it does not use up a turn."""


class WordleGame:
    """A single game. ``max_guesses=None`` means unlimited guesses (used in experiments)."""

    def __init__(
        self,
        answer: str,
        allowed_guesses: Iterable[str] | None = None,
        max_guesses: int | None = 6,
    ) -> None:
        self.answer = normalize(answer)
        if not is_valid_word(self.answer):
            raise ValueError(f"answer must be {WORD_LENGTH} Turkish letters: {answer!r}")
        if allowed_guesses is None or isinstance(allowed_guesses, (set, frozenset)):
            self.allowed = allowed_guesses
        else:
            self.allowed = frozenset(allowed_guesses)
        if self.allowed is not None and self.answer not in self.allowed:
            raise ValueError(f"answer {answer!r} is not in the allowed guesses")
        if max_guesses is not None and max_guesses < 1:
            raise ValueError("max_guesses must be at least 1 (or None for unlimited)")
        self.max_guesses = max_guesses
        self.history: History = []

    @property
    def guesses_used(self) -> int:
        return len(self.history)

    @property
    def won(self) -> bool:
        return bool(self.history) and self.history[-1][1] == ALL_GREEN

    @property
    def over(self) -> bool:
        return self.won or (self.max_guesses is not None and self.guesses_used >= self.max_guesses)

    def play(self, guess: str) -> int:
        """Score ``guess`` and record it. Invalid guesses raise and are not counted."""
        if self.over:
            raise InvalidGuessError("the game is over")
        word = normalize(guess)
        if not is_valid_word(word):
            raise InvalidGuessError(f"{guess.strip()!r} is not {WORD_LENGTH} Turkish letters")
        if self.allowed is not None and word not in self.allowed:
            raise InvalidGuessError(f"{to_upper(word)} is not in the word list")
        pattern = feedback(word, self.answer)
        self.history.append((word, pattern))
        return pattern
