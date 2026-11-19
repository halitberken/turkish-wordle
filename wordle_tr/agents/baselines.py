"""Baseline agents: a random candidate, and the candidate with the most common letters."""

from __future__ import annotations

import random
from collections import Counter

from wordle_tr.agents.base import Agent
from wordle_tr.alphabet import sort_key
from wordle_tr.feedback import History


class RandomAgent(Agent):
    """Guesses a uniformly random candidate. The random stream is seeded once
    and continues across games, so a run is reproducible for a given seed and
    order of games."""

    name = "random"
    deterministic = False

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def choose_guess(self, history: History, candidates: list[str]) -> str:
        return self.rng.choice(candidates)


class LetterFrequencyAgent(Agent):
    """Guesses the candidate whose distinct letters occur in the most candidates.

    score(w) = sum over the distinct letters L of w of |{c in candidates : L in c}|.
    Ties go to the first word in Turkish alphabetical order.
    """

    name = "frequency"

    def __init__(self) -> None:
        self._first: tuple[tuple[str, ...], str] | None = None

    def choose_guess(self, history: History, candidates: list[str]) -> str:
        if not history and self._first is not None and self._first[0] == tuple(candidates):
            return self._first[1]  # the opening position is the same in every game
        guess = best_by_letter_frequency(candidates)
        if not history:
            self._first = (tuple(candidates), guess)
        return guess


def best_by_letter_frequency(candidates: list[str]) -> str:
    counts = Counter(letter for word in candidates for letter in set(word))
    return min(candidates, key=lambda w: (-sum(counts[c] for c in set(w)), sort_key(w)))
