"""Exact minimum expected number of guesses (Bellman recursion) for small candidate sets.

    V*(C) = 1                                               if |C| = 1
    V*(C) = min_g [ 1 + sum_{p != all green} |C_p|/|C| * V*(C_p) ]   otherwise

where C_p are the candidates that give pattern p for guess g. Every allowed
guess is considered. The search is a depth-first branch and bound:

* guesses that split C the same way are merged;
* options are tried in order of a lower bound, so good solutions come first;
* a branch stops as soon as its lower bound reaches the best value found;
* exact values and proven lower bounds are memoised per candidate set.

Lower bounds. A set of s candidates needs at least 2 - 1/s guesses on average:
at best one guess (a candidate) separates all the others, which then need one
guess each. One step deeper: a guess g that splits n candidates into m parts
(the all-green part included) leaves parts of size s that need at least
2 - 1/s each, which adds up to

    V*(C) >= 1 + (2n - m(g) - [g is a candidate]) / n   for the best g,

so the guesses with the most parts (ties: candidates) give the best bound.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from wordle_tr.feedback import ALL_GREEN
from wordle_tr.pattern_table import PatternTable, partition_stats, split

if TYPE_CHECKING:
    from wordle_tr.agents.base import Agent

DEEP_BOUND_MIN_SIZE = 8  # below this, 2 - 1/s is already close and solving is cheap


def lower_bound(size: int) -> float:
    """No strategy can do better than 2 - 1/s on s candidates (1 for a single candidate)."""
    return 2.0 - 1.0 / size


def parts_bound(matrix: np.ndarray, ids: np.ndarray, answer_rows: np.ndarray) -> float:
    """The one-step lower bound 1 + (2n - max_g(parts + [g is a candidate])) / n."""
    n = len(ids)
    _, parts = partition_stats(matrix, ids)
    score = parts.astype(np.int64)
    score[answer_rows[ids]] += 1
    return 1.0 + (2 * n - int(score.max())) / n


def distinct_splits(matrix: np.ndarray, ids: np.ndarray) -> list[tuple[float, int, list[np.ndarray]]]:
    """One (lower bound, guess row, parts) per different way the guesses split ``ids``.

    Guesses that give no information (one part equal to all of ``ids``) are left out.
    Sorted by the lower bound 1 + sum |P|/n * (2 - 1/|P|), then by Turkish order.
    """
    n = len(ids)
    rows_patterns, first_rows = np.unique(matrix[:, ids], axis=0, return_index=True)
    seen: set[tuple] = set()
    options = []
    for patterns, row in sorted(zip(rows_patterns, first_rows), key=lambda item: item[1]):
        labels: dict[int, int] = {}
        signature = tuple(labels.setdefault(int(p), len(labels)) if p != ALL_GREEN else -1 for p in patterns)
        if signature in seen:
            continue
        seen.add(signature)
        parts = split(matrix, int(row), ids)
        if len(parts) == 1 and len(parts[0]) == n:
            continue
        bound = 1.0 + sum(len(p) * lower_bound(len(p)) for p in parts) / n
        options.append((bound, int(row), parts))
    options.sort(key=lambda option: (option[0], option[1]))
    return options


class Oracle:
    """Exact V*(C) by branch and bound; feasible for small candidate sets."""

    def __init__(self, table: PatternTable) -> None:
        self.table = table
        self.answer_rows = np.array([table.guess_index[w] for w in table.answers], dtype=np.intp)
        self.exact: dict[bytes, tuple[float, int]] = {}  # candidate set -> (V*, best guess row)
        self.lower: dict[bytes, float] = {}  # candidate set -> proven lower bound
        self.nodes = 0  # candidate sets expanded

    def bound(self, ids: np.ndarray) -> float:
        """Best known lower bound for V*(ids) (computes the one-step bound for larger sets)."""
        n = len(ids)
        if n <= 2:
            return 1.0 if n == 1 else 1.5
        key = ids.tobytes()
        if key in self.exact:
            return self.exact[key][0]
        if key not in self.lower:
            deep = parts_bound(self.table.matrix, ids, self.answer_rows) if n >= DEEP_BOUND_MIN_SIZE else 0.0
            self.lower[key] = max(lower_bound(n), deep)
        return self.lower[key]

    def value(self, ids: np.ndarray, bound: float = math.inf) -> float:
        """V*(ids) if it is below ``bound``; otherwise some value >= ``bound``."""
        n = len(ids)
        if n == 1:
            return 1.0
        if n == 2:
            return 1.5
        key = ids.tobytes()
        if key in self.exact:
            return self.exact[key][0]
        floor = self.bound(ids)
        if floor >= bound:
            return floor
        self.nodes += 1
        best, best_row = bound, -1
        for option_bound, row, parts in distinct_splits(self.table.matrix, ids):
            if option_bound >= best:
                break  # sorted: no later option can be better
            q = self._q_value(parts, n, best)
            if q < best:
                best, best_row = q, row
        if best_row < 0:
            self.lower[key] = max(floor, bound)  # proved: nothing below the bound
            return max(floor, bound)
        self.exact[key] = (best, best_row)
        return best

    def _q_value(self, parts: list[np.ndarray], n: int, best: float) -> float:
        """1 + sum |P|/n * V*(P), or a value >= ``best`` as soon as that is certain."""
        bounds = [self.bound(p) for p in parts]
        total = 1.0 + sum(len(p) * b for p, b in zip(parts, bounds)) / n
        for p, b in sorted(zip(parts, bounds), key=lambda item: -len(item[0])):
            if total >= best:
                return total
            weight = len(p) / n
            v = self.value(p, bound=b + (best - total) / weight)
            total += weight * (v - b)
        return total

    def solve(self, words: list[str]) -> tuple[float, str]:
        """V* and an optimal first guess for the candidate set ``words`` (answers)."""
        ids = np.sort(self.table.answer_ids(words))
        if len(ids) <= 2:
            return self.value(ids), self.table.answers[ids[0]]
        v = self.value(ids)
        return v, self.table.guesses[self.exact[ids.tobytes()][1]]

    def best_row(self, ids: np.ndarray) -> int:
        self.value(ids)
        return self.exact[ids.tobytes()][1]


def policy_value(agent: Agent, table: PatternTable, ids: np.ndarray, memo: dict | None = None) -> float:
    """Exact expected number of guesses of ``agent`` from the candidates ``ids`` (uniform hidden word).

    Follows the agent's own choices through every pattern; over the full answer
    list this equals the mean of an evaluation over all answers.
    """
    memo = {} if memo is None else memo
    n = len(ids)
    key = ids.tobytes()
    if key not in memo:
        guess = agent.choose_guess([], table.words(ids))
        parts = split(table.matrix, table.guess_index[guess], ids)
        memo[key] = 1.0 + sum(len(p) * policy_value(agent, table, p, memo) for p in parts) / n
    return memo[key]


def opener_lower_bound(table: PatternTable) -> tuple[float, str]:
    """Lower bound on the optimum over all openers: 1 + (2n - max_g(parts + [g is an answer])) / n."""
    ids = table.all_ids()
    answer_rows = np.array([table.guess_index[w] for w in table.answers], dtype=np.intp)
    _, parts = partition_stats(table.matrix, ids)
    score = parts.astype(np.int64)
    score[answer_rows] += 1
    best = int(np.argmax(score))
    return 1.0 + (2 * len(ids) - int(score[best])) / len(ids), table.guesses[best]
