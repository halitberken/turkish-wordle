"""Information-gain agents (week 9).

A guess g splits the current candidates by the pattern they would produce.
With p_k the share of candidates (or of their prior weight) in part k, the
expected information of g is H(g) = -sum_k p_k log2 p_k bits. The agent scores
every allowed guess with the pattern table and picks the best one.

Variants (registered names):

* ``entropy``: maximise H over the full guess list, uniform prior;
* ``entropy_candidates``: the same, but only candidates may be guessed;
* ``entropy_freq``: H under a prior that favours frequent words (sigmoid over log-rank);
* ``most_parts``: maximise the number of non-empty parts (Greenberg), ties by H.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from wordle_tr.agents.base import Agent
from wordle_tr.feedback import History
from wordle_tr.pattern_table import PatternTable, partition_stats  # noqa: F401 (re-exported)

def entropy_bits(sizes: Sequence[float]) -> float:
    """Entropy in bits of a partition given by its part sizes (or weights)."""
    c = np.asarray(sizes, dtype=float)
    c = c[c > 0]
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def frequency_prior(answers: list[str], frequencies: dict[str, int], width: float = 0.5,
                    center: float | None = None) -> np.ndarray:
    """Prior weight of each answer: a sigmoid over the log of its frequency rank.

    rank 1 = most frequent in the subtitles. weight = 1 / (1 + exp((ln rank - ln center) / width)),
    with ``center`` = half the list by default, so the top words get almost 1 and the
    least frequent about 0.2.
    """
    n = len(answers)
    center = n / 2 if center is None else center
    order = sorted(range(n), key=lambda i: (-frequencies[answers[i]], i))
    ranks = np.empty(n)
    ranks[order] = np.arange(1, n + 1)
    return 1.0 / (1.0 + np.exp((np.log(ranks) - math.log(center)) / width))


class EntropyAgent(Agent):
    """Picks the guess with the most expected information (or the most parts).

    Ties go to a guess that is itself a candidate, then to the first word in
    Turkish alphabetical order. With at most 2 candidates left it guesses a
    candidate (the most probable one under the prior). The opening guess is the
    same in every game, so it is computed once and cached.
    """

    def __init__(
        self,
        table: PatternTable,
        candidates_only: bool = False,
        prior: np.ndarray | None = None,
        score: str = "entropy",
        name: str = "entropy",
    ) -> None:
        if score not in ("entropy", "parts"):
            raise ValueError(f"score must be 'entropy' or 'parts', not {score!r}")
        self.table = table
        self.candidates_only = candidates_only
        self.prior = None if prior is None else np.asarray(prior, dtype=float)
        self.score = score
        self.name = name
        self.answer_rows = np.array([table.guess_index[w] for w in table.answers], dtype=np.intp)
        self._opening: tuple[str, dict] | None = None
        self.last_choice: dict | None = None  # the scores of the latest decision
        self.searches = 0  # full scoring passes (cache hits are not counted)

    def choose_guess(self, history: History, candidates: list[str]) -> str:
        ids = self.table.answer_ids(candidates)
        opening = len(ids) == len(self.table.answers)
        if opening and self._opening is not None:
            word, self.last_choice = self._opening
            return word
        if len(ids) <= 2:
            best = ids[0] if self.prior is None else ids[int(np.argmax(self.prior[ids]))]
            choice = self._describe(ids, self.answer_rows[best])
        else:
            choice = self.rank(ids, 1)[0]
        self.last_choice = choice
        if opening:
            self._opening = (choice["guess"], choice)
        return choice["guess"]

    def rank(self, ids: np.ndarray, k: int = 10) -> list[dict]:
        """The ``k`` best guesses for the candidates ``ids``, best first."""
        rows, bits, parts, is_candidate = self._ranked(ids, k)
        return [{"guess": self.table.guesses[r], "bits": float(b), "parts": int(m), "is_candidate": bool(c),
                 "candidates": len(ids)} for r, b, m, c in zip(rows, bits, parts, is_candidate)]

    def top_rows(self, ids: np.ndarray, k: int) -> np.ndarray:
        """Guess rows of the ``k`` best guesses, best first (the first is the agent's choice)."""
        return self._ranked(ids, k)[0]

    def _ranked(self, ids: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        self.searches += 1
        rows = self.answer_rows[ids] if self.candidates_only else np.arange(len(self.table.guesses))
        weights = None if self.prior is None else self.prior[ids]
        bits, parts = partition_stats(self.table.matrix, ids, rows if self.candidates_only else None, weights)
        is_candidate = np.zeros(len(self.table.guesses), dtype=bool)
        is_candidate[self.answer_rows[ids]] = True
        rounded = np.round(bits, 9)  # equal partitions must compare equal despite rounding noise
        keys = [rows, ~is_candidate[rows], -rounded]
        if self.score == "parts":
            keys.append(-parts)
        order = np.lexsort(keys)[:k]
        return rows[order], bits[order], parts[order], is_candidate[rows[order]]

    def _describe(self, ids: np.ndarray, row: int) -> dict:
        weights = None if self.prior is None else self.prior[ids]
        bits, parts = partition_stats(self.table.matrix, ids, np.array([row]), weights)
        return {"guess": self.table.guesses[row], "bits": float(bits[0]), "parts": int(parts[0]),
                "is_candidate": True, "candidates": len(ids)}
