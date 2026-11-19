"""Candidate filters behind one interface.

``filter_fn(candidates, history)`` returns the words of ``candidates`` that are
consistent with every (guess, pattern) in ``history``, in the same order.
``candidates`` must be a subset of the answer list in its (Turkish) order.
The game loop calls it after every guess with the full history, so a method
may use everything known so far (the CSP does) or just filter step by step.

* ``feedback``: reference, recompute feedback(guess, w) for every candidate;
* ``constraints``: check the combined ``Constraints`` of the history on each word;
* ``csp``: backtracking with forward checking in a trie of the answer list;
* ``table``: look the patterns up in the precomputed ``PatternTable``.
"""

from __future__ import annotations

from collections.abc import Callable

from wordle_tr.constraints import Constraints
from wordle_tr.csp_solver import CSPSolver
from wordle_tr.feedback import History, filter_candidates
from wordle_tr.pattern_table import PatternTable
from wordle_tr.words import load_answers

FilterFn = Callable[[list[str], History], list[str]]
FILTER_NAMES = ("feedback", "constraints", "csp", "table")


def filter_reference(candidates: list[str], history: History) -> list[str]:
    for guess, pattern in history:
        candidates = filter_candidates(candidates, guess, pattern)
    return list(candidates)


def filter_constraints(candidates: list[str], history: History) -> list[str]:
    constraints = Constraints.from_history(history)
    return [w for w in candidates if constraints.is_satisfied(w)]


class CSPFilter:
    """Solves the CSP of the whole history over the answer trie, then keeps the candidates."""

    def __init__(self, answers: list[str]) -> None:
        self.solver = CSPSolver(answers)
        self.num_answers = len(answers)
        self.nodes_expanded = 0  # running total, for statistics

    def __call__(self, candidates: list[str], history: History) -> list[str]:
        result = self.solver.solve(Constraints.from_history(history))
        self.nodes_expanded += result.nodes_expanded
        if len(candidates) == self.num_answers:  # all answers: nothing to intersect
            return result.solutions
        keep = set(candidates)
        return [w for w in result.solutions if w in keep]


class TableFilter:
    """Filters answer ids with ``PatternTable.filter_ids`` (one array lookup per guess)."""

    def __init__(self, table: PatternTable) -> None:
        self.table = table

    def __call__(self, candidates: list[str], history: History) -> list[str]:
        if len(candidates) == len(self.table.answers):
            ids = self.table.all_ids()
        else:
            ids = self.table.answer_ids(candidates)
        for guess, pattern in history:
            ids = self.table.filter_ids(ids, guess, pattern)
        return self.table.words(ids)


def make_filter(
    name: str,
    answers: list[str] | None = None,
    guesses: list[str] | None = None,
    table: PatternTable | None = None,
) -> FilterFn:
    """Build the filter called ``name`` (the CSP and the table need the word lists)."""
    if name == "feedback":
        return filter_reference
    if name == "constraints":
        return filter_constraints
    if name == "csp":
        return CSPFilter(load_answers() if answers is None else answers)
    if name == "table":
        return TableFilter(table or PatternTable.load_or_build(guesses, answers))
    raise ValueError(f"unknown filter {name!r}; choose from {', '.join(FILTER_NAMES)}")
