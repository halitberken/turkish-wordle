"""Precomputed feedback for every (guess, answer) pair: M[g, a] = feedback(g, a) as uint8.

The matrix is computed with numpy, without a Python loop over pairs, and is
cached in data/cache/ under a hash of the two word lists (a changed list means
a new file, so the table is rebuilt).
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from wordle_tr import DATA_DIR
from wordle_tr.alphabet import WORD_LENGTH
from wordle_tr.feedback import NUM_PATTERNS
from wordle_tr.words import encode, load_answers, load_guesses

CACHE_DIR = DATA_DIR / "cache"
_WEIGHTS = 3 ** np.arange(WORD_LENGTH - 1, -1, -1)  # 81, 27, 9, 3, 1: position 0 most significant
_EARLIER = np.tri(WORD_LENGTH, k=-1, dtype=bool)  # _EARLIER[i, k] is True when k < i


def compute_pattern_matrix(guesses: list[str], answers: list[str], chunk: int = 256) -> np.ndarray:
    """``M[g, a] = feedback(guesses[g], answers[a])`` for all pairs, vectorised.

    Greens: the guess and answer letters agree. A non-green position i with
    letter L is yellow iff the number of L's among the answer's non-green
    positions is greater than the number of non-green L's in the guess before i
    (this is the left-to-right rule written as counts). Both counts come from
    5 x 5 letter-equality matrices.
    """
    g_codes, a_codes = encode(guesses), encode(answers)
    matrix = np.empty((len(guesses), len(answers)), dtype=np.uint8)
    for start in range(0, len(guesses), chunk):
        g = g_codes[start:start + chunk]  # (c, 5)
        green = g[:, None, :] == a_codes[None, :, :]  # (c, n, 5)
        not_green = ~green
        # equal[x, y, i, j]: guess letter i equals answer letter j
        equal = g[:, None, :, None] == a_codes[None, :, None, :]  # (c, n, 5, 5)
        in_answer = (equal & not_green[:, :, None, :]).sum(axis=3)  # L among answer's non-green
        same = (g[:, :, None] == g[:, None, :]) & _EARLIER  # (c, 5, 5): earlier copy of the same letter
        before = (same[:, None, :, :] & not_green[:, :, None, :]).sum(axis=3)  # earlier non-green L's
        yellow = not_green & (in_answer > before)
        digits = 2 * green.astype(np.uint8) + yellow.astype(np.uint8)
        matrix[start:start + chunk] = digits @ _WEIGHTS
    return matrix


def lists_hash(guesses: list[str], answers: list[str]) -> str:
    text = "\n".join(guesses) + "\n\0\n" + "\n".join(answers)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class PatternTable:
    """Feedback lookups and fast filtering on answer ids (indices into ``answers``)."""

    def __init__(self, guesses: list[str], answers: list[str], matrix: np.ndarray) -> None:
        if matrix.shape != (len(guesses), len(answers)):
            raise ValueError(f"matrix shape {matrix.shape} does not match the word lists")
        self.guesses = list(guesses)
        self.answers = list(answers)
        self.matrix = matrix
        self.guess_index = {w: i for i, w in enumerate(self.guesses)}
        self.answer_index = {w: i for i, w in enumerate(self.answers)}

    @classmethod
    def load_or_build(
        cls,
        guesses: list[str] | None = None,
        answers: list[str] | None = None,
        cache_dir: Path = CACHE_DIR,
    ) -> PatternTable:
        """Load the cached table for these lists, or build and cache it."""
        guesses = load_guesses() if guesses is None else guesses
        answers = load_answers() if answers is None else answers
        path = Path(cache_dir) / f"pattern_table_{lists_hash(guesses, answers)}.npy"
        if path.exists():
            matrix = np.load(path)
            if matrix.shape == (len(guesses), len(answers)) and matrix.dtype == np.uint8:
                return cls(guesses, answers, matrix)
        matrix = compute_pattern_matrix(guesses, answers)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp.npy")
        np.save(tmp, matrix)
        os.replace(tmp, path)  # atomic, in case two processes build at once
        return cls(guesses, answers, matrix)

    def _row(self, guess: int | str) -> int:
        return self.guess_index[guess] if isinstance(guess, str) else int(guess)

    def pattern(self, guess: int | str, answer: int | str) -> int:
        a = self.answer_index[answer] if isinstance(answer, str) else int(answer)
        return int(self.matrix[self._row(guess), a])

    def all_ids(self) -> np.ndarray:
        return np.arange(len(self.answers), dtype=np.intp)

    def answer_ids(self, words: Iterable[str]) -> np.ndarray:
        return np.fromiter((self.answer_index[w] for w in words), dtype=np.intp)

    def words(self, ids: np.ndarray) -> list[str]:
        return [self.answers[i] for i in ids]

    def filter_ids(self, ids: np.ndarray, guess: int | str, pattern: int) -> np.ndarray:
        """The answer ids in ``ids`` that give ``pattern`` for ``guess`` (order kept)."""
        return ids[self.matrix[self._row(guess), ids] == pattern]

    def filter_words(self, words: Iterable[str], guess: int | str, pattern: int) -> list[str]:
        return self.words(self.filter_ids(self.answer_ids(words), guess, pattern))

    def partition_counts(self, guess: int | str, ids: np.ndarray) -> np.ndarray:
        """How many of ``ids`` fall into each of the 243 patterns of ``guess``."""
        return np.bincount(self.matrix[self._row(guess), ids], minlength=NUM_PATTERNS)
