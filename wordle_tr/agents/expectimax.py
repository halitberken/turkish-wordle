"""Depth-limited expectimax (week 10): agent nodes choose a guess, chance nodes draw a pattern.

    Q_d(C, g) = 1 + sum_{p != all green} |C_p| / |C| * V_{d-1}(C_p)
    V_d(C)    = 1 if |C| = 1,  1.5 if |C| = 2,  min over the beam of Q_d(C, g) otherwise
    V_0(C)    = expected number of guesses of the entropy agent from C (exact, by recursion)

The value is the expected number of guesses still needed, so the agent
minimises it. At each agent node only the ``width`` best guesses by entropy are
tried (the beam); ``width=None`` tries every different split (exact search).
Values are memoised per (candidate set, depth), and a guess is abandoned as soon
as its lower bound (2 - 1/s per part of size s) reaches the best value found.

The leaf value is the entropy agent's own expected score, and the entropy
agent's choice is always first in the beam. So this is a rollout of the entropy
policy: in expectation it is never worse than the entropy agent.
"""

from __future__ import annotations

import math

import numpy as np

from wordle_tr.agents.base import Agent
from wordle_tr.agents.entropy import EntropyAgent
from wordle_tr.feedback import History
from wordle_tr.oracle import distinct_splits, lower_bound
from wordle_tr.pattern_table import PatternTable, split


class ExpectimaxAgent(Agent):
    """Chooses the guess with the lowest expected number of remaining guesses (bounded search)."""

    def __init__(self, table: PatternTable, depth: int = 2, width: int | None = 10,
                 name: str = "expectimax") -> None:
        if depth < 1:
            raise ValueError("depth must be at least 1")
        if width is not None and width < 1:
            raise ValueError("width must be at least 1 (or None for every guess)")
        self.table = table
        self.matrix = table.matrix
        self.depth = depth
        self.width = width
        self.name = name
        self.entropy = EntropyAgent(table)
        self.answer_rows = self.entropy.answer_rows
        self._top: dict[bytes, np.ndarray] = {}  # candidate set -> best guess rows by entropy
        self._beams: dict[bytes, list[int]] = {}
        self._rollout: dict[bytes, float] = {}  # candidate set -> V_0
        self._values: dict[tuple[bytes, int], tuple[float, int]] = {}  # (set, depth) -> (V_d, guess row)
        self._opening: tuple[str, dict] | None = None
        self.last_choice: dict | None = None
        self.nodes = 0  # agent nodes expanded

    def choose_guess(self, history: History, candidates: list[str]) -> str:
        ids = np.sort(self.table.answer_ids(candidates))
        opening = len(ids) == len(self.table.answers)
        if opening and self._opening is not None:
            word, self.last_choice = self._opening
            return word
        value, row = self.search(ids, self.depth)
        guess = self.table.guesses[row]
        self.last_choice = {"guess": guess, "expected_guesses": value, "candidates": len(ids),
                            "is_candidate": bool(np.isin(row, self.answer_rows[ids]))}
        if opening:
            self._opening = (guess, self.last_choice)
        return guess

    def search(self, ids: np.ndarray, depth: int) -> tuple[float, int]:
        """(V_depth(ids), best guess row) for sorted candidate ids."""
        n = len(ids)
        if n <= 2:
            return (1.0 if n == 1 else 1.5), int(self.answer_rows[ids[0]])
        if depth == 0:
            return self.rollout_value(ids), int(self.top_rows(ids)[0])
        key = (ids.tobytes(), depth)
        if key in self._values:
            return self._values[key]
        self.nodes += 1
        best, best_row = math.inf, -1
        for row in self.beam(ids):
            parts = split(self.matrix, row, ids)
            if len(parts) == 1 and len(parts[0]) == n:
                continue  # no information
            total = 1.0 + sum(len(p) * lower_bound(len(p)) for p in parts) / n
            for part in sorted(parts, key=len, reverse=True):
                if total >= best:
                    break
                value, _ = self.search(part, depth - 1)
                total += len(part) * (value - lower_bound(len(part))) / n
            if total < best - 1e-12:  # ties keep the earlier (higher-entropy) guess
                best, best_row = total, row
        self._values[key] = (best, best_row)
        return best, best_row

    def rollout_value(self, ids: np.ndarray) -> float:
        """V_0: the exact expected number of guesses of the entropy agent from ``ids``."""
        n = len(ids)
        if n <= 2:
            return 1.0 if n == 1 else 1.5
        key = ids.tobytes()
        if key not in self._rollout:
            row = int(self.top_rows(ids)[0])
            self._rollout[key] = 1.0 + sum(len(p) * self.rollout_value(p)
                                           for p in split(self.matrix, row, ids)) / n
        return self._rollout[key]

    def top_rows(self, ids: np.ndarray) -> np.ndarray:
        """The best guesses by entropy (the entropy agent's own ranking), cached per set."""
        key = ids.tobytes()
        if key not in self._top:
            self._top[key] = self.entropy.top_rows(ids, self.width or 1)
        return self._top[key]

    def beam(self, ids: np.ndarray) -> list[int]:
        key = ids.tobytes()
        if key not in self._beams:
            if self.width is None:
                rows = [row for _, row, _ in distinct_splits(self.matrix, ids)]
                entropy_row = int(self.top_rows(ids)[0])
                self._beams[key] = [entropy_row] + [r for r in rows if r != entropy_row]
            else:
                self._beams[key] = [int(r) for r in self.top_rows(ids)]
        return self._beams[key]
